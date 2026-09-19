"""ARC3 Global Flash Closure V8: decision-leverage-gated refinement.

V7 established that a cross-game obstruction can safely *propose* a finer
representation and that destination-local evidence can validate it. But V7 was
neutral against the strong market control: valid refinements did not necessarily
change any decision.

V8 adds one more QCK gate:

    valid distinction != active distinction

A locally validated refinement becomes ACTIVE only when, on the same exact
pending action set and same destination-local evidence, switching from the
coarse representation to the refined representation changes the top-ranked
experiment by a material score margin. Otherwise the refinement remains RESERVE.

This is a counterfactual leverage test, not additional authority. Cross-game
evidence still cannot install destination outcomes or exact edges.
"""
from __future__ import annotations

import json

import global_flash_closure_v7 as v7

MIN_DECISION_MARGIN = 0.15

_ORIGINAL_CANDIDATES = v7.World.candidates
_ORIGINAL_SUMMARY = v7.World.summary


def _coarse_score(model, game: str, row):
    coarse = tuple(row.metadata.get("coarse_schema", row.schema or ()))
    score, meta = model.score(game, coarse, shared=False)
    return float(score), dict(meta), coarse


def leverage_gated_candidates(
    self,
    model,
    *,
    shared: bool,
    structural_model=None,
):
    rows = _ORIGINAL_CANDIDATES(
        self,
        model,
        shared=shared,
        structural_model=structural_model,
    )
    if not shared or structural_model is None or not rows:
        return rows

    if not hasattr(self, "leverage_evaluations"):
        self.leverage_evaluations = 0
        self.leverage_activations = 0
        self.leverage_reservations = 0
        self.leverage_changed_argmax = 0

    probe_rows = [
        row for row in rows
        if row.kind == "probe" and row.schema is not None
    ]
    if not probe_rows:
        return rows

    coarse_rows = []
    for row in probe_rows:
        score, meta, coarse = _coarse_score(model, self.game_id, row)
        coarse_rows.append((score, row, meta, coarse))
    coarse_rows.sort(
        key=lambda item: (
            item[0],
            tuple(-1 if value is None else value for value in (item[1].key or ())),
        ),
        reverse=True,
    )
    coarse_best = coarse_rows[0][1].key
    coarse_best_score = float(coarse_rows[0][0])

    current_rows = sorted(
        probe_rows,
        key=lambda row: (
            row.score,
            tuple(-1 if value is None else value for value in (row.key or ())),
        ),
        reverse=True,
    )
    refined_best = current_rows[0].key
    refined_best_score = float(current_rows[0].score)

    any_validated = any(
        row.metadata.get("representation_refined")
        for row in probe_rows
    )
    if not any_validated:
        return rows

    self.leverage_evaluations += 1
    changes_argmax = refined_best != coarse_best
    margin = refined_best_score - coarse_best_score
    if changes_argmax:
        self.leverage_changed_argmax += 1

    leverage_licensed = (
        changes_argmax
        and margin >= MIN_DECISION_MARGIN
    )

    if leverage_licensed:
        self.leverage_activations += 1
        for row in probe_rows:
            if row.metadata.get("representation_refined"):
                row.metadata["decision_leverage"] = {
                    "licensed": True,
                    "coarse_best": list(coarse_best) if coarse_best else None,
                    "refined_best": list(refined_best) if refined_best else None,
                    "score_margin": margin,
                    "threshold": MIN_DECISION_MARGIN,
                }
        return rows

    # The refinement was locally valid but had no demonstrated decision leverage.
    # Revert this candidate set to the market-local coarse ranking and keep the
    # proposed split in RESERVE. Raw observations in the shadow refined schema
    # remain retained for later re-evaluation.
    self.leverage_reservations += 1
    for score, row, coarse_meta, coarse in coarse_rows:
        row.score = score
        row.metadata = {
            **coarse_meta,
            "coarse_schema": coarse,
            "shadow_refined_schema": row.metadata.get(
                "shadow_refined_schema", coarse
            ),
            "effective_schema": coarse,
            "refinement_candidate": row.metadata.get(
                "refinement_capability"
            ),
            "local_refinement_validation": row.metadata.get(
                "local_refinement_validation"
            ),
            "representation_refined": False,
            "decision_leverage": {
                "licensed": False,
                "coarse_best": list(coarse_best) if coarse_best else None,
                "refined_best": list(refined_best) if refined_best else None,
                "score_margin": margin,
                "threshold": MIN_DECISION_MARGIN,
            },
        }

    # An unleveraged distinction is not ACTIVE in the destination representation.
    active_schemas = {
        tuple(row.metadata.get("coarse_schema", ()))
        for row in probe_rows
        if row.metadata.get("representation_refined")
    }
    for schema in list(self.active_refinements):
        if schema not in active_schemas:
            self.active_refinements.discard(schema)

    rows.sort(
        key=lambda row: (
            row.score,
            tuple(-1 if value is None else value for value in (row.key or ())),
        ),
        reverse=True,
    )
    return rows


def leverage_summary(self):
    row = _ORIGINAL_SUMMARY(self)
    row.update({
        "leverage_evaluations": int(getattr(self, "leverage_evaluations", 0)),
        "leverage_activations": int(getattr(self, "leverage_activations", 0)),
        "leverage_reservations": int(getattr(self, "leverage_reservations", 0)),
        "leverage_changed_argmax": int(getattr(self, "leverage_changed_argmax", 0)),
    })
    return row


v7.World.candidates = leverage_gated_candidates
v7.World.summary = leverage_summary


def main() -> None:
    v7.main()
    source = v7.OUT / "global-flash-closure-v7.json"
    report = json.loads(source.read_text())
    report["schema"] = "arc3-global-flash-closure-v8"
    report["repair"] = {
        "name": "COUNTERFACTUAL_DECISION_LEVERAGE_GATE_V1",
        "prior_boundary": "V7 safe but neutral vs market_local",
        "rule": (
            "a destination-validated refinement becomes ACTIVE only if refined "
            "local scoring changes the exact next probe relative to coarse local "
            "scoring by a material margin"
        ),
        "min_decision_margin": MIN_DECISION_MARGIN,
    }

    flash = report["arms"]["flash_validated_refinement"]
    market = report["arms"]["market_local"]
    leverage = {
        "evaluations": sum(
            game.get("leverage_evaluations", 0)
            for game in flash["games"].values()
        ),
        "activations": sum(
            game.get("leverage_activations", 0)
            for game in flash["games"].values()
        ),
        "reservations": sum(
            game.get("leverage_reservations", 0)
            for game in flash["games"].values()
        ),
        "changed_argmax": sum(
            game.get("leverage_changed_argmax", 0)
            for game in flash["games"].values()
        ),
    }
    report["decision_leverage"] = leverage

    protected_not_worse = all(
        flash["games"][game]["max_level"]
        >= market["games"][game]["max_level"]
        for game in v7.GAMES
    )
    better = (
        protected_not_worse
        and (
            flash["total_levels"] > market["total_levels"]
            or flash["consequence_yield_per_step"]
               > market["consequence_yield_per_step"]
            or flash["zero_change_steps"] < market["zero_change_steps"]
        )
    )
    report["scientific_verdict"] = (
        "PASS_LIVE_ADVANTAGE"
        if better
        else (
            "SAFE_PARITY"
            if protected_not_worse
            and flash["consequence_yield_per_step"]
               == market["consequence_yield_per_step"]
            and flash["zero_change_steps"] == market["zero_change_steps"]
            else "FAIL_LIVE_ADVANTAGE"
        )
    )

    out = v7.OUT / "global-flash-closure-v8.json"
    v7.audit.write_json(out, report)
    print(
        "GLOBAL_FLASH_CLOSURE_V8_RESULT="
        + json.dumps(
            {
                "scientific_verdict": report["scientific_verdict"],
                "decision_leverage": leverage,
                "market": {
                    "levels": market["total_levels"],
                    "yield": market["consequence_yield_per_step"],
                    "zero_change": market["zero_change_steps"],
                },
                "flash": {
                    "levels": flash["total_levels"],
                    "yield": flash["consequence_yield_per_step"],
                    "zero_change": flash["zero_change_steps"],
                },
            },
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()

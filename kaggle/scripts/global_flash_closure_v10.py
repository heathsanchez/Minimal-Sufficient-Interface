"""ARC3 Global Flash Closure V10: terminal-change deconfounding.

V9 failed because the ft09 fatal-basin counterexample was compiled too broadly:
it removed the entire positive state-change term across destinations.

V10 compiles only the consequence that is directly warranted by the failure:
GAME_OVER must not simultaneously receive a positive reward merely because it
changed public state.

The market's generic feature currently defines:
    change = CHANGE + PROGRESS + WIN + GAME_OVER
and scores +1.75 * change - 4.5 * terminal.

V10 subtracts exactly the terminal contribution to the positive change term:
    adjusted score = market score - 1.75 * terminal_rate

Fairness:
- every arm may apply this correction in ft09, where the exact source
  certificate lives;
- only Flash propagates the scheduler correction to ls20/vc33;
- nonterminal state change retains its original value;
- no destination outcomes are inferred.
"""
from __future__ import annotations

import json

import global_flash_closure_v7 as v7

CHANGE_REWARD = 1.75
CERT = v7.OUT / "inputs" / "ft09-fatal-basin-certificate.json"

_ORIGINAL_CANDIDATES = v7.World.candidates
_ORIGINAL_SUMMARY = v7.World.summary
_CERTIFICATE = None


def validate_certificate():
    global _CERTIFICATE
    data = json.loads(CERT.read_text())
    assert data["status"] == "CLOSED_BOUNDED_FATAL_BASIN_CERTIFICATE"
    assert data["fatal_source_states"] == 47
    assert data["probe_count"] == 282
    assert data["status_counts"]["GAME_OVER"] == 281
    assert data["negative_capability"]["protected_progress_observed"] is False
    _CERTIFICATE = data
    return data


def terminal_deconfounded_candidates(
    self,
    model,
    *,
    shared: bool,
    structural_model=None,
):
    # Isolate this scheduler mechanism; disable V7 representation transfer.
    rows = _ORIGINAL_CANDIDATES(
        self,
        model,
        shared=False,
        structural_model=None,
    )
    if not hasattr(self, "terminal_change_revaluations"):
        self.terminal_change_revaluations = 0
        self.terminal_change_rank_changes = 0
        self.terminal_change_score_removed = 0.0

    if _CERTIFICATE is None:
        return rows

    law_active = self.short == "ft09" or shared
    if not law_active:
        return rows

    before = [
        row.key for row in rows
        if row.kind == "probe" and row.key is not None
    ]
    changed = False
    for row in rows:
        if row.kind != "probe" or row.key is None:
            continue
        features = row.metadata.get("schema_features", {})
        terminal_rate = float(features.get("terminal", 0.0))
        removed = CHANGE_REWARD * terminal_rate
        if removed <= 0:
            continue
        row.score -= removed
        row.metadata = dict(row.metadata)
        row.metadata["compiled_scheduler_correction"] = {
            "law": "TERMINAL_CHANGE_HAS_NO_POSITIVE_CHANGE_CREDIT",
            "source_game": "ft09-0d8bbf25",
            "terminal_rate": terminal_rate,
            "positive_change_credit_removed": removed,
            "destination_behavior_inferred": False,
        }
        self.terminal_change_revaluations += 1
        self.terminal_change_score_removed += removed
        changed = True

    if changed:
        rows.sort(
            key=lambda row: (
                row.score,
                tuple(-1 if value is None else value for value in (row.key or ())),
            ),
            reverse=True,
        )
        after = [
            row.key for row in rows
            if row.kind == "probe" and row.key is not None
        ]
        if before and after and before[0] != after[0]:
            self.terminal_change_rank_changes += 1
    return rows


def summary(self):
    row = _ORIGINAL_SUMMARY(self)
    row.update({
        "terminal_change_revaluations": int(
            getattr(self, "terminal_change_revaluations", 0)
        ),
        "terminal_change_rank_changes": int(
            getattr(self, "terminal_change_rank_changes", 0)
        ),
        "terminal_change_score_removed": float(
            getattr(self, "terminal_change_score_removed", 0.0)
        ),
    })
    return row


v7.World.candidates = terminal_deconfounded_candidates
v7.World.summary = summary


def main() -> None:
    cert = validate_certificate()
    v7.main()
    source = v7.OUT / "global-flash-closure-v7.json"
    report = json.loads(source.read_text())
    report["schema"] = "arc3-global-flash-closure-v10"
    report["mechanism"] = {
        "name": "TERMINAL_CHANGE_DECONFOUNDING_V1",
        "source": {
            "game": "ft09-0d8bbf25",
            "status": cert["status"],
            "counterfactual_probes": cert["probe_count"],
            "game_over": cert["status_counts"]["GAME_OVER"],
        },
        "compiled_rule": (
            "remove only the positive state-change score contribution generated "
            "by destination-local GAME_OVER observations"
        ),
        "removed_weight": CHANGE_REWARD,
        "authority_boundary": (
            "scheduler arithmetic only; all terminal observations are destination-local"
        ),
    }

    flash = report["arms"]["flash_validated_refinement"]
    market = report["arms"]["market_local"]
    seq = report["arms"]["sequential_local"]

    def totals(arm):
        return {
            "revaluations": sum(
                g.get("terminal_change_revaluations", 0)
                for g in arm["games"].values()
            ),
            "rank_changes": sum(
                g.get("terminal_change_rank_changes", 0)
                for g in arm["games"].values()
            ),
            "score_removed": sum(
                g.get("terminal_change_score_removed", 0.0)
                for g in arm["games"].values()
            ),
        }

    market_effect = totals(market)
    flash_effect = totals(flash)
    seq_effect = totals(seq)
    cross_rank = flash_effect["rank_changes"] - market_effect["rank_changes"]

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
            or flash["terminal_failures"] < market["terminal_failures"]
        )
    )
    report["scheduler_correction_effect"] = {
        "sequential": seq_effect,
        "market_local": market_effect,
        "flash": flash_effect,
        "cross_game_rank_changes": cross_rank,
    }
    report["scientific_verdict"] = (
        "PASS_LIVE_ADVANTAGE"
        if better and cross_rank > 0
        else (
            "NO_CROSS_GAME_DECISION_EFFECT"
            if cross_rank == 0
            else (
                "SAFE_NO_ADVANTAGE"
                if protected_not_worse
                else "FAIL_LIVE_ADVANTAGE"
            )
        )
    )

    out = v7.OUT / "global-flash-closure-v10.json"
    v7.audit.write_json(out, report)
    print(
        "GLOBAL_FLASH_CLOSURE_V10_RESULT="
        + json.dumps(
            {
                "scientific_verdict": report["scientific_verdict"],
                "scheduler_correction_effect": report["scheduler_correction_effect"],
                "market": {
                    "levels": market["total_levels"],
                    "yield": market["consequence_yield_per_step"],
                    "zero_change": market["zero_change_steps"],
                    "terminal_failures": market["terminal_failures"],
                },
                "flash": {
                    "levels": flash["total_levels"],
                    "yield": flash["consequence_yield_per_step"],
                    "zero_change": flash["zero_change_steps"],
                    "terminal_failures": flash["terminal_failures"],
                },
            },
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()

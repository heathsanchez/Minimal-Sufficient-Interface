"""ARC3 Global Flash Closure V9: compiled negative scheduler law.

V5 established a bounded exact counterexample to the developmental heuristic
"state change is value": the retained ft09 (54,54) family changed public state
on 687/687 retained observations yet its bounded progression/counterfactual
family contained no protected progress and closed into a fatal basin.

The live market still contains a generic +1.75 * state-change term. V9 tests
whether a verified negative capability can compile into the scheduler itself:

    exact counterexample to generic heuristic
      -> remove unwarranted state-change reward
      -> revalue every live probe
      -> spend acquisition on protected/uncertain consequences instead

Fairness:
- all arms may compile the ft09 certificate into ft09's own local scheduler;
- only Flash may propagate that scheduler law to ls20/vc33;
- no destination outcome, exact edge, equivalence, or fatality is transferred;
- V7 representation-refinement effects are disabled to isolate this mechanism.
"""
from __future__ import annotations

import json
from pathlib import Path

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
    assert data["status_counts"]["ESCAPE_NO_CHANGE"] == 1
    assert data["negative_capability"]["protected_progress_observed"] is False
    _CERTIFICATE = data
    return data


def scheduler_law_candidates(
    self,
    model,
    *,
    shared: bool,
    structural_model=None,
):
    # Deliberately disable V7's representation mechanism. The only cross-game
    # experimental difference in V9 is propagation of the compiled scheduler law.
    rows = _ORIGINAL_CANDIDATES(
        self,
        model,
        shared=False,
        structural_model=None,
    )

    if not hasattr(self, "negative_scheduler_revaluations"):
        self.negative_scheduler_revaluations = 0
        self.negative_scheduler_score_removed = 0.0
        self.negative_scheduler_rank_changes = 0

    if _CERTIFICATE is None:
        return rows

    # Local authority: ft09 gets its own verified negative scheduler capability
    # in every arm. Flash may propagate the *proposal law* to other games.
    law_active = self.short == "ft09" or shared
    if not law_active:
        return rows

    before_order = [
        row.key for row in rows
        if row.kind == "probe" and row.key is not None
    ]
    changed = False
    for row in rows:
        if row.kind != "probe" or row.key is None:
            continue
        features = row.metadata.get("schema_features", {})
        change_rate = float(features.get("change", 0.0))
        removed = CHANGE_REWARD * change_rate
        if removed <= 0:
            continue
        row.score -= removed
        row.metadata = dict(row.metadata)
        row.metadata["compiled_negative_scheduler_law"] = {
            "law": "RAW_STATE_CHANGE_HAS_NO_GENERIC_POSITIVE_AUTHORITY",
            "source_game": "ft09-0d8bbf25",
            "source_certificate": "CLOSED_BOUNDED_FATAL_BASIN_CERTIFICATE",
            "change_reward_removed": removed,
            "destination_behavior_inferred": False,
        }
        self.negative_scheduler_revaluations += 1
        self.negative_scheduler_score_removed += removed
        changed = True

    if changed:
        rows.sort(
            key=lambda row: (
                row.score,
                tuple(-1 if value is None else value for value in (row.key or ())),
            ),
            reverse=True,
        )
        after_order = [
            row.key for row in rows
            if row.kind == "probe" and row.key is not None
        ]
        if before_order and after_order and before_order[0] != after_order[0]:
            self.negative_scheduler_rank_changes += 1

    return rows


def scheduler_law_summary(self):
    row = _ORIGINAL_SUMMARY(self)
    row.update({
        "negative_scheduler_revaluations": int(
            getattr(self, "negative_scheduler_revaluations", 0)
        ),
        "negative_scheduler_score_removed": float(
            getattr(self, "negative_scheduler_score_removed", 0.0)
        ),
        "negative_scheduler_rank_changes": int(
            getattr(self, "negative_scheduler_rank_changes", 0)
        ),
    })
    return row


v7.World.candidates = scheduler_law_candidates
v7.World.summary = scheduler_law_summary


def main() -> None:
    cert = validate_certificate()
    v7.main()

    source = v7.OUT / "global-flash-closure-v7.json"
    report = json.loads(source.read_text())
    report["schema"] = "arc3-global-flash-closure-v9"
    report["mechanism"] = {
        "name": "COMPILED_NEGATIVE_SCHEDULER_LAW_V1",
        "source": {
            "game": "ft09-0d8bbf25",
            "status": cert["status"],
            "fatal_source_states": cert["fatal_source_states"],
            "counterfactual_probes": cert["probe_count"],
            "game_over": cert["status_counts"]["GAME_OVER"],
            "no_change": cert["status_counts"]["ESCAPE_NO_CHANGE"],
        },
        "compiled_rule": (
            "remove the generic positive score assigned solely to raw public "
            "state change; retain progress, terminal, noop and uncertainty terms"
        ),
        "removed_weight": CHANGE_REWARD,
        "authority_boundary": (
            "proposal scoring only; no destination consequence is inferred"
        ),
    }

    flash = report["arms"]["flash_validated_refinement"]
    market = report["arms"]["market_local"]
    seq = report["arms"]["sequential_local"]

    def totals(arm):
        return {
            "revaluations": sum(
                g.get("negative_scheduler_revaluations", 0)
                for g in arm["games"].values()
            ),
            "rank_changes": sum(
                g.get("negative_scheduler_rank_changes", 0)
                for g in arm["games"].values()
            ),
            "score_removed": sum(
                g.get("negative_scheduler_score_removed", 0.0)
                for g in arm["games"].values()
            ),
        }

    market_effect = totals(market)
    flash_effect = totals(flash)
    seq_effect = totals(seq)

    # Cross-game effect excludes the locally-authorized ft09 uses that both
    # market and Flash receive.
    cross_game_revaluations = (
        flash_effect["revaluations"] - market_effect["revaluations"]
    )
    cross_game_rank_changes = (
        flash_effect["rank_changes"] - market_effect["rank_changes"]
    )

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
    report["scheduler_law_effect"] = {
        "sequential": seq_effect,
        "market_local": market_effect,
        "flash": flash_effect,
        "cross_game_revaluations": cross_game_revaluations,
        "cross_game_rank_changes": cross_game_rank_changes,
    }
    report["scientific_verdict"] = (
        "PASS_LIVE_ADVANTAGE"
        if better and cross_game_rank_changes > 0
        else (
            "NO_CROSS_GAME_DECISION_EFFECT"
            if cross_game_rank_changes == 0
            else (
                "SAFE_NO_ADVANTAGE"
                if protected_not_worse
                else "FAIL_LIVE_ADVANTAGE"
            )
        )
    )

    out = v7.OUT / "global-flash-closure-v9.json"
    v7.audit.write_json(out, report)
    print(
        "GLOBAL_FLASH_CLOSURE_V9_RESULT="
        + json.dumps(
            {
                "scientific_verdict": report["scientific_verdict"],
                "scheduler_law_effect": report["scheduler_law_effect"],
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

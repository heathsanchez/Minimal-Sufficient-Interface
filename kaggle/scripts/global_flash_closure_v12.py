"""ARC3 Global Flash Closure V12: separate allocation from local actuation.

V11 showed a clean decomposition:
- propagated terminal-change deconfounding improved vc33's local L1 milestone
  from 544 to 540 actions;
- but it distorted the global game allocator, causing 86 extra total actions
  before the same protected target.

V12 separates the two decisions.

1. GLOBAL ALLOCATION: which game receives the next paid interaction?
   Use destination-local market value only. A cross-game scheduler capability
   is not allowed to change another game's share of the acquisition budget.

2. LOCAL ACTUATION: once a game is selected, which exact probe does it execute?
   The ft09-derived terminal-change correction may change this within-game
   choice because all consequences remain destination-local.

The same anti-starvation rule is held fixed across market, Flash and SHAM.
"""
from __future__ import annotations

import json
import math

import global_flash_closure_v11 as v11

v10 = v11.v10
v7 = v11.v7


def _allocation_score(world, row, *, law_shared: bool) -> float:
    """Return the score authorized to allocate global budget to this game.

    ft09's correction is local authority and may affect its own allocation.
    For ls20/vc33 in the Flash arm, add back the propagated correction so
    foreign evidence cannot redirect global budget between games.
    """
    score = float(row.score)
    if (
        law_shared
        and world.short != "ft09"
        and row.kind == "probe"
    ):
        correction = row.metadata.get("compiled_scheduler_correction", {})
        score += float(correction.get("positive_change_credit_removed", 0.0))
    return score


def separated_selector(
    worlds,
    local_models,
    shared_model,
    *,
    law_shared: bool,
    total_steps: int,
):
    rows = []
    for game_id, world in worlds.items():
        if world.exhausted:
            continue

        candidates = world.candidates(
            local_models[game_id],
            shared=law_shared,
            structural_model=None,
        )
        if not candidates:
            continue

        execution_candidate = candidates[0]

        if execution_candidate.kind in ("reset", "replay"):
            allocation_score = float(execution_candidate.score)
        else:
            # Global demand sees the best destination-local baseline value from
            # this game's current executable frontier. Local Flash corrections
            # may still pick a different action after this game wins allocation.
            allocation_score = max(
                _allocation_score(world, row, law_shared=law_shared)
                for row in candidates
                if row.kind == "probe"
            )
            allocation_score += 0.35 / math.sqrt(1.0 + world.env_steps)

        rows.append((
            allocation_score,
            -world.env_steps,
            game_id,
            execution_candidate,
        ))

    if not rows:
        return None

    required = max(
        v7.WARMUP_PER_GAME,
        int(math.floor(v7.MIN_GAME_SHARE * float(total_steps + 1))),
    )
    starved = [
        row for row in rows
        if worlds[row[2]].env_steps < required
    ]
    if starved:
        starved.sort(
            key=lambda row: (
                required - worlds[row[2]].env_steps,
                row[0],
                row[1],
                row[2],
            ),
            reverse=True,
        )
        chosen = starved[0][3]
        chosen.metadata = dict(chosen.metadata)
        chosen.metadata["scheduler_guard"] = (
            "minimum_share_fixed_all_arms"
        )
        chosen.metadata["minimum_required_steps"] = required
        chosen.metadata["allocation_authority"] = (
            "destination_local_market"
        )
        return chosen

    rows.sort(
        key=lambda row: (row[0], row[1], row[2]),
        reverse=True,
    )
    chosen = rows[0][3]
    chosen.metadata = dict(chosen.metadata)
    chosen.metadata["allocation_authority"] = (
        "destination_local_market"
    )
    return chosen


v11.select_fair_candidate = separated_selector


def main():
    v11.main()
    source = v7.OUT / "global-flash-closure-v11.json"
    report = json.loads(source.read_text())
    report["schema"] = "arc3-global-flash-closure-v12"
    report["mechanism"] = {
        "name": "SEPARATED_GLOBAL_ALLOCATION_LOCAL_ACTUATION_V1",
        "v11_falsifier": (
            "cross-game scheduler correction improved vc33 locally but distorted "
            "global budget allocation"
        ),
        "global_allocation_authority": (
            "destination-local market score only"
        ),
        "local_actuation_authority": (
            "destination-local evidence plus verified proposal-law corrections"
        ),
    }

    market = report["market"]
    flash = report["flash"]
    sham = report["sham"]
    same_target = report["delta"]["same_protected_vector"]
    market_actions = market["acquisition_actions_to_target"]
    flash_actions = flash["acquisition_actions_to_target"]
    sham_actions = sham["acquisition_actions_to_target"]

    saved = (
        int(market_actions) - int(flash_actions)
        if market_actions is not None and flash_actions is not None
        else None
    )
    sham_saved = (
        int(market_actions) - int(sham_actions)
        if market_actions is not None and sham_actions is not None
        else None
    )
    verdict = (
        "PASS_EQUAL_OUTCOME_FEWER_ACQUISITION"
        if (
            same_target
            and saved is not None
            and saved > 0
            and sham_saved == 0
        )
        else (
            "PARITY"
            if same_target and saved == 0
            else "FAIL_EQUAL_OUTCOME_ACQUISITION"
        )
    )
    report["scientific_verdict"] = verdict
    report["delta"].update({
        "acquisition_actions_saved": saved,
        "sham_actions_saved": sham_saved,
    })

    v7.audit.write_json(
        v7.OUT / "global-flash-closure-v12.json",
        report,
    )
    print(
        "GLOBAL_FLASH_CLOSURE_V12_RESULT="
        + json.dumps(
            {
                "scientific_verdict": verdict,
                "delta": report["delta"],
                "market_per_game": market["per_game_actions_at_stop"],
                "flash_per_game": flash["per_game_actions_at_stop"],
                "market_milestones": market["target_game_milestones"],
                "flash_milestones": flash["target_game_milestones"],
            },
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()

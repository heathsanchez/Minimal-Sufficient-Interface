"""ARC3 Global Flash Closure V11: equal-protected-outcome acquisition test.

V10 produced a positive but mixed live signal. V11 asks the stronger question:
how many total paid environment interactions are required to reach the same
protected target?

Target:
    vc33 reaches Level 1
with ls20/ft09 remaining at their observed pre-target levels.

Both market and Flash:
- use the same frozen MG-ARC5;
- start from identical public worlds;
- use the same global market, warmup and anti-starvation rule;
- may compile the exact ft09 certificate locally inside ft09.

Only Flash may propagate the exact scheduler correction learned from ft09:
terminal observations do not receive positive state-change credit.

The run stops immediately when the target is first reached. No tail budget is
counted. SHAM runs the same global machinery without the relevant propagated
scheduler law.
"""
from __future__ import annotations

from collections import Counter
import json
import math

import global_flash_closure_v10 as v10

v7 = v10.v7

TARGET_GAME = "vc33-5430563c"
TARGET_LEVEL = 1


def target_reached(worlds) -> bool:
    return worlds[TARGET_GAME].max_level >= TARGET_LEVEL


def protected_vector(worlds):
    return {
        game: int(world.max_level)
        for game, world in worlds.items()
    }


def select_fair_candidate(
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
        candidate = candidates[0]
        fairness = 0.35 / math.sqrt(1.0 + world.env_steps)
        score = (
            candidate.score
            if candidate.kind in ("reset", "replay")
            else candidate.score + fairness
        )
        rows.append((score, -world.env_steps, game_id, candidate))

    if not rows:
        return None

    # Hold the anti-starvation rule fixed in every arm.
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
        chosen.metadata["scheduler_guard"] = "minimum_share_fixed_all_arms"
        chosen.metadata["minimum_required_steps"] = required
        return chosen

    rows.sort(key=lambda row: (row[0], row[1], row[2]), reverse=True)
    return rows[0][3]


def run_target(
    module,
    manifest,
    *,
    arm: str,
    law_shared: bool,
    global_graph: bool,
):
    worlds = v7.fresh_worlds(module, manifest, arm)
    local_models = {game: v7.ProposalModel() for game in v7.GAMES}
    shared_model = v7.ProposalModel() if global_graph else None
    metrics = Counter()
    trace = []
    global_steps_at_target = None

    try:
        initial = {game: world.root for game, world in worlds.items()}

        # Identical warmup order and count in every arm.
        for game_id in v7.GAMES:
            world = worlds[game_id]
            for _ in range(v7.WARMUP_PER_GAME):
                if target_reached(worlds):
                    break
                candidate_rows = world.candidates(
                    local_models[game_id],
                    shared=law_shared,
                    structural_model=None,
                )
                if not candidate_rows:
                    break
                event = v7.execute_and_close(
                    world,
                    candidate_rows[0],
                    local_model=local_models[game_id],
                    shared_model=shared_model,
                    worlds=worlds,
                    shared=global_graph,
                    metrics=metrics,
                )
                event["global_paid_step"] = sum(
                    item.env_steps for item in worlds.values()
                )
                trace.append(event)
                if target_reached(worlds):
                    global_steps_at_target = event["global_paid_step"]
                    break
            if target_reached(worlds):
                break

        while (
            global_steps_at_target is None
            and sum(item.env_steps for item in worlds.values()) < v7.TOTAL_BUDGET
        ):
            total = sum(item.env_steps for item in worlds.values())
            candidate = select_fair_candidate(
                worlds,
                local_models,
                shared_model,
                law_shared=law_shared,
                total_steps=total,
            )
            if candidate is None:
                break
            world = worlds[candidate.game]
            event = v7.execute_and_close(
                world,
                candidate,
                local_model=local_models[candidate.game],
                shared_model=shared_model,
                worlds=worlds,
                shared=global_graph,
                metrics=metrics,
            )
            event["global_paid_step"] = sum(
                item.env_steps for item in worlds.values()
            )
            trace.append(event)
            if target_reached(worlds):
                global_steps_at_target = event["global_paid_step"]
                break

        report = v7.arm_report(
            arm,
            worlds,
            metrics,
            trace[:240],
            initial,
        )
        report.update({
            "target_game": TARGET_GAME,
            "target_level": TARGET_LEVEL,
            "target_reached": target_reached(worlds),
            "acquisition_actions_to_target": global_steps_at_target,
            "protected_vector_at_stop": protected_vector(worlds),
            "per_game_actions_at_stop": {
                game: world.env_steps
                for game, world in worlds.items()
            },
            "target_game_milestones": list(
                worlds[TARGET_GAME].milestones
            ),
        })
        return report
    finally:
        v7.close_worlds(worlds)


def main():
    cert = v10.validate_certificate()

    manifest = json.loads((v7.OUT / "public.json").read_text())
    exact_games = tuple(row["game_id"] for row in manifest["games"])
    assert set(exact_games) == set(v7.GAMES)

    v7.audit.AGENT = v7.AGENT
    module = v7.audit.load_agent()
    v7.audit.block_network()

    market = run_target(
        module,
        manifest,
        arm="target_market_local",
        law_shared=False,
        global_graph=False,
    )
    flash = run_target(
        module,
        manifest,
        arm="target_flash",
        law_shared=True,
        global_graph=True,
    )
    sham = run_target(
        module,
        manifest,
        arm="target_sham",
        law_shared=False,
        global_graph=True,
    )

    same_target = (
        market["target_reached"]
        and flash["target_reached"]
        and market["protected_vector_at_stop"]
            == flash["protected_vector_at_stop"]
    )
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

    report = {
        "schema": "arc3-global-flash-closure-v11",
        "scientific_verdict": verdict,
        "interpretation": (
            "first-hit acquisition comparison to the same protected vc33 L1 "
            "target under an otherwise identical global market"
        ),
        "claim_boundary": (
            "public three-game seed-0 diagnostic; source capability changes "
            "proposal arithmetic only; no destination behavior transferred"
        ),
        "source_certificate": {
            "status": cert["status"],
            "run": "35387362885",
            "artifact": "10564626208",
            "sha256": "22748bb909fae8087e90bc51bd26780466dd153dd1974782515e676d0d24bd05",
        },
        "market": market,
        "flash": flash,
        "sham": sham,
        "delta": {
            "same_protected_vector": same_target,
            "acquisition_actions_saved": saved,
            "sham_actions_saved": sham_saved,
            "market_actions_to_target": market_actions,
            "flash_actions_to_target": flash_actions,
            "sham_actions_to_target": sham_actions,
        },
    }
    v7.audit.write_json(
        v7.OUT / "global-flash-closure-v11.json",
        report,
    )
    print(
        "GLOBAL_FLASH_CLOSURE_V11_RESULT="
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
    if verdict == "FAIL_EQUAL_OUTCOME_ACQUISITION":
        # Scientific failure is preserved as evidence; workflow itself remains
        # green unless an implementation/authority contract fails.
        pass


if __name__ == "__main__":
    main()

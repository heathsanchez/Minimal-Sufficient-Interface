"""Prospective ARC transfer gate: acquire level-1 capability, then hide target traces.

This is a development/mechanics qualification, not a Kaggle score claim.
Both arms see exactly the same public source-level trace evidence. At the first
level boundary, all exact trace/archive replay is removed before either arm
acts in the target level. The target asks only whether previously acquired
capability structure reduces charged interaction or earns progress.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))
sys.path.insert(0, str(ROOT / "kaggle" / "vendor" / "ARC-AGI-3-Agents"))

from arc_agi import Arcade, OperationMode
from arcengine import GameAction

from metalogic_arc3.memory_controller import MemoryGraphController
from metalogic_arc3.residual_exploration import ResidualController
from metalogic_arc3.runtime import normalize_frame


GAMES = (
    "ar25-0c556536",
    "ft09-0d8bbf25",
    "re86-8af5384d",
    "vc33-5430563c",
)


def action_ids() -> tuple[int, ...]:
    return tuple(int(a.value) for a in GameAction if a is not GameAction.RESET)


def commit_observation(controller, frame) -> None:
    if hasattr(controller, "observe_terminal"):
        controller.observe_terminal(frame)
        return
    obs = normalize_frame(frame)
    controller._process_previous_outcome(obs)
    controller._previous = obs
    controller._last_action = None


def issue(controller, env, current, sources: Counter[str]):
    obs = normalize_frame(current)
    token = controller.observe_and_choose(current)
    if token is None:
        return None
    if token.action_id not in obs.available_actions:
        raise AssertionError("controller emitted unavailable action")
    action = GameAction.from_id(token.action_id)
    data = {"x": token.x, "y": token.y} if token.action_id == 6 else {}
    nxt = env.step(action, data=data)
    sources[token.source] += 1
    if nxt is None:
        raise RuntimeError("environment returned no observation")
    return nxt


def disable_exact_target_replay(controller) -> None:
    # Source evidence has already been consumed. The target level is deliberately
    # trace-withheld for both arms. Learned in-session memory remains intact.
    controller.trace_capabilities = ()
    controller.archived_capabilities = ()
    controller._trace_active = None
    controller._trace_index = 0
    controller._archive_active = None
    controller._archive_index = 0
    controller._continuation = ()
    controller._continuation_index = 0


def run_arm(game_id: str, cls, environments: Path, source_budget: int, target_budget: int):
    controller = cls(action_ids())
    arcade = Arcade(operation_mode=OperationMode.OFFLINE,
                    environments_dir=str(environments.resolve()))
    env = arcade.make(game_id)
    if env is None:
        raise RuntimeError(f"missing public environment {game_id}")
    current = env.observation_space
    source_sources: Counter[str] = Counter()
    target_sources: Counter[str] = Counter()
    source_charged = 1  # initial make/reset observation
    target_charged = 0
    started = time.perf_counter()

    # Acquire exactly one source-level progress witness under ordinary warranted
    # priority. No target trace is withheld until that progress has happened.
    while int(current.levels_completed) < 1 and source_charged <= source_budget:
        obs = normalize_frame(current)
        if obs.state in ("GAME_OVER", "NOT_PLAYED"):
            commit_observation(controller, current)
            if obs.state == "GAME_OVER":
                controller.record_terminal_failure("GAME_OVER")
            controller.reset_episode()
            current = env.step(GameAction.RESET)
            source_charged += 1
            continue
        nxt = issue(controller, env, current, source_sources)
        if nxt is None:
            break
        current = nxt
        source_charged += 1

    source_level = int(current.levels_completed)
    commit_observation(controller, current)

    if source_level < 1:
        arcade.close_scorecard()
        return {
            "source_reached": False,
            "source_level": source_level,
            "source_charged": source_charged,
            "source_sources": dict(source_sources),
            "target_progress": False,
            "target_level": source_level,
            "target_charged": 0,
            "target_sources": {},
            "seconds": time.perf_counter() - started,
        }

    disable_exact_target_replay(controller)
    target_start_level = source_level

    # Target is the first unseen next-level problem for this controller.
    while int(current.levels_completed) <= target_start_level and target_charged < target_budget:
        obs = normalize_frame(current)
        if obs.state == "WIN":
            break
        if obs.state in ("GAME_OVER", "NOT_PLAYED"):
            commit_observation(controller, current)
            if obs.state == "GAME_OVER":
                controller.record_terminal_failure("GAME_OVER")
            controller.reset_episode()
            current = env.step(GameAction.RESET)
            target_charged += 1
            continue
        nxt = issue(controller, env, current, target_sources)
        if nxt is None:
            break
        current = nxt
        target_charged += 1

    commit_observation(controller, current)
    final_level = int(current.levels_completed)
    stats = dict(getattr(getattr(controller, "crystal", None), "stats", {}))
    arcade.close_scorecard()
    return {
        "source_reached": True,
        "source_level": source_level,
        "source_charged": source_charged,
        "source_sources": dict(source_sources),
        "target_start_level": target_start_level,
        "target_progress": final_level > target_start_level or normalize_frame(current).state == "WIN",
        "target_level": final_level,
        "target_charged": target_charged,
        "target_sources": dict(target_sources),
        "crystal_stats": stats,
        "seconds": time.perf_counter() - started,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environments", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-budget", type=int, default=220)
    parser.add_argument("--target-budget", type=int, default=220)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for game_id in GAMES:
        row = {"game": game_id, "arms": {}}
        for name, cls in (
            ("baseline", MemoryGraphController),
            ("candidate", ResidualController),
        ):
            result = run_arm(
                game_id, cls, args.environments,
                args.source_budget, args.target_budget)
            row["arms"][name] = result
            print(json.dumps({"game": game_id, "arm": name, **result}, sort_keys=True), flush=True)
        rows.append(row)

    comparable = [
        row for row in rows
        if row["arms"]["baseline"]["source_reached"]
        and row["arms"]["candidate"]["source_reached"]
    ]
    regressions = [
        row["game"] for row in comparable
        if row["arms"]["baseline"]["target_progress"]
        and not row["arms"]["candidate"]["target_progress"]
    ]
    gains = []
    for row in comparable:
        b = row["arms"]["baseline"]
        c = row["arms"]["candidate"]
        if c["target_progress"] and not b["target_progress"]:
            gains.append({"game": row["game"], "kind": "new_progress"})
        elif c["target_progress"] and b["target_progress"] and c["target_charged"] < b["target_charged"]:
            gains.append({
                "game": row["game"], "kind": "fewer_actions",
                "baseline": b["target_charged"], "candidate": c["target_charged"]})

    relative_uses = sum(
        row["arms"]["candidate"]["target_sources"].get("crystal_relative", 0)
        + row["arms"]["candidate"]["target_sources"].get("crystal_relative_extension", 0)
        for row in comparable
    )
    relative_progress = sum(
        row["arms"]["candidate"].get("crystal_stats", {}).get("relative_capability_progress", 0)
        for row in comparable
    )
    extension_progress = sum(
        row["arms"]["candidate"].get("crystal_stats", {}).get("relative_extension_progress", 0)
        for row in comparable
    )

    result = {
        "schema": "arc3.source-acquire-target-withhold@1",
        "scope": "four public development games with independently known later-level progress; target exact traces hidden equally from both arms",
        "games": list(GAMES),
        "rows": rows,
        "comparable_games": [row["game"] for row in comparable],
        "relative_target_uses": relative_uses,
        "relative_progress": relative_progress,
        "relative_extension_progress": extension_progress,
        "gains": gains,
        "regressions": regressions,
        "promotion_candidate": bool(gains and not regressions and relative_uses and (relative_progress or extension_progress)),
    }
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, sort_keys=True))


if __name__ == "__main__":
    main()

"""Prospective public development A/B for palette-invariant ACTION6 role grounding.

Both arms use the same ResidualController with all exact trace/archive banks
removed. The only changed variable is role_grounding. Role grounding may
reorder ACTION6 proposals but never removes the historical dense lattice.
This is not a Kaggle/private score claim.
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
from metalogic_arc3.residual_exploration import ResidualController
from metalogic_arc3.runtime import normalize_frame


def action_ids() -> tuple[int, ...]:
    return tuple(int(a.value) for a in GameAction if a is not GameAction.RESET)


def terminal(controller, frame) -> None:
    if hasattr(controller, "observe_terminal"):
        controller.observe_terminal(frame)
    else:
        obs = normalize_frame(frame)
        controller._process_previous_outcome(obs)
        controller._previous = obs
        controller._last_action = None


def run_game(game_id: str, environments: Path, *, role_grounding: bool, budget: int):
    ctl = ResidualController(
        action_ids(),
        role_grounding=role_grounding,
        archived_capabilities=(),
        trace_capabilities=(),
    )
    arcade = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=str(environments.resolve()),
    )
    env = arcade.make(game_id)
    if env is None:
        raise RuntimeError(f"missing public environment {game_id}")
    current = env.observation_space
    steps = 0
    resets = 1
    peak = int(current.levels_completed)
    sources: Counter[str] = Counter()
    role_action6 = 0
    action6 = 0
    checkpoints = []
    started = time.perf_counter()

    for _ in range(budget):
        obs = normalize_frame(current)
        if obs.state == "WIN":
            break
        if obs.state in ("GAME_OVER", "NOT_PLAYED"):
            terminal(ctl, current)
            if obs.state == "GAME_OVER":
                ctl.record_terminal_failure("GAME_OVER")
            ctl.reset_episode()
            current = env.step(GameAction.RESET)
            resets += 1
        else:
            token = ctl.observe_and_choose(current)
            if token is None:
                break
            if token.action_id not in obs.available_actions:
                raise AssertionError("controller emitted unavailable action")
            if token.action_id == 6:
                action6 += 1
                if (
                    getattr(ctl, "_role_grounding_digest", None) == obs.frame_digest
                    and (token.x, token.y) in getattr(ctl, "_role_grounding_coordinates", ())
                ):
                    role_action6 += 1
            action = GameAction.from_id(token.action_id)
            data = {"x": token.x, "y": token.y} if token.action_id == 6 else {}
            current = env.step(action, data=data)
            if current is None:
                raise RuntimeError("environment returned no observation")
            sources[token.source] += 1
            steps += 1

        if int(current.levels_completed) > peak:
            peak = int(current.levels_completed)
            checkpoints.append({"level": peak, "charged": steps + resets})

    terminal(ctl, current)
    result = {
        "levels": peak,
        "steps": steps,
        "resets": resets,
        "charged": steps + resets,
        "sources": dict(sources),
        "action6": action6,
        "role_action6": role_action6,
        "checkpoints": checkpoints,
        "seconds": time.perf_counter() - started,
        "crystal_stats": dict(ctl.crystal.stats),
    }
    arcade.close_scorecard()
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environments", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--budget", type=int, default=220)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)

    download = Arcade(
        operation_mode=OperationMode.NORMAL,
        environments_dir=str(args.environments.resolve()),
    )
    catalog = sorted(download.get_environments(), key=lambda item: item.game_id)
    games = [item.game_id for item in catalog]
    manifest = {
        "schema": "arc.role-grounding-public-manifest@1",
        "games": games,
        "budget": args.budget,
        "protocol": "same no-trace ResidualController; only role_grounding flag differs",
    }
    args.output.with_suffix(".manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    for game in games:
        env = download.make(game)
        if env is None:
            raise RuntimeError(f"public environment download failed: {game}")
        print("ROLE_GROUNDING_GAME_READY", game, flush=True)
    download.close_scorecard()

    rows = []
    for game in games:
        row = {"game": game, "arms": {}}
        for name, enabled in (("baseline", False), ("candidate", True)):
            value = run_game(game, args.environments, role_grounding=enabled, budget=args.budget)
            row["arms"][name] = value
            print(json.dumps({"game": game, "arm": name, **value}, sort_keys=True), flush=True)
        rows.append(row)
        args.output.with_suffix(".partial.json").write_text(
            json.dumps(rows, indent=2, sort_keys=True) + "\n"
        )

    regressions = []
    gains = []
    action_savings = []
    for row in rows:
        b = row["arms"]["baseline"]
        c = row["arms"]["candidate"]
        if c["levels"] < b["levels"]:
            regressions.append({
                "game": row["game"], "baseline": b["levels"], "candidate": c["levels"]
            })
        if c["levels"] > b["levels"]:
            gains.append({
                "game": row["game"], "kind": "level",
                "baseline": b["levels"], "candidate": c["levels"]
            })
        bcp = {x["level"]: x["charged"] for x in b["checkpoints"]}
        ccp = {x["level"]: x["charged"] for x in c["checkpoints"]}
        for level in sorted(set(bcp) & set(ccp)):
            if ccp[level] < bcp[level]:
                action_savings.append({
                    "game": row["game"], "level": level,
                    "baseline": bcp[level], "candidate": ccp[level],
                    "saved": bcp[level] - ccp[level],
                })

    result = {
        "schema": "arc3.role-grounded-action6-v1",
        "scope": "all accessible public development games; exact trace/archive banks disabled; not private/Kaggle score",
        "manifest": manifest,
        "rows": rows,
        "sum_levels": {
            "baseline": sum(row["arms"]["baseline"]["levels"] for row in rows),
            "candidate": sum(row["arms"]["candidate"]["levels"] for row in rows),
        },
        "total_role_action6": sum(row["arms"]["candidate"]["role_action6"] for row in rows),
        "total_action6": {
            "baseline": sum(row["arms"]["baseline"]["action6"] for row in rows),
            "candidate": sum(row["arms"]["candidate"]["action6"] for row in rows),
        },
        "gains": gains,
        "action_savings": action_savings,
        "regressions": regressions,
    }
    result["promotion_candidate"] = bool(
        not regressions
        and result["total_role_action6"] > 0
        and (gains or action_savings)
        and result["sum_levels"]["candidate"] >= result["sum_levels"]["baseline"]
    )
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        k: v for k, v in result.items() if k not in ("rows", "manifest")
    }, sort_keys=True))


if __name__ == "__main__":
    main()

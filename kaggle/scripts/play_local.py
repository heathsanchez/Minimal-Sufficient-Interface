"""Run the generated agent locally against real ARC-AGI-3 games.

Adapted from the official ARC-AGI-3 Kaggle starter. Build `agent/my_agent.py`
first, then use the vendored ARC-AGI-3-Agents framework installed by setup.
"""
from __future__ import annotations

import argparse
import importlib.util
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "ARC-AGI-3-Agents"
if not VENDOR.exists():
    raise SystemExit(f"Framework not found at {VENDOR}. Run `make setup` first.")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(VENDOR))

import arc_agi
from arc_agi import OperationMode


def load_my_agent_class():
    spec = importlib.util.spec_from_file_location(
        "user_agent_module", ROOT / "agent" / "my_agent.py"
    )
    if spec is None or spec.loader is None:
        raise SystemExit("Could not load agent/my_agent.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "MyAgent"):
        raise SystemExit("agent/my_agent.py must define MyAgent")
    return module.MyAgent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", default=None)
    parser.add_argument("--max-steps", type=int, default=200)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--render", default=None, choices=[None, "terminal"])
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    arc = arc_agi.Arcade(operation_mode=OperationMode.NORMAL)
    all_envs = arc.get_environments()

    if args.list:
        print(f"{len(all_envs)} environments:")
        for env in all_envs:
            print(f"  {env.game_id}: {getattr(env, 'title', '?')}")
        return

    if args.game:
        wanted = {game.strip().split("-")[0] for game in args.game.split(",")}
        game_ids = [
            env.game_id.split("-")[0]
            for env in all_envs
            if env.game_id.split("-")[0] in wanted
        ]
        missing = wanted - set(game_ids)
        if missing:
            raise SystemExit(f"Unknown game id(s): {sorted(missing)}. Run --list.")
    else:
        game_ids = [env.game_id.split("-")[0] for env in all_envs]
        print(f"Playing all {len(game_ids)} available games.\n")

    MyAgentCls = load_my_agent_class()
    if hasattr(MyAgentCls, "MAX_ACTIONS"):
        MyAgentCls.MAX_ACTIONS = min(MyAgentCls.MAX_ACTIONS, args.max_steps)

    per_game = []
    for index, game_id in enumerate(game_ids, 1):
        print(f"=== [{index}/{len(game_ids)}] {game_id} ===")
        env = arc.make(game_id, render_mode=args.render)
        if env is None:
            print(f"  could not create env for {game_id!r}, skipping")
            continue
        agent = MyAgentCls(
            card_id="local-dev",
            game_id=game_id,
            agent_name=f"MyAgent.local.{game_id}",
            ROOT_URL="http://localhost",
            record=False,
            arc_env=env,
            tags=["local-dev"],
        )
        agent.main()
        final = agent.frames[-1]
        per_game.append((game_id, final.state, final.levels_completed, agent.action_counter))
        print(
            f"  -> state={final.state}, levels_completed={final.levels_completed}, "
            f"actions={agent.action_counter}"
        )

    scorecard = arc.get_scorecard()
    print("\n========= SUMMARY =========")
    for game_id, state, levels, actions in per_game:
        print(f"  {game_id:8} levels={levels:3} actions={actions:5} state={state}")
    score = scorecard.score if hasattr(scorecard, "score") else scorecard
    print(f"\nAggregate scorecard score: {score}")


if __name__ == "__main__":
    main()

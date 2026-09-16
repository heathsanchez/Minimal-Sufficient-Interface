"""Run the generated agent through the official ARC-AGI-3 Agent loop.

Two modes are supported:

* default: normal local/API development mode from the official starter;
* --offline-environments-dir: exact public offline environment files, matching
  the pinned qualification protocol used by the ARC3 research lineage.

The offline path preserves full versioned game IDs (for example
``bt33-a7c3f9d18b4e``) so the exact public environment is exercised.
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


def _available_game_ids(arc) -> list[str]:
    try:
        return [env.game_id for env in arc.get_environments()]
    except Exception:
        return []


def _resolve_requested_games(requested: str | None, available: list[str], offline: bool) -> list[str]:
    if not requested:
        if available:
            return available
        raise SystemExit("No game specified and no environments could be enumerated.")

    tokens = [item.strip() for item in requested.split(",") if item.strip()]
    resolved_game_ids: list[str] = []
    for token in tokens:
        if token in available:
            resolved_game_ids.append(token)
            continue

        short_matches = [gid for gid in available if gid.split("-")[0] == token]
        if len(short_matches) == 1:
            resolved_game_ids.append(short_matches[0])
            continue
        if len(short_matches) > 1:
            raise SystemExit(
                f"Ambiguous short game id {token!r}; choose one exact versioned id: {short_matches}"
            )

        # The pinned public offline protocol already knows exact versioned IDs.
        # Some SDK versions do not enumerate offline files, so preserve an
        # explicitly versioned request and let Arcade.make validate it.
        if offline and "-" in token:
            resolved_game_ids.append(token)
            continue

        raise SystemExit(f"Unknown game id {token!r}. Available: {available}")
    return resolved_game_ids


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", default=None)
    parser.add_argument("--max-steps", type=int, default=200)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--render", default=None, choices=[None, "terminal"])
    parser.add_argument(
        "--offline-environments-dir",
        type=Path,
        default=None,
        help="Use pinned public ARC environment files with OperationMode.OFFLINE.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    offline = args.offline_environments_dir is not None
    if offline:
        env_dir = args.offline_environments_dir.resolve()
        if not env_dir.is_dir():
            raise SystemExit(f"Offline environments directory not found: {env_dir}")
        arc = arc_agi.Arcade(
            operation_mode=OperationMode.OFFLINE,
            environments_dir=str(env_dir),
        )
    else:
        arc = arc_agi.Arcade(operation_mode=OperationMode.NORMAL)

    available = _available_game_ids(arc)
    if args.list:
        print(f"{len(available)} environments:")
        for game_id in available:
            print(f"  {game_id}")
        return

    resolved_game_ids = _resolve_requested_games(args.game, available, offline)
    MyAgentCls = load_my_agent_class()
    if hasattr(MyAgentCls, "MAX_ACTIONS"):
        MyAgentCls.MAX_ACTIONS = min(int(MyAgentCls.MAX_ACTIONS), args.max_steps)

    per_game = []
    for index, game_id in enumerate(resolved_game_ids, 1):
        print(f"=== [{index}/{len(resolved_game_ids)}] {game_id} ===")
        env = arc.make(game_id, render_mode=args.render)
        if env is None:
            raise SystemExit(f"Could not create exact environment {game_id!r}")
        agent = MyAgentCls(
            card_id="local-dev",
            game_id=game_id,
            agent_name=f"MyAgent.local.{game_id}",
            ROOT_URL="http://localhost",
            record=False,
            arc_env=env,
            tags=["local-dev", "offline-public" if offline else "normal"],
        )
        agent.main()
        final = agent.frames[-1]
        per_game.append((game_id, final.state, final.levels_completed, agent.action_counter))
        print(
            f"  -> state={final.state}, levels_completed={final.levels_completed}, "
            f"actions={agent.action_counter}"
        )

    if not per_game:
        raise SystemExit("No ARC3 environment was executed")

    try:
        scorecard = arc.close_scorecard()
        score = getattr(scorecard, "score", scorecard)
    except Exception:
        score = None

    print("\n========= SUMMARY =========")
    for game_id, state, levels, actions in per_game:
        print(f"  {game_id:24} levels={levels:3} actions={actions:5} state={state}")
    if score is not None:
        print(f"\nAggregate scorecard score: {score}")
    print("ARC3_PUBLIC_SMOKE=PASS")


if __name__ == "__main__":
    main()

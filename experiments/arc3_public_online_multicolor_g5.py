from __future__ import annotations

import json
import os
from pathlib import Path

from arcengine import GameState

import arc3_public_panel_correspondence_g3 as g3
from arc3_public_online_scale_normalized_g4 import execute_session
from metalogic_arc3.semantic_path import close_path_capabilities


OUT = Path(os.environ.get(
    "OUTDIR", "evidence/arc3-public-online-multicolor-g5"
)).resolve()
OUT.mkdir(parents=True, exist_ok=True)


def replay_once():
    env, _ = g3.enter_level3()
    frame = env.observation_space
    sessions = []
    actions = []
    for expected_level in (3, 4, 5):
        frame, session, level_actions = execute_session(env, frame)
        sessions.append(session)
        actions.append(level_actions)
        if int(frame.levels_completed) != expected_level:
            raise AssertionError(f"qualified level {expected_level} entry drifted")
    successor = close_path_capabilities(frame)
    return {
        "progressed": int(frame.levels_completed) > 4 or frame.state == GameState.WIN,
        "level": int(frame.levels_completed),
        "state": str(frame.state),
        "paths": [session.plan.path for session in sessions],
        "action_counts": [len(level_actions) for level_actions in actions],
        "g5_codes": {key: list(value) for key, value in sorted(sessions[-1].codes.items())},
        "g5_probe_ports": list(sessions[-1].plan.probe_ports),
        "successor_closure": {
            "closed_interfaces": list(successor.closed_interfaces),
            "plan": None if successor.plan is None else successor.plan.path,
            "residual": None if successor.residual is None else {
                "missing_interface": successor.residual.missing_interface,
                "reason": successor.residual.reason,
            },
        },
    }


def main():
    replays = [replay_once(), replay_once()]
    promoted = all(row["progressed"] for row in replays)
    result = {
        "status": "PROMOTED" if promoted else "RESIDUAL",
        "classification": "WARRANTED POSITIVE" if promoted else "RESIDUAL",
        "hypothesis": (
            "the reusable controller compiles G5 as rotate, descend three, recolor through "
            "the active middle source port, then grow"
        ),
        "replays": replays,
        "independent_replay_count": 2,
        "action_budget_per_level": 40,
        "model_calls": 0,
        "source_inspection": False,
        "claim_boundary": (
            "hard restart through qualified G1-G4 and integrated semantic G5; visible pixels, "
            "legal clicks, terminal progress, and typed successor residual only"
        ),
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True), flush=True)
    print(f"ARC3_PUBLIC_ONLINE_MULTICOLOR_G5={result['status']}", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()

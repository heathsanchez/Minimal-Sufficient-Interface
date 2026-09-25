from __future__ import annotations

import json
import os
from pathlib import Path

from arcengine import GameState

import arc3_public_all_blue_to_gray_g2 as ab
import arc3_public_panel_correspondence_g3 as g3
from metalogic_arc3.semantic_path import SemanticPathSession, close_path_capabilities


OUT = Path(os.environ.get(
    "OUTDIR", "evidence/arc3-public-online-scale-normalized-g4"
)).resolve()
OUT.mkdir(parents=True, exist_ok=True)


def execute_session(env, frame):
    session = SemanticPathSession.start(frame)
    actions = []
    while session.phase != "done" and len(actions) < 40:
        x, y = session.next_action(frame)
        actions.append({
            "xy": [x, y],
            "kind": session.last_action_kind,
            "label": session.pending_probe if session.last_action_kind == "probe" else None,
            "value": session.last_write_value if session.last_action_kind == "write" else None,
        })
        frame = ab.click(env, (y, x))
    if session.phase != "done":
        raise AssertionError("semantic session exceeded action budget")
    return frame, session, actions


def replay_once():
    env, _ = g3.enter_level3()
    frame, g3_session, g3_actions = execute_session(env, env.observation_space)
    if int(frame.levels_completed) != 3:
        raise AssertionError("qualified G3 entry drifted")
    frame, g4_session, g4_actions = execute_session(env, frame)
    progressed = int(frame.levels_completed) > 3 or frame.state == GameState.WIN
    successor = close_path_capabilities(frame) if progressed else None
    return {
        "progressed": progressed,
        "level": int(frame.levels_completed),
        "state": str(frame.state),
        "g3_path": g3_session.plan.path,
        "g4_path": g4_session.plan.path,
        "g3_action_count": len(g3_actions),
        "g4_action_count": len(g4_actions),
        "g4_codes": {key: list(value) for key, value in sorted(g4_session.codes.items())},
        "successor_closure": None if successor is None else {
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
            "scale-normalize the enlarged transported mover, prove primitive complementarity, "
            "select the smaller equal-anchor control to shrink, align left, then descend"
        ),
        "replays": replays,
        "independent_replay_count": 2,
        "action_budget_per_level": 40,
        "model_calls": 0,
        "source_inspection": False,
        "claim_boundary": (
            "hard restart through qualified G1-G3 and integrated semantic G4; only visible "
            "pixels, legal clicks, and terminal progress; successor preserves typed UNKNOWN"
        ),
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True), flush=True)
    print(f"ARC3_PUBLIC_ONLINE_SCALE_NORMALIZED_G4={result['status']}", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import os
from pathlib import Path

from metalogic_arc3.semantic_path import SemanticPathSession, close_path_capabilities


OUT = Path(os.environ.get(
    "OUTDIR", "evidence/arc3-public-online-path-capability-g3"
)).resolve()
OUT.mkdir(parents=True, exist_ok=True)


def require_runtime():
    from arcengine import GameState
    import arc3_public_all_blue_to_gray_g2 as ab
    import arc3_public_panel_correspondence_g3 as g3
    return GameState, ab, g3


def replay_once():
    GameState, ab, g3 = require_runtime()
    env, _ = g3.enter_level3()
    frame = env.observation_space
    start_level = int(frame.levels_completed)
    session = SemanticPathSession.start(frame)
    actions = []
    for _ in range(40):
        if session.phase == "done":
            break
        x, y = session.next_action(frame)
        kind = session.last_action_kind
        direction = session.pending_probe if kind == "probe" else None
        value = session.last_write_value if kind == "write" else None
        frame = ab.click(env, (y, x))
        actions.append({
            "xy": [x, y],
            "kind": kind,
            "direction": direction,
            "value": value,
            "level": int(frame.levels_completed),
            "state": str(frame.state),
        })
    if session.phase != "done":
        raise AssertionError("online semantic session exceeded action budget")
    progressed = int(frame.levels_completed) > start_level or frame.state == GameState.WIN
    successor = close_path_capabilities(frame) if progressed else None
    return {
        "progressed": progressed,
        "start_level": start_level,
        "final_level": int(frame.levels_completed),
        "state": str(frame.state),
        "path": session.plan.path,
        "probes": [list(point) for point in session.plan.probes],
        "probe_directions": list(session.plan.probe_directions),
        "codes": {key: list(value) for key, value in sorted(session.codes.items())},
        "submit": list(session.plan.submit),
        "action_count": len(actions),
        "actions": actions,
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
    promoted = all(replay["progressed"] for replay in replays)
    successor_residuals = [
        replay["successor_closure"]["residual"]
        for replay in replays
        if replay["successor_closure"] is not None
    ]
    stable_successor_residual = (
        len(successor_residuals) == 2
        and all(item == {
            "missing_interface": "shape.subcell-docking-pose@1",
            "reason": "subcell_docking_geometry",
        } for item in successor_residuals)
    )
    result = {
        "status": "PROMOTED" if promoted else "RESIDUAL",
        "hypothesis": (
            "a complement-tiling glyph translation identifies a board displacement; "
            "the shortest legal path supplies ordered target columns; direction codes "
            "are learned by four sequential legal selector probes in the same episode"
        ),
        "classification": "WARRANTED POSITIVE" if promoted else "RESIDUAL",
        "replays": replays,
        "independent_replay_count": 2,
        "successor_interface_status": (
            "EXACT_RESIDUAL" if stable_successor_residual else "UNKNOWN"
        ),
        "successor_missing_interface": (
            "shape.subcell-docking-pose@1" if stable_successor_residual else None
        ),
        "action_budget": 40,
        "model_calls": 0,
        "source_inspection": False,
        "claim_boundary": (
            "exact public tn36 G3 after qualified G1+G2 entry; only public pixels, "
            "legal clicks, and terminal progress; online codebook induction uses one "
            "live episode per replay; the immediate G4 observation is closed only "
            "through current-frame and tiled-grid interfaces, then preserves typed "
            "UNKNOWN at shape.subcell-docking-pose@1"
        ),
        "residual": None if promoted else "online_path_capability_did_not_advance_g3",
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    marker = "PROMOTED" if promoted else "RESIDUAL"
    print(f"ARC3_PUBLIC_ONLINE_PATH_CAPABILITY_G3={marker}")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

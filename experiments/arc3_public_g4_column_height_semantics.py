from __future__ import annotations

import json
import os
from pathlib import Path

from arcengine import GameState

import arc3_public_all_blue_to_gray_g2 as ab
import arc3_public_panel_correspondence_g3 as g3
from metalogic_arc3.semantic_path import SemanticPathSession, _bar_rows, _matrix, _source_bits, _submit


OUT = Path(os.environ.get(
    "OUTDIR", "evidence/arc3-public-g4-column-height-semantics"
)).resolve()
OUT.mkdir(parents=True, exist_ok=True)

PROBES = {5: (15, 58), 2: (25, 58), 1: (35, 58)}
PROFILE = (5, 1, 2, 2, 1, 5)


def enter_g4():
    env, _ = g3.enter_level3()
    frame = env.observation_space
    session = SemanticPathSession.start(frame)
    while session.phase != "done":
        x, y = session.next_action(frame)
        frame = ab.click(env, (y, x))
    return env, frame


def replay_once():
    env, frame = enter_g4()
    start_level = int(frame.levels_completed)
    codes = {}
    actions = []
    for height, (x, y) in PROBES.items():
        frame = ab.click(env, (y, x))
        codes[height] = _source_bits(_matrix(frame))
        actions.append({"kind": "probe", "height": height, "xy": [x, y]})

    targets = _bar_rows(_matrix(frame), "right")
    columns = [codes[height] for height in PROFILE]
    for row_index, target_row in enumerate(targets):
        for col_index, (x, y) in enumerate(target_row):
            desired = columns[col_index][row_index]
            current = 1 if _matrix(frame)[y][x] == 5 else 0
            if current != desired:
                frame = ab.click(env, (y, x))
                actions.append({
                    "kind": "write", "row": row_index, "column": col_index,
                    "value": desired, "xy": [x, y],
                })

    submit = _submit(_matrix(frame))
    frame = ab.click(env, (submit[1], submit[0]))
    actions.append({"kind": "submit", "xy": list(submit)})
    return {
        "progressed": int(frame.levels_completed) > start_level or frame.state == GameState.WIN,
        "level": int(frame.levels_completed),
        "state": str(frame.state),
        "codes": {str(key): list(value) for key, value in codes.items()},
        "profile": list(PROFILE),
        "actions": actions,
        "action_count": len(actions),
    }


def main() -> None:
    first = replay_once()
    verification = [replay_once(), replay_once()] if first["progressed"] else []
    promoted = first["progressed"] and all(row["progressed"] for row in verification)
    result = {
        "status": "PROMOTED" if promoted else "RESIDUAL",
        "classification": "WARRANTED POSITIVE" if promoted else "WARRANTED NEGATIVE",
        "hypothesis": (
            "after scale-normalized complement identification, each of the six target "
            "columns is labeled by the visible vertical purple extent of the corresponding "
            "column of the six-wide small docking glyph; the selector glyphs encode heights 5, 2, 1"
        ),
        "profile": list(PROFILE),
        "first": first,
        "verification": verification,
        "independent_replay_count": len(verification),
        "model_calls": 0,
        "source_inspection": False,
        "claim_boundary": (
            "exact public tn36 G4 after qualified G1-G3 entry; one directly observed "
            "six-column height profile; terminal progress is the independent oracle"
        ),
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True), flush=True)
    print(f"ARC3_PUBLIC_G4_COLUMN_HEIGHT_SEMANTICS={result['status']}", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()

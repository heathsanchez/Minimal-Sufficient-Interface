from __future__ import annotations

import json
import os
from pathlib import Path

from arcengine import GameState

import arc3_public_all_blue_to_gray_g2 as ab
import arc3_public_panel_correspondence_g3 as g3
from metalogic_arc3.semantic_path import (
    SemanticPathSession,
    _bar_rows,
    _matrix,
    _source_bits,
    _submit,
)


OUT = Path(os.environ.get(
    "OUTDIR", "evidence/arc3-public-g4-scale-normalized-docking"
)).resolve()
OUT.mkdir(parents=True, exist_ok=True)

PROBES = {"S": (15, 58), "D": (25, 58), "L": (35, 58)}
PATHS = ("SDDLDD", "SLDDDD", "SDLDDD")


def enter_g4():
    env, _ = g3.enter_level3()
    frame = env.observation_space
    session = SemanticPathSession.start(frame)
    while session.phase != "done":
        x, y = session.next_action(frame)
        frame = ab.click(env, (y, x))
    if int(frame.levels_completed) != 3 or frame.state != GameState.NOT_FINISHED:
        raise AssertionError(f"expected G4, got level={frame.levels_completed} state={frame.state}")
    return env, frame


def run_path(path: str):
    env, frame = enter_g4()
    start_level = int(frame.levels_completed)
    codes = {}
    actions = []
    for label, (x, y) in PROBES.items():
        frame = ab.click(env, (y, x))
        codes[label] = _source_bits(_matrix(frame))
        actions.append({"kind": "probe", "label": label, "xy": [x, y]})

    grid = _matrix(frame)
    targets = _bar_rows(grid, "right")
    if len(targets) != 6 or any(len(row) != len(path) for row in targets):
        raise AssertionError("expected six-by-six target panel")
    columns = [codes[label] for label in path]
    for row_index, target_row in enumerate(targets):
        for col_index, (x, y) in enumerate(target_row):
            desired = columns[col_index][row_index]
            current = 1 if _matrix(frame)[y][x] == 5 else 0
            if current != desired:
                frame = ab.click(env, (y, x))
                actions.append({
                    "kind": "write",
                    "row": row_index,
                    "column": col_index,
                    "value": desired,
                    "xy": [x, y],
                })

    submit = _submit(_matrix(frame))
    frame = ab.click(env, (submit[1], submit[0]))
    actions.append({"kind": "submit", "xy": list(submit)})
    progressed = int(frame.levels_completed) > start_level or frame.state == GameState.WIN
    return {
        "path": path,
        "progressed": progressed,
        "level": int(frame.levels_completed),
        "state": str(frame.state),
        "codes": {key: list(value) for key, value in codes.items()},
        "actions": actions,
        "action_count": len(actions),
    }


def main() -> None:
    variants = []
    selected = None
    verification = []
    for path in PATHS:
        result = run_path(path)
        variants.append(result)
        if result["progressed"]:
            checks = [run_path(path), run_path(path)]
            if all(check["progressed"] for check in checks):
                selected = path
                verification = checks
                break

    status = "PROMOTED" if selected is not None else "RESIDUAL"
    result = {
        "status": status,
        "classification": "WARRANTED POSITIVE" if selected else "WARRANTED NEGATIVE",
        "hypothesis": (
            "scale-normalize the 56-pixel glyph to the transported 14-pixel mover, "
            "recover its exact 14+16 complement relation, then compile the only "
            "collision-free six-step programs consisting of one scale, four down, "
            "and one left action"
        ),
        "paths": list(PATHS),
        "variants": variants,
        "selected": selected,
        "verification": verification,
        "independent_replay_count": len(verification),
        "model_calls": 0,
        "source_inspection": False,
        "claim_boundary": (
            "exact public tn36 G4 after qualified G1-G3 entry; three earned path "
            "orderings only, derived from visible scale-normalized complement geometry "
            "and wall collision; terminal progress is the independent oracle"
        ),
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True), flush=True)
    print(f"ARC3_PUBLIC_G4_SCALE_NORMALIZED_DOCKING={status}", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()

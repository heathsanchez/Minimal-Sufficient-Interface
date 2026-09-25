from __future__ import annotations

import json
import os
from pathlib import Path

from arcengine import GameState

import arc3_public_all_blue_to_gray_g2 as ab
import arc3_public_panel_correspondence_g3 as g3
from metalogic_arc3.semantic_path import SemanticPathSession, _bar_rows, _matrix, _source_bits, _submit


OUT = Path(os.environ.get(
    "OUTDIR", "evidence/arc3-public-g4-four-control-docking"
)).resolve()
OUT.mkdir(parents=True, exist_ok=True)

PROBES = {"S": (15, 58), "D": (25, 58), "I": (35, 58)}
PATHS = (
    "SLDDDD", "SDLDDD", "SDDLDD", "LSDDDD",
    "DSLDDD", "DSDLDD", "LDSDDD", "DLSDDD",
)


def enter_g4():
    env, _ = g3.enter_level3()
    frame = env.observation_space
    session = SemanticPathSession.start(frame)
    while session.phase != "done":
        x, y = session.next_action(frame)
        frame = ab.click(env, (y, x))
    return env, frame


def run_path(path):
    env, frame = enter_g4()
    start_level = int(frame.levels_completed)
    codes = {"L": _source_bits(_matrix(frame))}
    for label, (x, y) in PROBES.items():
        frame = ab.click(env, (y, x))
        codes[label] = _source_bits(_matrix(frame))

    targets = _bar_rows(_matrix(frame), "right")
    columns = [codes[label] for label in path]
    actions = len(PROBES)
    for row_index, target_row in enumerate(targets):
        for col_index, (x, y) in enumerate(target_row):
            desired = columns[col_index][row_index]
            current = 1 if _matrix(frame)[y][x] == 5 else 0
            if current != desired:
                frame = ab.click(env, (y, x))
                actions += 1
    submit = _submit(_matrix(frame))
    frame = ab.click(env, (submit[1], submit[0]))
    actions += 1
    return {
        "path": path,
        "progressed": int(frame.levels_completed) > start_level or frame.state == GameState.WIN,
        "level": int(frame.levels_completed),
        "state": str(frame.state),
        "codes": {key: list(value) for key, value in sorted(codes.items())},
        "action_count": actions,
    }


def main():
    variants = []
    selected = None
    verification = []
    for path in PATHS:
        row = run_path(path)
        variants.append(row)
        if row["progressed"]:
            checks = [run_path(path), run_path(path)]
            if all(check["progressed"] for check in checks):
                selected = path
                verification = checks
                break
    result = {
        "status": "PROMOTED" if selected else "RESIDUAL",
        "classification": "WARRANTED POSITIVE" if selected else "WARRANTED NEGATIVE",
        "hypothesis": (
            "scale-normalize the large transported mover, then route it through the wall "
            "with one scale action, four down actions, and the initially selected vertical "
            "left control; the singleton is an identity/anchor control, not left"
        ),
        "paths": list(PATHS),
        "variants": variants,
        "selected": selected,
        "verification": verification,
        "independent_replay_count": len(verification),
        "model_calls": 0,
        "source_inspection": False,
        "claim_boundary": (
            "exact public tn36 G4 after qualified G1-G3 entry; all and only eight "
            "collision-free orderings of the earned action multiset, with four visible controls"
        ),
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True), flush=True)
    print(f"ARC3_PUBLIC_G4_FOUR_CONTROL_DOCKING={result['status']}", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()

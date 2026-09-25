from __future__ import annotations

import json
import os
from pathlib import Path

from arcengine import GameState

import arc3_public_all_blue_to_gray_g2 as ab
from arc3_public_g5_control_separator import enter_g5, source_signature
from metalogic_arc3.semantic_path import _bar_rows, _matrix, _submit


OUT = Path(os.environ.get("OUTDIR", "evidence/arc3-public-g5-factorized-docking")).resolve()
OUT.mkdir(parents=True, exist_ok=True)

CONTROLS = {
    "I": (5, 58),
    "S": (15, 58),
    "D": (25, 58),
    "X": (35, 58),
    "T": (45, 58),
}
PATH = "XDDDTS"


def run_path(path=PATH, selector_port=1):
    env, frame = enter_g5()
    start_level = int(frame.levels_completed)
    raw_codes = {}
    for label, (x, y) in CONTROLS.items():
        frame = ab.click(env, (y, x))
        raw_codes[label] = source_signature(_matrix(frame))
    codes = {}
    for label, rows in raw_codes.items():
        column = selector_port if label == "T" else 0
        codes[label] = tuple(1 if row[column] == 5 else 0 for row in rows)
    targets = _bar_rows(_matrix(frame), "right")
    columns = [codes[label] for label in path]
    actions = len(CONTROLS)
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
        "raw_codes": raw_codes,
        "action_count": actions,
        "selector_port": selector_port,
    }


def main():
    negatives = [
        run_path("TIXDDD", selector_port=1),
        run_path("TIXDDD", selector_port=0),
        run_path("XDDDDD", selector_port=1),
    ]
    variants = [run_path(selector_port=port) for port in (1, 0)]
    primary = next((row for row in variants if row["progressed"]), variants[0])
    verification = (
        [run_path(selector_port=primary["selector_port"]), run_path(selector_port=primary["selector_port"])]
        if primary["progressed"] else []
    )
    promoted = primary["progressed"] and all(row["progressed"] for row in verification)
    result = {
        "status": "PROMOTED" if promoted else "RESIDUAL",
        "classification": "WARRANTED POSITIVE" if promoted else "WARRANTED NEGATIVE",
        "hypothesis": (
            "compile the visible endpoint transformation as rotate, descend three cells, "
            "recolor to color 15, then grow; project the non-monochromatic recolor response "
            "through its visibly active middle source port"
        ),
        "primary": primary,
        "variants": variants,
        "qualified_negatives": negatives,
        "verification": verification,
        "independent_replay_count": len(verification),
        "action_budget_per_replay": 30,
        "model_calls": 0,
        "source_inspection": False,
        "claim_boundary": (
            "exact public tn36 G5 after qualified G1-G4; endpoint-transform program, both "
            "binary projections of the only non-monochromatic response, and two independent replays"
        ),
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True), flush=True)
    print(f"ARC3_PUBLIC_G5_FACTORIZED_DOCKING={result['status']}", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()

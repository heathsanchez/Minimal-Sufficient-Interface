from __future__ import annotations

import json
import os
from pathlib import Path

from arcengine import GameState

import arc3_public_all_blue_to_gray_g2 as ab
import arc3_public_panel_correspondence_g3 as g3
from arc3_public_online_scale_normalized_g4 import execute_session
from metalogic_arc3.semantic_path import _bar_rows, _matrix, _selector_controls, _source_bits, _submit


OUT = Path(os.environ.get("OUTDIR", "evidence/arc3-public-g6-paired-route")).resolve()
OUT.mkdir(parents=True, exist_ok=True)
ROUTE = "RRRRUULLUUUL"


def enter_g6():
    env, _ = g3.enter_level3()
    frame = env.observation_space
    for _ in range(3):
        frame, _, _ = execute_session(env, frame)
    if int(frame.levels_completed) != 5:
        raise AssertionError("qualified G6 entry drifted")
    return env, frame


def run_once(operator="or"):
    env, frame = enter_g6()
    start_level = int(frame.levels_completed)
    codes = {}
    controls = _selector_controls(_matrix(frame))
    for (x, y), label in controls:
        frame = ab.click(env, (y, x))
        codes[label] = _source_bits(_matrix(frame))
    pairs = [ROUTE[index:index + 2] for index in range(0, len(ROUTE), 2)]
    functions = {
        "or": lambda left, right: left | right,
        "and": lambda left, right: left & right,
        "xor": lambda left, right: left ^ right,
    }
    if operator == "idempotent_xor":
        columns = [
            codes[pair[0]] if pair[0] == pair[1]
            else tuple(left ^ right for left, right in zip(codes[pair[0]], codes[pair[1]]))
            for pair in pairs
        ]
    else:
        combine = functions[operator]
        columns = [tuple(combine(left, right) for left, right in zip(codes[pair[0]], codes[pair[1]])) for pair in pairs]
    targets = _bar_rows(_matrix(frame), "right")
    actions = len(controls)
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
        "route": ROUTE,
        "pairs": pairs,
        "operator": f"rowwise_{operator}",
        "codes": {key: list(value) for key, value in sorted(codes.items())},
        "columns": [list(column) for column in columns],
        "progressed": int(frame.levels_completed) > start_level or frame.state == GameState.WIN,
        "level": int(frame.levels_completed),
        "state": str(frame.state),
        "action_count": actions,
    }


def main():
    variants = [run_once(operator) for operator in ("or", "and", "xor", "idempotent_xor")]
    primary = next((row for row in variants if row["progressed"]), variants[0])
    operator = primary["operator"].removeprefix("rowwise_")
    verification = [run_once(operator), run_once(operator)] if primary["progressed"] else []
    promoted = primary["progressed"] and all(row["progressed"] for row in verification)
    result = {
        "status": "PROMOTED" if promoted else "RESIDUAL",
        "classification": "WARRANTED POSITIVE" if promoted else "WARRANTED NEGATIVE",
        "hypothesis": (
            "the 12-step visible maze route factors into six consecutive pairs, and each "
            "target column is a set-theoretic rowwise composition of the two direction-incidence codes"
        ),
        "primary": primary,
        "variants": variants,
        "verification": verification,
        "independent_replay_count": len(verification),
        "action_budget_per_replay": 30,
        "model_calls": 0,
        "source_inspection": False,
        "claim_boundary": (
            "exact public tn36 G6; one earned route partition, union/intersection/"
            "symmetric-difference, and equality-preserving turn cancellation only"
        ),
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True), flush=True)
    print(f"ARC3_PUBLIC_G6_PAIRED_ROUTE={result['status']}", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()

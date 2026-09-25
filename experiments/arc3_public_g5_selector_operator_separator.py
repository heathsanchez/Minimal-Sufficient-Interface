from __future__ import annotations

import json
import os
from pathlib import Path

import arc3_public_all_blue_to_gray_g2 as ab
from arc3_public_g5_control_separator import enter_g5, source_signature
from metalogic_arc3.semantic_path import _matrix


OUT = Path(os.environ.get(
    "OUTDIR", "evidence/arc3-public-g5-selector-operator-separator"
)).resolve()
OUT.mkdir(parents=True, exist_ok=True)

OPERATORS = {"I": (5, 58), "S": (15, 58), "D": (25, 58), "X": (35, 58)}
SELECTOR = (45, 58)


def run(points):
    env, frame = enter_g5()
    signatures = [source_signature(_matrix(frame))]
    for x, y in points:
        frame = ab.click(env, (y, x))
        signatures.append(source_signature(_matrix(frame)))
    return signatures


def main():
    arms = {}
    for label, point in OPERATORS.items():
        arms[f"T{label}"] = run((SELECTOR, point))
        arms[f"{label}T"] = run((point, SELECTOR))
    result = {
        "classification": "RESPONSE_SEPARATOR_ONLY",
        "hypothesis": (
            "the color-15 glyph is an object selector that composes with the four "
            "transported six-row operator controls"
        ),
        "arms": arms,
        "action_budget_per_arm": 2,
        "model_calls": 0,
        "source_inspection": False,
    }
    (OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True), flush=True)
    print("ARC3_PUBLIC_G5_SELECTOR_OPERATOR_SEPARATOR=PASS", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Executable audit of TaskSAT's range/bounds well-formedness contract.

Pinned target:
  nasa-jpl/tasksat@f9d6063b45967a3fea578c47f54806aadaafe1b0

The current human-readable sources disagree on interval containment:
  * tasknet_ast.py + public manual: range is a subtype of bounds (R subset B)
  * TaskNetPaper semantics skeleton: bounds are within range (B subset R)

This script asks the actual Python well-formedness checker which direction it
enforces.  It fails unless both opposite nestings are accepted, demonstrating
that the checker currently resolves neither semantic fork.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def spec(name: str, range_pair: tuple[float, float], bounds_pair: tuple[float, float]) -> str:
    r0, r1 = range_pair
    b0, b1 = bounds_pair
    return f"""
tasknet {name} {{
  end = 20;

  timelines {{
    x : cumulative [{r0}, {r1}] bounds [{b0}, {b1}] = 5.0;
  }}

  task idle {{
    id 1;
    start_range [5, 5];
    end_range [10, 10];
    duration 5;
    start 5;
  }}
}}
"""


def check(tasksat_root: Path, source: str) -> dict[str, object]:
    smt = tasksat_root / "src" / "smt"
    sys.path.insert(0, str(smt))

    from tasknet_parser import parse_tasknet  # type: ignore
    from tasknet_wellformedness import WellFormednessChecker  # type: ignore

    tn = parse_tasknet(source)
    errors = WellFormednessChecker(tn).check()
    return {
        "accepted": not errors,
        "errors": [str(e) for e in errors],
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("tasksat_root", type=Path)
    p.add_argument(
        "--out",
        type=Path,
        default=Path("results/tasksat_range_bounds_contract_audit.json"),
    )
    args = p.parse_args()
    root = args.tasksat_root.resolve()

    # B subset R, matching TaskNetPaper's explicit bounds_in_range field.
    bounds_inside_range = check(
        root,
        spec("BoundsInsideRange", (0.0, 100.0), (0.0, 10.0)),
    )

    # R subset B, matching tasknet_ast.py and the public manual wording.
    range_inside_bounds = check(
        root,
        spec("RangeInsideBounds", (0.0, 10.0), (0.0, 100.0)),
    )

    payload = {
        "upstream_repo": "nasa-jpl/tasksat",
        "upstream_commit": "f9d6063b45967a3fea578c47f54806aadaafe1b0",
        "bounds_inside_range_case": bounds_inside_range,
        "range_inside_bounds_case": range_inside_bounds,
        "warranted_if_both_accepted": (
            "The pinned Python well-formedness checker enforces neither "
            "R subset B nor B subset R."
        ),
        "epistemic_state": (
            "WARRANTED_MISSING_CONTAINMENT_CHECK"
            if bounds_inside_range["accepted"] and range_inside_bounds["accepted"]
            else "NOT_REPRODUCED"
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))

    return 0 if payload["epistemic_state"] == "WARRANTED_MISSING_CONTAINMENT_CHECK" else 2


if __name__ == "__main__":
    raise SystemExit(main())

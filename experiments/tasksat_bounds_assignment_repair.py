#!/usr/bin/env python3
"""Apply the smallest candidate TaskSAT repair in a disposable checkout.

The repair re-applies the declared bounds clamp after value assignments on
bounded cumulative and rate timelines.  It does not mutate the upstream repo;
CI applies it only to the pinned checkout used by this audit.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from tasksat_bounds_assignment_audit import run_upstream_property_check


NONRATE_MARKER = "                    # Track numeric timeline evolution\n"
RATE_MARKER = "                    # Track rate timeline value evolution\n"

NONRATE_REPAIR = """                    # Semantic-boundary repair: assignments are computed values too.
                    # Re-apply type-level bounds after any assignment override.
                    if bounds_opt is not None:
                        expr = If(expr < low_bnd, low_bnd,
                                  If(expr > high_bnd, high_bnd, expr))

"""

RATE_REPAIR = """                    # Semantic-boundary repair: assignments are computed values too.
                    # Re-apply type-level bounds after any assignment override.
                    if bounds_opt is not None:
                        value_expr = If(value_expr < low_bnd, low_bnd,
                                        If(value_expr > high_bnd, high_bnd, value_expr))

"""


def apply_candidate_repair(tasksat_root: Path) -> dict[str, int]:
    path = tasksat_root / "src" / "smt" / "tasknet_smt.py"
    source = path.read_text()

    nonrate_count = source.count(NONRATE_MARKER)
    rate_count = source.count(RATE_MARKER)
    if nonrate_count != 1:
        raise AssertionError(f"expected one non-rate insertion marker, found {nonrate_count}")
    if rate_count != 1:
        raise AssertionError(f"expected one rate insertion marker, found {rate_count}")

    patched = source.replace(NONRATE_MARKER, NONRATE_REPAIR + NONRATE_MARKER, 1)
    patched = patched.replace(RATE_MARKER, RATE_REPAIR + RATE_MARKER, 1)
    compile(patched, str(path), "exec")
    path.write_text(patched)
    return {"nonrate_insertions": 1, "rate_insertions": 1}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tasksat_root", type=Path)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("results/tasksat_bounds_assignment_repair.json"),
    )
    args = parser.parse_args()
    root = args.tasksat_root.resolve()

    patch_info = apply_candidate_repair(root)

    # Ensure the import sees the just-patched checkout.
    sys.modules.pop("tasknet_smt", None)
    result = run_upstream_property_check(root)
    repaired = result.get("status") == "holds"

    payload = {
        "candidate_repair": "re-clamp bounded numeric values after assignment overrides",
        "patch_info": patch_info,
        "property_after_repair": result,
        "repair_result": "WARRANTED_FOR_MINIMIZED_WITNESS" if repaired else "REJECTED",
        "scope": "Disposable pinned TaskSAT checkout only; no upstream source was changed.",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if repaired else 3


if __name__ == "__main__":
    raise SystemExit(main())

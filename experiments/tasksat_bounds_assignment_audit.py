#!/usr/bin/env python3
"""Reproduce the smallest TaskSAT numeric-assignment semantic boundary.

This audit is intentionally narrow.  It does not claim TaskSAT is unsound.
It checks one commuting square at one pinned upstream revision:

    bounded numeric assignment
      -> executable Lean semantics
      -> Python/Z3 encoder semantics

For an assignment-only transition, the executable Lean semantics applies the
assignment and then clamps the resulting numeric value.  The Python/Z3 encoder
at the pinned revision clamps the pre-assignment value and then lets the
assignment override that clamp.

The witness is deliberately minimal:
    old = 5, bounds = [0, 10], assignment = 20.

Reference/Lean result: 10.
Current Python/Z3 result: 20.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

TASKSAT_COMMIT = "f9d6063b45967a3fea578c47f54806aadaafe1b0"

FIXTURE = r"""
tasknet BoundsAssignmentAudit {
  end = 20;

  timelines {
    x : cumulative [0.0, 100.0] bounds [0.0, 10.0] = 5.0;
  }

  task assign_high {
    id 1;
    start_range [5, 5];
    end_range [10, 10];
    duration 5;
    start 5;

    impacts {
      pre {
        x = 20.0;
      }
    }
  }

  properties {
    prop bounds_respected: always (x <= 10.0);
  }
}
"""


def clamp(value: float, bounds: tuple[float, float]) -> float:
    low, high = bounds
    return low if value < low else high if value > high else value


def lean_reference_assignment_only(
    old_value: float,
    bounds: tuple[float, float],
    assignment: float | None,
) -> float:
    """Executable-Lean ordering for the assignment-only slice: assign, then clamp."""
    start_value = assignment if assignment is not None else old_value
    return clamp(start_value, bounds)


def python_encoder_assignment_only(
    old_value: float,
    bounds: tuple[float, float],
    assignment: float | None,
) -> float:
    """Pinned Python/Z3 ordering for the same slice: clamp, then assignment overrides."""
    clamped = clamp(old_value, bounds)
    return assignment if assignment is not None else clamped


def source_lock(tasksat_root: Path) -> dict[str, str]:
    """Fail closed if the pinned source no longer has the audited transition shapes."""
    smt_path = tasksat_root / "src" / "smt" / "tasknet_smt.py"
    lean_path = tasksat_root / "src" / "lean" / "TaskNetExec" / "TaskNet" / "Semantics.lean"
    ast_path = tasksat_root / "src" / "smt" / "tasknet_ast.py"

    smt = smt_path.read_text()
    lean = lean_path.read_text()
    ast = ast_path.read_text()

    smt_needles = [
        "raw = cur + delta",
        "clamped = If(raw < low_bnd, low_bnd,",
        "expr = clamped",
        "Apply assignments (they override the delta-based value)",
        "expr = If(zi == s, val, expr)",
    ]
    lean_needles = [
        "let startV :=",
        "match asgn? with",
        "| some v => v",
        "let resultV :=",
        "match bnds.get? tl with",
        "Value.realVal (clamp r low high)",
    ]
    ast_needles = [
        "`bounds` is the timeline\'s type",
        "computed values are",
        "clamped into it",
    ]

    for needle in smt_needles:
        if needle not in smt:
            raise AssertionError(f"SMT source lock failed: missing {needle!r}")
    for needle in lean_needles:
        if needle not in lean:
            raise AssertionError(f"Lean source lock failed: missing {needle!r}")
    for needle in ast_needles:
        if needle not in ast:
            raise AssertionError(f"AST semantic-contract lock failed: missing {needle!r}")

    return {
        "smt": str(smt_path),
        "lean": str(lean_path),
        "ast": str(ast_path),
    }


def run_upstream_property_check(tasksat_root: Path) -> dict[str, object]:
    """Ask the pinned TaskSAT encoder whether bounds_respected holds."""
    smt_dir = tasksat_root / "src" / "smt"
    sys.path.insert(0, str(smt_dir))

    from tasknet_parser import parse_tasknet_file  # type: ignore
    from tasknet_smt import TaskNetTL  # type: ignore
    from tasknet_transforms import apply_transforms  # type: ignore
    from tasknet_wellformedness import check_wellformedness  # type: ignore

    with tempfile.TemporaryDirectory(prefix="tasksat-semantic-audit-") as tmp:
        fixture_path = Path(tmp) / "bounds_assignment_audit.tn"
        fixture_path.write_text(FIXTURE)
        tn = parse_tasknet_file(str(fixture_path))
        tn, transform_info = apply_transforms(tn)
        if not check_wellformedness(tn):
            raise AssertionError("audit fixture was rejected by TaskSAT well-formedness")

        enc = TaskNetTL(tn, error_trace=False, use_optimization=False)
        results, _violations = enc.check_temporal_properties(property_timeout_ms=60_000)
        matches = [r for r in results if r.get("name") == "bounds_respected"]
        if len(matches) != 1:
            raise AssertionError(f"expected exactly one bounds_respected result, got {matches!r}")

        entry = matches[0]
        return {
            "status": entry.get("status"),
            "formula": entry.get("formula"),
            "violation_zones": entry.get("violation_zones", []),
            "transform_info": str(transform_info),
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tasksat_root", type=Path)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("results/tasksat_bounds_assignment_audit.json"),
    )
    args = parser.parse_args()

    root = args.tasksat_root.resolve()
    locks = source_lock(root)

    old_value = 5.0
    bounds = (0.0, 10.0)
    assignment = 20.0
    lean_value = lean_reference_assignment_only(old_value, bounds, assignment)
    python_formula_value = python_encoder_assignment_only(old_value, bounds, assignment)

    if lean_value != 10.0 or python_formula_value != 20.0:
        raise AssertionError("the minimized algebraic witness no longer separates the two orderings")

    upstream_result = run_upstream_property_check(root)
    reproduced = upstream_result["status"] == "violated"

    payload = {
        "audit": "TaskSAT bounded numeric assignment semantic boundary",
        "epistemic_state": "WARRANTED_IMPLEMENTATION_DIVERGENCE" if reproduced else "SUPERSEDED_OR_NOT_REPRODUCED",
        "upstream_repo": "nasa-jpl/tasksat",
        "upstream_commit": TASKSAT_COMMIT,
        "source_locks": locks,
        "witness": {
            "timeline_kind": "cumulative",
            "range": [0.0, 100.0],
            "bounds": list(bounds),
            "old_value": old_value,
            "assignment": assignment,
            "additive_delta": 0.0,
        },
        "reference_executable_lean_value": lean_value,
        "pinned_python_formula_value": python_formula_value,
        "upstream_property": upstream_result,
        "claim_boundary": {
            "warranted": "The pinned executable Lean transition and pinned Python/Z3 numeric transition use opposite assignment/clamp order, and the minimized TaskSAT property check reproduces an observable verdict difference.",
            "unknown": "Which ordering the TaskSAT authors intend as canonical, and whether either exactly matches MEXEC semantics.",
            "not_claimed": "This audit does not claim that Z3, Lean, TaskSAT as a whole, or MEXEC is unsound.",
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))

    if not reproduced:
        print("Expected the pinned Python/Z3 encoder to violate bounds_respected; it did not.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Contract-compliant TaskSAT assignment/clamp validity separator.

Public/current AST semantics say R is effectively a subtype of B.

  R=[10,100], B=[0,100], initial=50, PRE assignment=110.

Current Python/Z3 keeps 110, violating R => no valid schedule.
The candidate re-clamp repair maps 110 -> 100, which is in R => valid schedule.

Run before and after the disposable repair and require UNSAT then SAT.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SPEC = r"""
tasknet ContractCompliantAssignmentClamp {
  end = 20;

  timelines {
    x : cumulative [10.0, 100.0] bounds [0.0, 100.0] = 50.0;
  }

  task assign_high {
    id 1;
    start_range [5, 5];
    end_range [10, 10];
    duration 5;
    start 5;

    impacts {
      pre {
        x = 110.0;
      }
    }
  }
}
"""


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("tasksat_root", type=Path)
    p.add_argument("--expect", choices=["sat", "unsat"], required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()

    root = args.tasksat_root.resolve()
    sys.path.insert(0, str(root / "src" / "smt"))

    from tasknet_parser import parse_tasknet  # type: ignore
    from tasknet_smt import TaskNetTL  # type: ignore
    from tasknet_wellformedness import WellFormednessChecker  # type: ignore

    tn = parse_tasknet(SPEC)
    errors = WellFormednessChecker(tn).check()
    if errors:
        status = "wellformedness-failed"
    else:
        enc = TaskNetTL(
            tn,
            error_trace=False,
            use_optimization=False,
            track=False,
            timeout_ms=60_000,
        )
        model, _ = enc.solve(analyze_core=False)
        status = "sat" if model is not None else "unsat"

    payload = {
        "upstream_repo": "nasa-jpl/tasksat",
        "upstream_commit": "f9d6063b45967a3fea578c47f54806aadaafe1b0",
        "contract": "R_subset_B",
        "range": [10.0, 100.0],
        "bounds": [0.0, 100.0],
        "assignment": 110.0,
        "wellformed": not errors,
        "wellformedness_errors": [str(e) for e in errors],
        "solver_status": status,
        "expected": args.expect,
        "matches_expected": status == args.expect,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if status == args.expect else 2


if __name__ == "__main__":
    raise SystemExit(main())

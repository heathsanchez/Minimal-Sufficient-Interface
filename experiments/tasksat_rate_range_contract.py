#!/usr/bin/env python3
"""Minimal executable separator for TaskSAT rate-timeline interval semantics.

Pinned TaskSAT:
  nasa-jpl/tasksat@f9d6063b45967a3fea578c47f54806aadaafe1b0

The public manual writes:
  battery : rate [-5,5] bounds [0,100] = 50 initial_rate = -0.1

and explicitly labels [-5,5] "Rate bounds" and [0,100] "Value bounds".

The Python SMT encoder instead stores the first interval as tl.range and
constrains the VALUE variable at every zone to lie in it.  This script asks the
actual pinned solver to decide the manual example and a one-token semantic
control where the first interval is changed to [0,100].
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def make_spec(name: str, first_interval: tuple[float, float]) -> str:
    lo, hi = first_interval
    return f"""
tasknet {name} {{
  end = 20;

  timelines {{
    battery : rate [{lo}, {hi}] bounds [0.0, 100.0] = 50.0 initial_rate = -0.1;
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


def evaluate(tasksat_root: Path, source: str) -> dict[str, object]:
    sys.path.insert(0, str(tasksat_root / "src" / "smt"))

    from tasknet_parser import parse_tasknet  # type: ignore
    from tasknet_smt import TaskNetTL  # type: ignore
    from tasknet_wellformedness import WellFormednessChecker  # type: ignore

    tn = parse_tasknet(source)
    errors = WellFormednessChecker(tn).check()
    if errors:
        return {
            "wellformed": False,
            "wellformedness_errors": [str(e) for e in errors],
            "solver_status": "not-run",
        }

    enc = TaskNetTL(
        tn,
        error_trace=False,
        use_optimization=False,
        track=False,
        timeout_ms=60_000,
    )
    value0 = str(enc.numeric_tl_zone["battery"][2][0])
    rate0 = str(enc.rate_tl_rate_zone["battery"][0])
    model, _ = enc.solve(analyze_core=False)
    return {
        "wellformed": True,
        "wellformedness_errors": [],
        "solver_status": "sat" if model is not None else "unsat",
        "encoded_value_zone0": value0,
        "encoded_rate_zone0": rate0,
        "declared_range": [
            tn.timelines[0].range.low,  # type: ignore[attr-defined]
            tn.timelines[0].range.high,  # type: ignore[attr-defined]
        ],
        "declared_bounds": [
            tn.timelines[0].bounds.low,  # type: ignore[attr-defined]
            tn.timelines[0].bounds.high,  # type: ignore[attr-defined]
        ],
        "declared_initial_value": tn.timelines[0].initial,  # type: ignore[attr-defined]
        "declared_initial_rate": tn.timelines[0].initial_rate,  # type: ignore[attr-defined]
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("tasksat_root", type=Path)
    p.add_argument(
        "--out",
        type=Path,
        default=Path("results/tasksat_rate_range_contract.json"),
    )
    args = p.parse_args()
    root = args.tasksat_root.resolve()

    manual_example = evaluate(root, make_spec("ManualRateContract", (-5.0, 5.0)))
    value_range_control = evaluate(root, make_spec("ValueRangeControl", (0.0, 100.0)))

    reproduced = (
        manual_example["wellformed"] is True
        and manual_example["solver_status"] == "unsat"
        and value_range_control["wellformed"] is True
        and value_range_control["solver_status"] == "sat"
    )

    payload = {
        "upstream_repo": "nasa-jpl/tasksat",
        "upstream_commit": "f9d6063b45967a3fea578c47f54806aadaafe1b0",
        "manual_documented_interpretation": {
            "first_interval": "rate bounds",
            "bounds_interval": "value bounds / clamp interval",
            "example": "rate [-5,5] bounds [0,100] = 50 initial_rate = -0.1",
        },
        "manual_example_under_python_encoder": manual_example,
        "value_range_control_under_python_encoder": value_range_control,
        "epistemic_state": (
            "WARRANTED_RATE_INTERVAL_DOCUMENTATION_IMPLEMENTATION_DIVERGENCE"
            if reproduced
            else "NOT_REPRODUCED"
        ),
        "claim_boundary": {
            "warranted_if_reproduced": (
                "At the pinned revision, the public manual's explicit 'rate bounds' "
                "example is well-formed but UNSAT under the Python/Z3 encoding, while "
                "changing only the first interval to include the initial VALUE makes "
                "the control SAT. This is consistent with the implementation treating "
                "the first interval as a value admissibility range, not a rate bound."
            ),
            "unknown": (
                "Which interpretation is intended to match MEXEC, and whether the "
                "manual or the current Python/SMT semantics should change."
            ),
            "not_claimed": (
                "This does not by itself establish that either interpretation is the "
                "correct MEXEC semantics."
            ),
        },
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if reproduced else 2


if __name__ == "__main__":
    raise SystemExit(main())

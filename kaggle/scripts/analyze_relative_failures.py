#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


def action_text(step):
    action = step.get("action", [])
    return ":".join("" if x is None else str(x) for x in action)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", type=Path)
    ap.add_argument("--focus", nargs="*", default=[])
    args = ap.parse_args()

    files = sorted(args.root.rglob("*.continuations.json"))
    focus = set(args.focus)
    out = {"schema": "arc3.relative-progress-failure-analysis@1", "games": []}
    aggregate_reasons = Counter()
    aggregate_steps = Counter()
    aggregate_expected_actual = Counter()

    for path in files:
        game = path.name.removesuffix(".continuations.json")
        if focus and game not in focus:
            continue
        data = json.loads(path.read_text())
        caps = data.get("relative_capabilities", {})
        residuals = [
            r for r in data.get("residuals", [])
            if str(r.get("reason", "")).startswith("relative_")
        ]
        aggregate_reasons.update(r.get("reason", "UNKNOWN") for r in residuals)

        cap_rows = []
        for cid, cap in caps.items():
            steps = cap.get("steps", [])
            cap_rows.append({
                "id": cid,
                "source_levels": cap.get("source_levels", []),
                "target_delta": cap.get("target_delta"),
                "length": len(steps),
                "actions": [action_text(s) for s in steps],
                "interfaces": [s.get("interface") for s in steps],
                "effects": [{
                    "board_relation": s.get("board_relation"),
                    "frame_relation": s.get("frame_relation"),
                    "progress": bool(s.get("progress")),
                } for s in steps],
                "support_count": len(cap.get("support_refs", [])),
            })

        mismatch_rows = []
        for r in residuals:
            if r.get("reason") != "relative_progress_separator":
                continue
            step = int(r.get("step", -1))
            aggregate_steps[step] += 1
            expected = r.get("expected", {})
            actual = r.get("actual", {})
            key = (
                expected.get("board_relation"),
                actual.get("board_relation"),
                expected.get("frame_relation"),
                actual.get("frame_relation"),
                bool(expected.get("progress")),
                bool(actual.get("progress")),
            )
            aggregate_expected_actual[str(key)] += 1
            mismatch_rows.append({
                "capability": r.get("capability"),
                "step": step,
                "expected": expected,
                "actual": actual,
            })

        out["games"].append({
            "game": game,
            "stats": data.get("stats", {}),
            "history_depth": data.get("history_depth"),
            "capabilities": cap_rows,
            "relative_residuals": residuals,
            "mismatches": mismatch_rows,
        })

    out["aggregate"] = {
        "relative_reasons": dict(aggregate_reasons),
        "mismatch_steps": {str(k): v for k, v in sorted(aggregate_steps.items())},
        "effect_confusions": dict(aggregate_expected_actual),
    }
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

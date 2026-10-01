"""V8 support-preserving audit for the ka59-L1 applicability residual.

Purpose:
- distinguish genuine error correction from reduced coverage/abstention;
- compare V5 -> V6(same_action_run) -> V7(+since_reset);
- preserve the V4 changed-effect branch exactly;
- inspect only the already-earned calibration no-op collision when judging
  latent-state signal.

This is a diagnostic audit on the already-observed split, not fresh promotion
authority.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from arc3_relational_applicability_v5 import retrace
from arc3_latent_control_tournament_v6 import traced, train
from arc3_typed_local_refinement_v4 import learn


def combined_trace(path: Path):
    v5 = retrace(path)
    v6 = traced(path)
    if len(v5) != len(v6):
        raise AssertionError(f"trace length mismatch for {path.name}: {len(v5)} != {len(v6)}")
    out = []
    for i, (a, b) in enumerate(zip(v5, v6)):
        if a[:6] != b[:6]:
            raise AssertionError(f"trace row mismatch for {path.name} row {i}")
        # (lev, coarse, fine, state, y, effect, app_features, control)
        out.append(a + (b[6],))
    return out


def state(pred, actual):
    if pred is None:
        return "abstain"
    return "correct" if pred == actual else "wrong"


def transition_summary(records, left_key, right_key):
    cats = Counter()
    left_known = left_wrong = 0
    right_known = right_wrong = 0
    common = common_left_wrong = common_right_wrong = 0

    for r in records:
        actual = r["actual"]
        left = r[left_key]
        right = r[right_key]
        ls = state(left, actual)
        rs = state(right, actual)
        cats[f"{ls}_to_{rs}"] += 1

        if left is not None:
            left_known += 1
            left_wrong += left != actual
        if right is not None:
            right_known += 1
            right_wrong += right != actual
        if left is not None and right is not None:
            common += 1
            common_left_wrong += left != actual
            common_right_wrong += right != actual

    wrong_to_correct = cats["wrong_to_correct"]
    wrong_to_abstain = cats["wrong_to_abstain"]
    correct_to_wrong = cats["correct_to_wrong"]

    if wrong_to_correct == 0 and right_wrong < left_wrong and wrong_to_abstain > 0:
        classification = "ABSTENTION_ONLY"
    elif wrong_to_correct > 0 and correct_to_wrong == 0:
        classification = "GENUINE_CORRECTION_CANDIDATE"
    elif wrong_to_correct > 0:
        classification = "MIXED_CORRECTION_AND_REGRESSION"
    elif right_wrong == left_wrong:
        classification = "NO_ERROR_CONTRACTION"
    else:
        classification = "OTHER"

    return {
        "left": {
            "known": left_known,
            "wrong": left_wrong,
            "coverage": left_known / len(records) if records else 0,
            "error_rate_on_known": left_wrong / left_known if left_known else 0,
        },
        "right": {
            "known": right_known,
            "wrong": right_wrong,
            "coverage": right_known / len(records) if records else 0,
            "error_rate_on_known": right_wrong / right_known if right_known else 0,
        },
        "common_support": {
            "cells": common,
            "left_wrong": common_left_wrong,
            "right_wrong": common_right_wrong,
        },
        "transitions": dict(sorted(cats.items())),
        "wrong_to_correct": wrong_to_correct,
        "wrong_to_abstain": wrong_to_abstain,
        "correct_to_wrong": correct_to_wrong,
        "classification": classification,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--game-prefix", default="ka59")
    ap.add_argument("--target-level", type=int, default=1)
    args = ap.parse_args()

    games = defaultdict(list)
    for p in sorted(args.events_dir.glob("*_events.jsonl")):
        game = p.name.split("_p", 1)[0]
        if args.game_prefix and not game.startswith(args.game_prefix):
            continue
        games[game].append((p.name, combined_trace(p)))

    if not games:
        raise SystemExit(f"no games matched prefix {args.game_prefix!r}")

    all_records = []
    noop_records = []
    calibration = {}

    for game, labelled in sorted(games.items()):
        cal = [tr for i, (_, tr) in enumerate(labelled) if i % 2 == 0]
        ev = [(name, tr) for i, (name, tr) in enumerate(labelled) if i % 2 == 1]
        target = args.target_level

        coarse = learn(cal, target, 1, 4)
        effect_bad = set()
        noop_bad = set()
        for tr in cal:
            for row in tr:
                lev, c, _, _, y, _, _, _ = row
                if lev != target or c not in coarse or coarse[c] == y:
                    continue
                if y[0] == "same" or coarse[c][0] == "same":
                    noop_bad.add(c)
                else:
                    effect_bad.add(c)

        me = learn(cal, target, 2, 5)
        ma = learn(cal, target, 6, 4)
        mr = train(cal, target, lambda r: (r[1], r[7]["same_action_run"]), 4)
        mp = train(
            cal,
            target,
            lambda r: (
                r[1],
                r[7]["same_action_run"],
                r[7]["since_reset"],
            ),
            4,
        )

        calibration[game] = {
            "coarse_keys": len(coarse),
            "effect_bad_roles": len(effect_bad),
            "noop_bad_roles": len(noop_bad),
        }

        for trace_name, tr in ev:
            for row_index, row in enumerate(tr):
                lev, c, f, _, y, e, app, ctrl = row
                if lev != target:
                    continue

                if c in effect_bad:
                    actual = e
                    p5 = p6 = p7 = me.get(f)
                    branch = "effect"
                elif c in noop_bad:
                    actual = y
                    p5 = ma.get(app)
                    p6 = mr.get((c, ctrl["same_action_run"]))
                    p7 = mp.get((c, ctrl["same_action_run"], ctrl["since_reset"]))
                    branch = "noop"
                else:
                    actual = y
                    p5 = p6 = p7 = coarse.get(c)
                    branch = "coarse"

                rec = {
                    "game": game,
                    "trace": trace_name,
                    "row_index": row_index,
                    "branch": branch,
                    "coarse_role": c,
                    "actual": actual,
                    "v5": p5,
                    "v6_same_action_run": p6,
                    "v7_same_action_run_since_reset": p7,
                    "control": ctrl,
                    "app_features": app,
                }
                all_records.append(rec)
                if branch == "noop":
                    noop_records.append(rec)

    audits = {
        "v5_to_v6_all": transition_summary(all_records, "v5", "v6_same_action_run"),
        "v6_to_v7_all": transition_summary(all_records, "v6_same_action_run", "v7_same_action_run_since_reset"),
        "v5_to_v6_noop": transition_summary(noop_records, "v5", "v6_same_action_run"),
        "v6_to_v7_noop": transition_summary(noop_records, "v6_same_action_run", "v7_same_action_run_since_reset"),
        "v5_to_v7_noop": transition_summary(noop_records, "v5", "v7_same_action_run_since_reset"),
    }

    decisive = []
    for r in noop_records:
        s5 = state(r["v5"], r["actual"])
        s6 = state(r["v6_same_action_run"], r["actual"])
        s7 = state(r["v7_same_action_run_since_reset"], r["actual"])
        if s5 != s6 or s6 != s7 or "wrong" in (s5, s6, s7):
            decisive.append({
                **r,
                "v5_state": s5,
                "v6_state": s6,
                "v7_state": s7,
            })

    v6_cls = audits["v5_to_v6_noop"]["classification"]
    v7_cls = audits["v6_to_v7_noop"]["classification"]
    if v6_cls == "ABSTENTION_ONLY":
        conclusion = "REJECT_V6_SCALAR_AS_ERROR_SEPARATOR"
    elif v6_cls == "GENUINE_CORRECTION_CANDIDATE":
        conclusion = "KEEP_V6_SCALAR_SIGNAL_LOCALIZE_REMAINING_RESIDUAL"
    else:
        conclusion = "V6_SIGNAL_MIXED_OR_UNRESOLVED"

    out = {
        "schema": "msi.arc3-latent-support-audit-v8",
        "game_prefix": args.game_prefix,
        "target_level": args.target_level,
        "epistemic_scope": "DIAGNOSTIC_ON_ALREADY_OBSERVED_V5_V6_V7_SPLIT",
        "calibration": calibration,
        "heldout_cells": len(all_records),
        "noop_cells": len(noop_records),
        "audits": audits,
        "v6_noop_classification": v6_cls,
        "v7_noop_classification": v7_cls,
        "conclusion": conclusion,
        "decisive_noop_records": decisive,
        "boundary": (
            "V5 relational applicability, V6 same_action_run, and V7 "
            "same_action_run+since_reset are compared cell-for-cell on identical "
            "held-out support. Fewer wrong predictions only counts as separator "
            "evidence when errors become correct rather than merely unpredicted."
        ),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    main()

from __future__ import annotations

import itertools
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

from arcengine import GameAction, GameState

import arc3_public_direct_schema_g2 as ds

OUT = Path(os.environ.get(
    "OUTDIR", "evidence/arc3-public-future-response-quotient-g2"
)).resolve()
OUT.mkdir(parents=True, exist_ok=True)

# Same direct-schema quotient that produced 36 zero-residual G2 realizations.
A = (58, 46)
B = (58, 11)
C = (58, 20)
D = (58, 22)
E = (55, 20)
REC = (2, 20)
BUNDLE = (54, 17)

# A tiny, fixed future-test alphabet. A itself is included so A,A and A,A,A
# are tested, while the empty probe sequence tests A directly.
PROBES = [
    ("mouse:A", "mouse", A),
    ("mouse:B", "mouse", B),
    ("mouse:C", "mouse", C),
    ("mouse:D", "mouse", D),
    ("mouse:E", "mouse", E),
    ("mouse:REC", "mouse", REC),
    ("mouse:BUNDLE", "mouse", BUNDLE),
    ("primitive:ACTION1", "primitive", "ACTION1"),
    ("primitive:ACTION2", "primitive", "ACTION2"),
    ("primitive:ACTION3", "primitive", "ACTION3"),
    ("primitive:ACTION4", "primitive", "ACTION4"),
    ("primitive:ACTION5", "primitive", "ACTION5"),
    ("primitive:ACTION7", "primitive", "ACTION7"),
]
MAX_PROBE_DEPTH = 2
VALID_OUTCOMES = {"PROGRESS", "GAME_OVER", "CONTINUE"}


def candidate_programs():
    e = ds.env()
    ds.enter_level2(e)
    for rc in ds.SETUP:
        ds.click(e, rc)
    H, V = ds.relation_toggle_centers(e.observation_space)

    hrows = defaultdict(list)
    vrows = defaultdict(list)
    for r, c in H:
        hrows[r].append(c)
    for r, c in V:
        vrows[r].append(c)

    rows = []
    for hr, hcs in sorted(hrows.items()):
        if len(hcs) < 3:
            continue
        for hs in itertools.combinations(sorted(hcs), 3):
            for vr, vcs in sorted(vrows.items()):
                common = sorted(set(hs) & set(vcs))
                if len(common) < 3:
                    continue
                for cols in itertools.combinations(common, 3):
                    program = [(hr, c) for c in cols] + [(vr, c) for c in cols]
                    rows.append({
                        "hrow": hr,
                        "vrow": vr,
                        "cols": list(cols),
                        "program": [list(x) for x in program],
                    })
    return rows


def apply_action(e, action):
    _, kind, payload = action
    if kind == "mouse":
        return ds.click(e, tuple(payload))
    return e.step(getattr(GameAction, payload))


def enter_candidate(candidate):
    e = ds.env()
    start, _ = ds.enter_level2(e)
    for rc in ds.SETUP:
        z = ds.click(e, rc)
        if z is None:
            raise RuntimeError("setup returned None")
    for rc in candidate["program"]:
        z = ds.click(e, tuple(rc))
        if z is None:
            raise RuntimeError("candidate returned None")
        if z.state == GameState.GAME_OVER or int(z.levels_completed) > 1 or z.state == GameState.WIN:
            raise RuntimeError("candidate left the declared preterminal envelope")
    return e, start


def quotient_residual(candidate, source_net):
    e, start = enter_candidate(candidate)
    target = ds.delta(start, ds.feat(e.observation_space))
    return ds.residual(source_net, target)


def protected_outcome(candidate, probe_sequence):
    e, _ = enter_candidate(candidate)
    trace = []
    suffix = list(probe_sequence) + [("terminal:A", "mouse", A)]
    for action in suffix:
        name, _, _ = action
        try:
            z = apply_action(e, action)
        except Exception as ex:
            return {
                "outcome": "INVALID",
                "error": type(ex).__name__,
                "action": name,
                "trace": trace,
            }
        if z is None:
            return {"outcome": "INVALID", "error": "NoneFrame", "action": name, "trace": trace}
        row = {
            "action": name,
            "level": int(z.levels_completed),
            "state": str(z.state),
        }
        trace.append(row)
        if int(z.levels_completed) > 1 or z.state == GameState.WIN:
            return {"outcome": "PROGRESS", "trace": trace}
        if z.state == GameState.GAME_OVER:
            return {"outcome": "GAME_OVER", "trace": trace}
    return {"outcome": "CONTINUE", "trace": trace}


def suffix_record(seq):
    return [x[0] for x in seq] + ["terminal:A"]


def verify_separator(left, right, seq, expected_left, expected_right):
    trials = []
    for trial in range(2):
        lo = protected_outcome(left, seq)
        ro = protected_outcome(right, seq)
        trials.append({
            "trial": trial,
            "left": lo,
            "right": ro,
            "stable": lo["outcome"] == expected_left and ro["outcome"] == expected_right,
        })
    return trials


def main():
    source_net = ds.source_net()
    candidates = candidate_programs()

    # Freeze the exact historical attack surface rather than silently changing it.
    if len(candidates) != 36:
        raise AssertionError(f"expected 36 direct-schema candidates, got {len(candidates)}")

    residuals = []
    retained = []
    for i, cand in enumerate(candidates):
        rem = quotient_residual(cand, source_net)
        residuals.append(rem)
        if not rem:
            retained.append({**cand, "candidate_id": i})

    if len(retained) != 36:
        raise AssertionError(f"expected 36 zero-residual candidates, got {len(retained)}")

    suffix_summaries = []
    separator = None
    tested_evaluations = 0

    # Search the smallest future suffix first. This is not board BFS:
    # all candidates are already merged by the declared q, and only the fixed
    # protected-response suffix bank is evaluated.
    for depth in range(MAX_PROBE_DEPTH + 1):
        seqs = [()] if depth == 0 else itertools.product(PROBES, repeat=depth)
        for seq0 in seqs:
            seq = tuple(seq0)
            outcomes = []
            details = []
            for cand in retained:
                out = protected_outcome(cand, seq)
                tested_evaluations += 1
                outcomes.append(out["outcome"])
                details.append(out)
            counts = dict(sorted(Counter(outcomes).items()))
            suffix_summaries.append({
                "probe_depth": depth,
                "suffix": suffix_record(seq),
                "outcome_counts": counts,
            })

            # A scientific separator must compare valid protected outcomes only.
            if set(outcomes).issubset(VALID_OUTCOMES) and len(set(outcomes)) > 1:
                left_i = None
                right_i = None
                for i in range(len(retained)):
                    for j in range(i + 1, len(retained)):
                        if outcomes[i] != outcomes[j]:
                            left_i, right_i = i, j
                            break
                    if left_i is not None:
                        break
                left = retained[left_i]
                right = retained[right_i]
                verification = verify_separator(
                    left, right, seq, outcomes[left_i], outcomes[right_i]
                )
                if not all(x["stable"] for x in verification):
                    raise AssertionError("separator was not deterministic on replay")
                separator = {
                    "suffix": suffix_record(seq),
                    "probe_depth": depth,
                    "left_candidate": left,
                    "right_candidate": right,
                    "left_outcome": outcomes[left_i],
                    "right_outcome": outcomes[right_i],
                    "left_first_trace": details[left_i]["trace"],
                    "right_first_trace": details[right_i]["trace"],
                    "verification": verification,
                }
                break
        if separator is not None:
            break

    status = "SEPARATOR" if separator is not None else "NO_SEPARATOR"
    max_level2_actions = len(ds.SETUP) + 6 + MAX_PROBE_DEPTH + 1

    out = {
        "lineage": {
            "base_head": "e238ed3f59ad6055ce75a0b474274a29f450d7bd",
            "direct_schema_run": 35868828608,
            "direct_schema_artifact": 10754302499,
            "bundle_residual_run": 35897658382,
            "terminal_directed_residual_run": 35898510110,
        },
        "hypothesis": (
            "the source-net structural quotient is insufficient iff two of its "
            "zero-residual histories have different protected responses to the same "
            "bounded future suffix"
        ),
        "quotient": "direct-schema source-net residual == {}",
        "candidate_programs": len(candidates),
        "zero_residual_candidates": len(retained),
        "future_probe_alphabet": [x[0] for x in PROBES],
        "max_probe_depth": MAX_PROBE_DEPTH,
        "terminal_action": list(A),
        "max_level2_actions": max_level2_actions,
        "tested_suffixes": len(suffix_summaries),
        "tested_candidate_suffix_evaluations": tested_evaluations,
        "suffix_summaries": suffix_summaries,
        "separator": separator,
        "status": status,
        "model_calls": 0,
        "source_inspection": False,
        "claim_boundary": (
            "finite black-box quotient-sufficiency falsifier on the exact 36 "
            "zero-residual direct-schema histories of public tn36 G2; suffixes are "
            "the fixed probe alphabet to depth <=2 followed by transported terminal A; "
            "no claim of global WIN-reachability equivalence when no separator is found"
        ),
    }
    (OUT / "result.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print("ARC3_PUBLIC_FUTURE_RESPONSE_QUOTIENT_G2=" + status)


if __name__ == "__main__":
    main()

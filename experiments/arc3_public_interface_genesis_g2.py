from __future__ import annotations

import itertools
import json
import math
import os
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from arcengine import GameAction, GameState

import arc3_public_direct_schema_g2 as ds

OUT = Path(os.environ.get(
    "OUTDIR", "evidence/arc3-public-interface-genesis-g2"
)).resolve()
OUT.mkdir(parents=True, exist_ok=True)

A = (58, 46)
KNOWN = [
    (58, 11), (58, 20), (58, 22), (55, 20), (54, 17), (2, 20),
    (32, 37), (32, 42), (32, 47), (32, 52),
    (35, 37), (35, 42), (35, 47), (35, 52),
]
MAX_ROOT_PROBES = 72
MAX_SECOND_PROBES = 56


def grid(f):
    x = f.frame
    if isinstance(x, (list, tuple)):
        x = x[-1]
    if hasattr(x, "tolist"):
        x = x.tolist()
    return [[int(v) for v in row] for row in x]


def board_hash(f):
    import hashlib
    return hashlib.sha256(
        json.dumps(grid(f), separators=(",", ":")).encode()
    ).hexdigest()


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
                        "candidate_id": len(rows),
                        "hrow": hr,
                        "vrow": vr,
                        "cols": list(cols),
                        "program": [list(x) for x in program],
                    })
    return rows


def replay(e, cand, prefix=()):
    start, _ = ds.enter_level2(e)
    for rc in ds.SETUP:
        z = ds.click(e, tuple(rc))
        if z is None:
            raise RuntimeError("setup returned None")
    for rc in cand["program"]:
        z = ds.click(e, tuple(rc))
        if z is None:
            raise RuntimeError("candidate returned None")
        if int(z.levels_completed) > 1 or z.state in (GameState.WIN, GameState.GAME_OVER):
            raise RuntimeError("candidate escaped preterminal envelope")
    for rc in prefix:
        z = ds.click(e, tuple(rc))
        if z is None:
            raise RuntimeError("prefix returned None")
        if int(z.levels_completed) > 1 or z.state in (GameState.WIN, GameState.GAME_OVER):
            break
    return start, e.observation_space


def protected(frame):
    if int(frame.levels_completed) > 1 or frame.state == GameState.WIN:
        return "PROGRESS"
    if frame.state == GameState.GAME_OVER:
        return "GAME_OVER"
    return "CONTINUE"


def patch(g, r, c, radius=1):
    h, w = len(g), len(g[0])
    out = []
    for rr in range(max(0, r-radius), min(h, r+radius+1)):
        row = []
        for cc in range(max(0, c-radius), min(w, c+radius+1)):
            row.append(g[rr][cc])
        out.append(tuple(row))
    return tuple(out)


def pool_from_grids(grids, limit, mandatory=()):
    h, w = len(grids[0]), len(grids[0][0])
    scored = []
    for r in range(h):
        for c in range(w):
            px = Counter(g[r][c] for g in grids)
            pa = Counter(patch(g, r, c) for g in grids)
            if len(pa) <= 1:
                continue
            n = len(grids)
            balance = n - max(pa.values())
            scored.append((
                len(pa),
                len(px),
                balance,
                -r,
                -c,
                (r, c),
            ))
    scored.sort(reverse=True)

    out = []
    seen = set()
    for rc in mandatory:
        rc = tuple(rc)
        if rc not in seen:
            seen.add(rc)
            out.append(rc)
    for *_, rc in scored:
        if rc in seen:
            continue
        seen.add(rc)
        out.append(rc)
        if len(out) >= limit:
            break
    return out


def response_signature(before, after, rc):
    outcome = protected(after)
    changed = board_hash(before) != board_hash(after)
    if outcome != "CONTINUE":
        return {
            "outcome": outcome,
            "changed": changed,
            "effect": {},
        }
    effect = ds.delta(ds.feat(before), ds.feat(after))
    return {
        "outcome": outcome,
        "changed": changed,
        "effect": effect,
    }


def sig_key(sig):
    return json.dumps(sig, sort_keys=True, separators=(",", ":"))


def partition_score(signatures):
    counts = Counter(signatures)
    n = len(signatures)
    entropy = 0.0
    for k in counts.values():
        p = k / n
        entropy -= p * math.log2(p)
    changed_classes = len(counts)
    largest = max(counts.values())
    return {
        "classes": changed_classes,
        "entropy": entropy,
        "largest_class": largest,
        "counts": dict(sorted(counts.items())),
    }


def evaluate_probe(e, candidates, candidate_ids, probe, prefix=()):
    signatures = []
    protected_outcomes = []
    details = []
    for cid in candidate_ids:
        cand = candidates[cid]
        _, f = replay(e, cand, prefix)
        before = f
        z = ds.click(e, probe)
        if z is None:
            sig = {"outcome": "INVALID", "changed": False, "effect": {}}
            po = "INVALID"
            details.append({"candidate_id": cid, "signature": sig, "protected": po})
            signatures.append(sig_key(sig))
            protected_outcomes.append(po)
            continue
        sig = response_signature(before, z, probe)
        po = protected(z)
        if po == "CONTINUE":
            t = ds.click(e, A)
            if t is None:
                po = "INVALID"
            else:
                po = protected(t)
        details.append({
            "candidate_id": cid,
            "signature": sig,
            "protected": po,
        })
        signatures.append(sig_key(sig))
        protected_outcomes.append(po)

    pscore = partition_score(signatures)
    ocounts = dict(sorted(Counter(protected_outcomes).items()))
    return {
        "probe": list(probe),
        "partition": pscore,
        "protected_counts": ocounts,
        "details": details,
        "_signatures": signatures,
        "_protected": protected_outcomes,
    }


def best_probe(records):
    usable = [r for r in records if r["partition"]["classes"] > 1]
    if not usable:
        return None
    usable.sort(
        key=lambda r: (
            r["partition"]["classes"],
            r["partition"]["entropy"],
            -r["partition"]["largest_class"],
            sum(1 for d in r["details"] if d["signature"]["changed"]),
            -r["probe"][0],
            -r["probe"][1],
        ),
        reverse=True,
    )
    return usable[0]


def protected_split(record):
    vals = record["_protected"]
    valid = {"PROGRESS", "GAME_OVER", "CONTINUE"}
    return set(vals).issubset(valid) and len(set(vals)) > 1


def progress_witness(record):
    for d in record["details"]:
        if d["protected"] == "PROGRESS":
            return d["candidate_id"]
    return None


def verify_sequence(candidates, cid, seq):
    rows = []
    for _ in range(2):
        e = ds.env()
        cand = candidates[cid]
        _, f = replay(e, cand)
        trace = []
        for rc in seq:
            z = ds.click(e, tuple(rc))
            if z is None:
                rows.append({"outcome": "INVALID", "trace": trace})
                break
            trace.append({
                "rc": list(rc),
                "level": int(z.levels_completed),
                "state": str(z.state),
            })
            out = protected(z)
            if out != "CONTINUE":
                rows.append({"outcome": out, "trace": trace})
                break
        else:
            rows.append({"outcome": protected(e.observation_space), "trace": trace})
    return rows


def make_separator(record, candidates, prefix=()):
    vals = record["_protected"]
    li = None
    ri = None
    for i in range(len(vals)):
        for j in range(i+1, len(vals)):
            if vals[i] != vals[j]:
                li, ri = i, j
                break
        if li is not None:
            break
    left = record["details"][li]
    right = record["details"][ri]
    seq = [tuple(x) for x in prefix] + [tuple(record["probe"]), A]
    return {
        "suffix": [list(x) for x in seq],
        "left_candidate": left["candidate_id"],
        "right_candidate": right["candidate_id"],
        "left_outcome": left["protected"],
        "right_outcome": right["protected"],
        "left_verification": verify_sequence(candidates, left["candidate_id"], seq),
        "right_verification": verify_sequence(candidates, right["candidate_id"], seq),
    }


def snapshot_grids(e, candidates, candidate_ids, prefix=()):
    rows = []
    hashes = []
    for cid in candidate_ids:
        _, f = replay(e, candidates[cid], prefix)
        rows.append(grid(f))
        hashes.append(board_hash(f))
    return rows, hashes


def main():
    candidates = candidate_programs()
    if len(candidates) != 36:
        raise AssertionError(f"expected 36 candidates, got {len(candidates)}")

    e = ds.env()
    source = ds.source_net()
    base_grids = []
    base_hashes = []
    for cand in candidates:
        start, f = replay(e, cand)
        rem = ds.residual(source, ds.delta(start, ds.feat(f)))
        if rem:
            raise AssertionError(f"candidate {cand['candidate_id']} escaped zero residual: {rem}")
        base_grids.append(grid(f))
        base_hashes.append(board_hash(f))

    mandatory = list(KNOWN)
    root_pool = pool_from_grids(base_grids, MAX_ROOT_PROBES, mandatory)
    root_records = []
    separator = None
    selected = None
    verification = []
    tested = 0

    all_ids = list(range(len(candidates)))
    for probe in root_pool:
        rec = evaluate_probe(e, candidates, all_ids, probe)
        tested += len(all_ids)
        root_records.append(rec)
        cid = progress_witness(rec)
        if cid is not None:
            seq = [tuple(probe), A]
            vv = verify_sequence(candidates, cid, seq)
            if all(x["outcome"] == "PROGRESS" for x in vv):
                selected = {
                    "candidate_id": cid,
                    "program": ds.SETUP + [tuple(x) for x in candidates[cid]["program"]] + seq,
                    "probe": list(probe),
                }
                verification = vv
                break
        if protected_split(rec):
            separator = make_separator(rec, candidates)
            break

    root_best = best_probe(root_records)

    second_level = []
    if selected is None and separator is None and root_best is not None:
        # Partition by the genuinely observed response to the best active probe.
        classes = defaultdict(list)
        for d, sk in zip(root_best["details"], root_best["_signatures"]):
            classes[sk].append(d["candidate_id"])

        root_probe = tuple(root_best["probe"])
        for class_key, ids in sorted(classes.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            if len(ids) < 2:
                continue

            post_grids, post_hashes = snapshot_grids(e, candidates, ids, (root_probe,))
            pool = pool_from_grids(post_grids, MAX_SECOND_PROBES, mandatory)
            records = []
            class_separator = None
            class_selected = None

            for probe2 in pool:
                rec2 = evaluate_probe(e, candidates, ids, probe2, prefix=(root_probe,))
                tested += len(ids)
                records.append(rec2)

                cid = progress_witness(rec2)
                if cid is not None:
                    seq = [root_probe, tuple(probe2), A]
                    vv = verify_sequence(candidates, cid, seq)
                    if all(x["outcome"] == "PROGRESS" for x in vv):
                        selected = {
                            "candidate_id": cid,
                            "program": ds.SETUP + [tuple(x) for x in candidates[cid]["program"]] + seq,
                            "root_probe": list(root_probe),
                            "second_probe": list(probe2),
                        }
                        verification = vv
                        class_selected = selected
                        break

                if protected_split(rec2):
                    separator = make_separator(rec2, candidates, prefix=(root_probe,))
                    class_separator = separator
                    break

            b2 = best_probe(records)
            second_level.append({
                "root_signature": json.loads(class_key),
                "candidate_ids": ids,
                "candidate_count": len(ids),
                "post_root_board_classes": len(set(post_hashes)),
                "probe_pool": len(pool),
                "best_second_probe": None if b2 is None else {
                    "probe": b2["probe"],
                    "partition": b2["partition"],
                    "protected_counts": b2["protected_counts"],
                },
                "separator": class_separator,
                "selected": class_selected,
            })
            if selected is not None or separator is not None:
                break

    if selected is not None:
        status = "SOLVED"
    elif separator is not None:
        status = "SEPARATOR"
    elif root_best is not None:
        status = "INTERFACE_CREATED"
    else:
        status = "NO_INTERFACE"

    def compact(rec):
        return {
            "probe": rec["probe"],
            "partition": rec["partition"],
            "protected_counts": rec["protected_counts"],
        }

    root_ranked = sorted(
        [compact(x) for x in root_records],
        key=lambda r: (
            r["partition"]["classes"],
            r["partition"]["entropy"],
            -r["partition"]["largest_class"],
        ),
        reverse=True,
    )[:12]

    out = {
        "lineage": {
            "parent_head": "87d991acedc0bec6af19f5609dab0019ddf6dc12",
            "parent_run": 35922719199,
            "parent_artifact": 10778441361,
            "direct_schema_run": 35868828608,
        },
        "hypothesis": (
            "when the current quotient and fixed suffix bank yield no separator, "
            "synthesize the cheapest active probe from candidate-world disagreement; "
            "only a protected split or verified progress licenses a goal-relative refinement"
        ),
        "candidate_count": len(candidates),
        "base_exact_board_classes": len(set(base_hashes)),
        "root_probe_pool": len(root_pool),
        "root_top": root_ranked,
        "chosen_root_probe": None if root_best is None else {
            "probe": root_best["probe"],
            "partition": root_best["partition"],
            "protected_counts": root_best["protected_counts"],
        },
        "second_level": second_level,
        "tested_candidate_probe_evaluations": tested,
        "separator": separator,
        "selected": selected,
        "verification": verification,
        "status": status,
        "model_calls": 0,
        "source_inspection": False,
        "max_live_suffix_actions": 3,
        "claim_boundary": (
            "finite black-box active-interface genesis on the exact 36 zero-residual "
            "public tn36 G2 candidates; candidate probes are selected from observed board "
            "disagreement but promotion requires fixed-sequence protected consequence "
            "separation or independently replayed progress; no raw pixel novelty is authority"
        ),
    }
    (OUT / "result.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print("ARC3_PUBLIC_INTERFACE_GENESIS_G2=" + status)


if __name__ == "__main__":
    main()

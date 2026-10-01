"""V9 visible-state sufficiency audit for the ka59-L1 ACTION1 collision.

Question: is hidden control state actually required, or did the previous
nonzero-support quotient erase visible information?

The experiment preserves the V5 calibration/evaluation split and tests:
1. raw visible board identity (diagnostic observability upper bound),
2. exact color-permutation-invariant spatial partition,
3. dominant-background-relative geometry,
4. color-count multiset,
5. per-color geometry multiset.

No result from exact identity is promoted as a reusable representation; it is
used only to decide whether hidden state is observationally earned.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from arc3_prospective_role_refinement_v3 import base, geom, outcome
from arc3_typed_local_refinement_v4 import board, effect, loc
from arc3_relational_applicability_v5 import app_features


def components(points):
    todo = set(points)
    n = 0
    while todo:
        n += 1
        stack = [todo.pop()]
        while stack:
            r, c = stack.pop()
            for q in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if q in todo:
                    todo.remove(q)
                    stack.append(q)
    return n


def dominant_background(g):
    counts = Counter(str(v) for row in g for v in row)
    if not counts:
        return "", counts
    # Deterministic tie break only; the chosen value itself is not retained by
    # the color-invariant candidate features.
    bg = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
    return bg, counts


def bg_geometry(g):
    h = len(g)
    w = len(g[0]) if h else 0
    bg, counts = dominant_background(g)
    fg = {(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if str(v) != bg}
    if not fg:
        return (0, 0, 0, 0, 0, 0, 0, 0)
    rs = [r for r, _ in fg]
    cs = [c for _, c in fg]
    bh = max(rs) - min(rs) + 1
    bw = max(cs) - min(cs) + 1
    border = sum(r in (0, h - 1) or c in (0, w - 1) for r, c in fg)
    cr = round(sum(rs) / len(rs), 2)
    cc = round(sum(cs) / len(cs), 2)
    return (
        len(fg),
        bh,
        bw,
        components(fg),
        border,
        min(rs),
        min(cs),
        cr,
        cc,
    )


def color_count_multiset(g):
    _, counts = dominant_background(g)
    return tuple(sorted(counts.values(), reverse=True))


def one_color_geom(g, color):
    h = len(g)
    w = len(g[0]) if h else 0
    pts = {(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if str(v) == color}
    if not pts:
        return (0, 0, 0, 0, 0, 0, 0)
    rs = [r for r, _ in pts]
    cs = [c for _, c in pts]
    return (
        len(pts),
        max(rs) - min(rs) + 1,
        max(cs) - min(cs) + 1,
        components(pts),
        sum(r in (0, h - 1) or c in (0, w - 1) for r, c in pts),
        min(rs),
        min(cs),
    )


def per_color_geom_multiset(g):
    bg, counts = dominant_background(g)
    feats = [one_color_geom(g, color) for color in counts if color != bg]
    return tuple(sorted(feats))


def canonical_partition(g):
    relabel = {}
    nxt = 0
    out = []
    for row in g:
        for v in row:
            k = str(v)
            if k not in relabel:
                relabel[k] = nxt
                nxt += 1
            out.append(relabel[k])
    return tuple(out)


def raw_board_key(g):
    return tuple(str(v) for row in g for v in row)


def key_digest(key):
    payload = repr(key).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def trace(path):
    rows = []
    prev = None
    level = 0
    for line in path.read_text().splitlines():
        if not line:
            continue
        x = json.loads(line)
        now = board(x)
        if x.get("type") == "action":
            name = str(x.get("action_name", ""))
            if name == "RESET":
                prev = now
                continue
            if name.startswith("ACTION"):
                aid = int(name.replace("ACTION", ""))
                if prev is not None and aid != 6:
                    coarse = (aid,) + base(prev)
                    rows.append(
                        {
                            "level": level,
                            "coarse": coarse,
                            "fine": coarse + geom(prev),
                            "state": coarse + loc(prev),
                            "y": outcome(prev, now),
                            "effect": effect(prev, now),
                            "app": coarse + app_features(prev),
                            "bg_geom": coarse + bg_geometry(prev),
                            "count_multiset": coarse + color_count_multiset(prev),
                            "per_color_geom": coarse + per_color_geom_multiset(prev),
                            "partition": coarse + canonical_partition(prev),
                            "raw": coarse + raw_board_key(prev),
                            "dominant_background_count": max(Counter(str(v) for row in prev for v in row).values()) if prev else 0,
                            "board_cells": sum(len(row) for row in prev),
                        }
                    )
                if bool(x.get("level_completed")):
                    level += 1
        prev = now
    return rows


def learn(rows, target, key_name, out_name="y"):
    seen = defaultdict(set)
    for tr in rows:
        for row in tr:
            if row["level"] < target:
                seen[row[key_name]].add(row[out_name])
    return {k: next(iter(v)) for k, v in seen.items() if len(v) == 1}


def state(pred, actual):
    if pred is None:
        return "abstain"
    return "correct" if pred == actual else "wrong"


def transition_summary(records, candidate):
    cats = Counter()
    v5_known = v5_wrong = cand_known = cand_wrong = 0
    common = common_v5_wrong = common_cand_wrong = 0
    for r in records:
        actual = r["actual"]
        left = r["v5"]
        right = r[candidate]
        ls = state(left, actual)
        rs = state(right, actual)
        cats[f"{ls}_to_{rs}"] += 1
        if left is not None:
            v5_known += 1
            v5_wrong += left != actual
        if right is not None:
            cand_known += 1
            cand_wrong += right != actual
        if left is not None and right is not None:
            common += 1
            common_v5_wrong += left != actual
            common_cand_wrong += right != actual

    return {
        "v5_known": v5_known,
        "v5_wrong": v5_wrong,
        "candidate_known": cand_known,
        "candidate_wrong": cand_wrong,
        "candidate_coverage": cand_known / len(records) if records else 0,
        "common_support": {
            "cells": common,
            "v5_wrong": common_v5_wrong,
            "candidate_wrong": common_cand_wrong,
        },
        "transitions": dict(sorted(cats.items())),
        "wrong_to_correct": cats["wrong_to_correct"],
        "wrong_to_abstain": cats["wrong_to_abstain"],
        "correct_to_wrong": cats["correct_to_wrong"],
        "correct_to_abstain": cats["correct_to_abstain"],
    }


def ambiguity(rows, key_name):
    seen = defaultdict(set)
    examples = defaultdict(list)
    for row in rows:
        seen[row[key_name]].add(row["y"])
        if len(examples[row[key_name]]) < 3:
            examples[row[key_name]].append(row["y"])
    ambiguous = [k for k, ys in seen.items() if len(ys) > 1]
    return {
        "unique_keys": len(seen),
        "ambiguous_keys": len(ambiguous),
        "ambiguous_examples": [
            {"key_digest": key_digest(k), "outcomes": sorted(map(repr, seen[k]))}
            for k in ambiguous[:20]
        ],
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
        games[game].append((p.name, trace(p)))
    if not games:
        raise SystemExit(f"no games matched {args.game_prefix!r}")

    candidates = ("bg_geom", "count_multiset", "per_color_geom", "partition", "raw")
    result_games = {}

    for game, labelled in sorted(games.items()):
        cal = [tr for i, (_, tr) in enumerate(labelled) if i % 2 == 0]
        ev = [(name, tr) for i, (name, tr) in enumerate(labelled) if i % 2 == 1]
        target = args.target_level

        coarse = learn(cal, target, "coarse")
        noop_bad = set()
        effect_bad = set()
        for tr in cal:
            for row in tr:
                if row["level"] != target:
                    continue
                c = row["coarse"]
                if c not in coarse or coarse[c] == row["y"]:
                    continue
                if row["y"][0] == "same" or coarse[c][0] == "same":
                    noop_bad.add(c)
                else:
                    effect_bad.add(c)

        ma = learn(cal, target, "app")
        maps = {q: learn(cal, target, q) for q in candidates}

        heldout = []
        for trace_name, tr in ev:
            for idx, row in enumerate(tr):
                if row["level"] != target or row["coarse"] not in noop_bad:
                    continue
                actual = row["y"]
                rec = {
                    "trace": trace_name,
                    "row_index": idx,
                    "actual": actual,
                    "v5": ma.get(row["app"]),
                    "dominant_background_fraction": (
                        row["dominant_background_count"] / row["board_cells"]
                        if row["board_cells"] else 0
                    ),
                }
                for q in candidates:
                    rec[q] = maps[q].get(row[q])
                heldout.append(rec)

        # Observability is not a predictive qualification. Use every target-level
        # occurrence of the earned collision to ask whether an identical visible
        # state/action was ever observed with two different consequences.
        target_collision_rows = []
        for _, tr in labelled:
            for row in tr:
                if row["level"] == target and row["coarse"] in noop_bad:
                    target_collision_rows.append(row)

        tournament = {q: transition_summary(heldout, q) for q in candidates}
        observability = {
            "raw": ambiguity(target_collision_rows, "raw"),
            "partition": ambiguity(target_collision_rows, "partition"),
            "bg_geom": ambiguity(target_collision_rows, "bg_geom"),
            "count_multiset": ambiguity(target_collision_rows, "count_multiset"),
            "per_color_geom": ambiguity(target_collision_rows, "per_color_geom"),
        }

        bg_fracs = [r["dominant_background_fraction"] for r in heldout]
        result_games[game] = {
            "target_level": target,
            "noop_bad_roles": len(noop_bad),
            "effect_bad_roles": len(effect_bad),
            "heldout_noop_cells": len(heldout),
            "dominant_background_fraction": {
                "min": min(bg_fracs) if bg_fracs else 0,
                "max": max(bg_fracs) if bg_fracs else 0,
                "mean": sum(bg_fracs) / len(bg_fracs) if bg_fracs else 0,
            },
            "tournament": tournament,
            "observability": observability,
        }

    raw_ambiguous = sum(v["observability"]["raw"]["ambiguous_keys"] for v in result_games.values())
    partition_ambiguous = sum(v["observability"]["partition"]["ambiguous_keys"] for v in result_games.values())

    if raw_ambiguous:
        conclusion = "VISIBLE_BOARD_NOT_MARKOVIAN_HIDDEN_STATE_EARNED"
    elif partition_ambiguous:
        conclusion = "RAW_COLOR_IDENTITY_MAY_MATTER"
    else:
        conclusion = "NO_OBSERVED_VISIBLE_IDENTITY_CONTRADICTION_REFINE_VISIBLE_IR_FIRST"

    out = {
        "schema": "msi.arc3-visible-state-sufficiency-v9",
        "epistemic_scope": "DIAGNOSTIC_ON_EXISTING_PUBLIC_TRACES",
        "games": result_games,
        "conclusion": conclusion,
        "boundary": (
            "Raw/canonical board identity are diagnostic upper bounds only. "
            "Candidate transfer still uses even-index calibration traces, strictly "
            "earlier levels, and odd-index target evaluation. No history feature "
            "or game ID is added to the role."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps(out, sort_keys=True))


if __name__ == "__main__":
    main()

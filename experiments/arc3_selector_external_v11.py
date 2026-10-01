"""V11 prospective external selector-latch gate.

Frozen before touching the external outcomes:
  hidden coordinate = shape of the component clicked by the most recent
  ACTION6/MOUSE, persisted until another click or RESET.

Authority surface is independent public ka59-38d34dbb traces in canivel/kaggle,
pinned by the workflow.  No candidate tournament is allowed here.

The gate asks a narrower causal question than V4-V10 (pre-registered external test):
does adding that frozen selector coordinate make repeated (full frame, UP)
transitions more deterministic on genuinely independent streams?
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

MOUSE_RE = re.compile(r"MOUSE\(row=(\d+), col=(\d+)\)")
FILES = (
    "a22_compaction_v1/artifacts/ka59-38d34dbb_p0_events.jsonl",
    "a22_v2_seed1/artifacts/ka59-38d34dbb_p0_events.jsonl",
    "tmp_pullback_duckgate_v1post/artifacts/ka59-38d34dbb_p0_events.jsonl",
    "tmp_pullback_gate_eval_s2v3/artifacts/ka59-38d34dbb_p0_events.jsonl",
)

def board(ev):
    g = ev.get("board", [])
    if g and isinstance(g[0], list) and g[0] and isinstance(g[0][0], list):
        g = g[0]
    return g

def digest(g):
    return hashlib.blake2b(
        json.dumps(g, separators=(",", ":")).encode(), digest_size=8
    ).hexdigest()

def clicked_component_shape(g, r, c):
    if not g or r < 0 or c < 0 or r >= len(g) or c >= len(g[0]):
        return ("OUT",)
    v = g[r][c]
    todo = [(r, c)]
    seen = {(r, c)}
    while todo:
        x, y = todo.pop()
        for a, b in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if (
                0 <= a < len(g)
                and 0 <= b < len(g[0])
                and (a,b) not in seen
                and g[a][b] == v
            ):
                seen.add((a,b))
                todo.append((a,b))
    rs = [x for x,_ in seen]
    cs = [y for _,y in seen]
    return (len(seen), max(rs)-min(rs)+1, max(cs)-min(cs)+1)

def extract(path):
    prev = None
    selector = None
    rows = []
    clicks = board_invariant_clicks = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw:
            continue
        ev = json.loads(raw)
        now = board(ev)
        if ev.get("type") == "initial":
            prev = now
            selector = None
            continue
        if ev.get("type") != "action":
            continue
        name = str(ev.get("action_name", ""))
        disp = str(ev.get("action_display") or name)
        if name == "RESET" or disp == "RESET":
            selector = None
            prev = now
            continue
        if prev is None:
            prev = now
            continue
        if name == "ACTION6":
            clicks += 1
            m = MOUSE_RE.search(disp)
            if m:
                r, c = map(int, m.groups())
                selector = clicked_component_shape(prev, r, c)
            board_invariant_clicks += int(prev == now)
        elif name == "ACTION1":
            rows.append(
                dict(
                    prev=digest(prev),
                    act=disp,
                    out=digest(now),
                    selector=selector,
                    changed=(prev != now),
                    level=ev.get("level"),
                )
            )
        prev = now
    return rows, clicks, board_invariant_clicks

def stats(rows, augmented):
    buckets = defaultdict(Counter)
    for r in rows:
        k = (r["prev"], r["act"])
        if augmented:
            k += (r["selector"],)
        buckets[k][r["out"]] += 1
    visits = hits = repeat_keys = aliased = 0
    for dist in buckets.values():
        n = sum(dist.values())
        if n < 2:
            continue
        repeat_keys += 1
        visits += n
        hits += max(dist.values())
        aliased += int(len(dist) > 1)
    return dict(
        transitions=len(rows),
        repeat_keys=repeat_keys,
        repeat_visits=visits,
        modal_hits=hits,
        wrong=visits-hits,
        aliased_keys=aliased,
        determinism=(hits/visits if visits else None),
    )

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-root", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()

    all_rows = []
    streams = []
    total_clicks = invariant = 0
    for rel in FILES:
        p = a.runs_root / rel
        if not p.exists():
            raise SystemExit(f"missing frozen external stream: {p}")
        rows, clicks, inv = extract(p)
        all_rows += rows
        total_clicks += clicks
        invariant += inv
        streams.append(dict(path=rel, up_transitions=len(rows), clicks=clicks,
                            board_invariant_clicks=inv))

    base = stats(all_rows, False)
    selector = stats(all_rows, True)
    floor = max(10, int((0.20 * base["repeat_visits"]) + 0.999999))
    support_ok = selector["repeat_visits"] >= floor
    improves = (
        base["determinism"] is not None
        and selector["determinism"] is not None
        and selector["determinism"] > base["determinism"]
    )
    zero_error = bool(selector["repeat_visits"] and selector["wrong"] == 0)
    out = dict(
        schema="msi.arc3-ka59-selector-external-v11",
        game="ka59-38d34dbb",
        protected_action="ACTION1/UP",
        frozen_coordinate="persistent last-MOUSE clicked-component shape",
        streams=streams,
        mouse_events=total_clicks,
        board_invariant_mouse_events=invariant,
        base=base,
        selector=selector,
        support_floor=floor,
        support_ok=support_ok,
        status=(
            "PROSPECTIVE_ZERO_ERROR"
            if support_ok and zero_error
            else "PROSPECTIVE_IMPROVEMENT"
            if support_ok and improves
            else "PROSPECTIVE_NEGATIVE"
        ),
        boundary=(
            "Representation frozen from V9 before external outcomes. "
            "Independent public canivel/kaggle same-version traces only. "
            "No feature selection or post-outcome adaptation. Full-frame ACTION1 "
            "aliasing test; this does not by itself promote the broader V4 quotient."
        ),
    )
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(out, indent=2, sort_keys=True)+"\n")
    print(json.dumps(out, sort_keys=True))

if __name__ == "__main__":
    main()

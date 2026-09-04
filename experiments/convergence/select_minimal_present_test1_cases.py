#!/usr/bin/env python3
"""Mechanical case selector for Minimal-Present Test 1.

Must be run only after controller v1 was frozen.
Does not score or inspect candidate semantics; it only applies the preregistered
eligibility and hash-ranking rule.
"""
from __future__ import annotations
import hashlib, json, subprocess, sys

CONTROLLER_SHA256 = "3d5571716f70c47ad795538f0401f0ee45ba1c66ef9ce7f8af8d832f072b35b8"
FREEZE_COMMIT = "72c85a51fd2dae21684834a31a0a72129b883f0a"
HISTORY_TIP = "0cfd1bbf4a1b261d61bba920764591b3f8e5574a"

def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL).strip()

def load_frontier(commit: str):
    try:
        raw = git("show", f"{commit}:program_frontier.json")
        return json.loads(raw)
    except Exception:
        return None

def first_parent(commit: str):
    line = git("rev-list", "--parents", "-n", "1", commit).split()
    return line[1] if len(line) > 1 else None

def field(f, path, default=""):
    x = f
    for p in path:
        if not isinstance(x, dict):
            return default
        x = x.get(p, default)
    return x

def main():
    commits = git("rev-list", "--first-parent", HISTORY_TIP).splitlines()
    candidates = []
    for c in commits:
        p = first_parent(c)
        if not p:
            continue
        fc, fp = load_frontier(c), load_frontier(p)
        if fc is None or fp is None:
            continue
        rid_c = field(fc, ["last_transition", "result_id"])
        rid_p = field(fp, ["last_transition", "result_id"])
        res_c = field(fc, ["live_residual", "text"])
        res_p = field(fp, ["live_residual", "text"])
        if rid_c != rid_p or res_c != res_p:
            rank = hashlib.sha256(f"{CONTROLLER_SHA256}:{c}".encode()).hexdigest()
            candidates.append({
                "commit": c,
                "parent": p,
                "rank": rank,
                "result_id_before": rid_p,
                "result_id_after": rid_c,
                "residual_changed": res_c != res_p,
            })
    candidates.sort(key=lambda x: x["rank"])
    selected = candidates[:20]
    out = {
        "freeze_commit": FREEZE_COMMIT,
        "history_tip_strictly_before_freeze": HISTORY_TIP,
        "controller_sha256": CONTROLLER_SHA256,
        "eligible_count": len(candidates),
        "selected_count": len(selected),
        "selected": selected,
    }
    json.dump(out, sys.stdout, indent=2)
    print()

if __name__ == "__main__":
    main()

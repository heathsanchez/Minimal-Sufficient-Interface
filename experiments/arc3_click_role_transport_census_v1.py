"""Exact public click-role transport census.

Diagnostic only. It consumes the pinned public Duck replay corpus and asks whether
palette-invariant local/component click roles observed in one successful level
remain available and uniquely bindable in the next successfully reached level.

No game score, hidden state, or post-hoc action choice is used. Primitive actions
are deliberately outside this census.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.developmental_controller import ProgressMemory

_MOUSE = re.compile(r"MOUSE\(row=(-?\d+),\s*col=(-?\d+)\)")


def board_tuple(board):
    return tuple(tuple(int(v) for v in row) for row in board)


def action(row):
    name = str(row.get("action_name", ""))
    if name == "RESET":
        return ("RESET", None, None)
    if not name.startswith("ACTION"):
        return None
    aid = int(name.removeprefix("ACTION"))
    if aid != 6:
        return (aid, None, None)
    m = _MOUSE.fullmatch(str(row.get("action_display", "")))
    if m is None:
        return (6, None, None)
    y, x = (int(v) for v in m.groups())
    return (6, x, y)


def game_id(path: Path) -> str:
    return path.name.split("_p", 1)[0]


def parse_file(path: Path):
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not lines:
        return []
    rows = [json.loads(line) for line in lines]
    current = board_tuple(rows[0]["board"])
    life = 0
    segment = {"actions": [], "clicks": [], "start_board": current, "life": life}
    previous = None
    pairs = []

    for row in rows[1:]:
        if row.get("type") != "action":
            current = board_tuple(row["board"])
            if not segment["actions"]:
                segment["start_board"] = current
            continue

        a = action(row)
        after = board_tuple(row["board"])
        if a is None:
            current = after
            continue
        if a[0] == "RESET":
            life += 1
            previous = None
            current = after
            segment = {"actions": [], "clicks": [], "start_board": current, "life": life}
            continue

        before = current
        segment["actions"].append(a)
        if a[0] == 6 and a[1] is not None and a[2] is not None:
            role = ProgressMemory.click_role(before, int(a[1]), int(a[2]))
            unique = (
                role is not None
                and ProgressMemory._unique_click_binding(before, role) == (int(a[1]), int(a[2]))
            )
            segment["clicks"].append(
                {"role": role, "unique": bool(unique), "action": a, "before": before}
            )
        current = after

        if bool(row.get("level_completed")):
            completed = {
                "actions": tuple(segment["actions"]),
                "clicks": tuple(segment["clicks"]),
                "start_board": segment["start_board"],
                "end_board": current,
                "life": life,
            }
            if previous is not None and previous["life"] == life:
                pairs.append((previous, completed))
            previous = completed
            segment = {"actions": [], "clicks": [], "start_board": current, "life": life}

    return pairs


def summarize(root: Path):
    pair_rows = []
    by_game = defaultdict(lambda: Counter())
    for path in sorted(root.glob("*_events.jsonl")):
        for source, target in parse_file(path):
            src_roles = {repr(click["role"]) for click in source["clicks"] if click["role"] is not None}
            target_clicks = list(target["clicks"])
            seen = sum(1 for c in target_clicks if repr(c["role"]) in src_roles)
            unique = sum(1 for c in target_clicks if c["unique"])
            seen_unique = sum(
                1 for c in target_clicks
                if c["unique"] and repr(c["role"]) in src_roles
            )

            start_unique_source_roles = 0
            for click in source["clicks"]:
                role = click["role"]
                if role is not None and ProgressMemory._unique_click_binding(target["start_board"], role) is not None:
                    start_unique_source_roles += 1

            first_target = target_clicks[0] if target_clicks else None
            first_seen_unique = bool(
                first_target
                and first_target["unique"]
                and repr(first_target["role"]) in src_roles
            )
            both_click_only = bool(source["actions"] and target["actions"]) and all(
                a[0] == 6 for a in source["actions"] + target["actions"]
            )
            source_seq = tuple(repr(c["role"]) for c in source["clicks"])
            target_seq = tuple(repr(c["role"]) for c in target["clicks"])
            exact_role_sequence = bool(source_seq) and source_seq == target_seq

            row = {
                "game": game_id(path),
                "file": path.name,
                "source_actions": len(source["actions"]),
                "target_actions": len(target["actions"]),
                "source_clicks": len(source["clicks"]),
                "target_clicks": len(target_clicks),
                "target_roles_seen_in_source": seen,
                "target_roles_unique": unique,
                "target_roles_seen_and_unique": seen_unique,
                "source_roles_uniquely_bindable_at_target_start": start_unique_source_roles,
                "first_target_click_seen_and_unique": first_seen_unique,
                "both_click_only": both_click_only,
                "exact_click_role_sequence": exact_role_sequence,
            }
            pair_rows.append(row)
            c = by_game[row["game"]]
            c["pairs"] += 1
            c["target_clicks"] += len(target_clicks)
            c["seen"] += seen
            c["unique"] += unique
            c["seen_unique"] += seen_unique
            c["first_seen_unique"] += int(first_seen_unique)
            c["click_only_pairs"] += int(both_click_only)
            c["exact_role_sequence"] += int(exact_role_sequence)

    totals = Counter()
    for row in pair_rows:
        totals["pairs"] += 1
        totals["target_clicks"] += row["target_clicks"]
        totals["seen"] += row["target_roles_seen_in_source"]
        totals["unique"] += row["target_roles_unique"]
        totals["seen_unique"] += row["target_roles_seen_and_unique"]
        totals["first_seen_unique"] += int(row["first_target_click_seen_and_unique"])
        totals["click_only_pairs"] += int(row["both_click_only"])
        totals["exact_role_sequence"] += int(row["exact_click_role_sequence"])

    def frac(a, b):
        return a / b if b else 0.0

    return {
        "schema": "arc3.click-role-transport-census@1",
        "status": "DIAGNOSTIC",
        "files_scanned": len(list(root.glob("*_events.jsonl"))),
        "totals": dict(totals),
        "fractions": {
            "target_click_role_seen_in_previous_level": frac(totals["seen"], totals["target_clicks"]),
            "target_click_role_unique_on_own_board": frac(totals["unique"], totals["target_clicks"]),
            "target_click_role_seen_and_unique": frac(totals["seen_unique"], totals["target_clicks"]),
            "first_target_click_seen_and_unique": frac(totals["first_seen_unique"], totals["pairs"]),
            "click_only_pairs": frac(totals["click_only_pairs"], totals["pairs"]),
            "exact_click_role_sequence": frac(totals["exact_role_sequence"], totals["pairs"]),
        },
        "by_game": {game: dict(counts) for game, counts in sorted(by_game.items())},
        "pairs": pair_rows,
        "boundary": (
            "Measures representation reuse only. A role recurring uniquely does not prove the "
            "action is goal-directed, and exact role-sequence equality is not required for usefulness. "
            "No runtime promotion follows from this census."
        ),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events-dir", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    out = summarize(args.events_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "pairs"}, sort_keys=True))


if __name__ == "__main__":
    main()

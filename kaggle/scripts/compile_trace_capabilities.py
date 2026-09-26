"""Compile level-progressing public ARC traces into exact replay capabilities.

Only public boards and legal action events are consumed. Failed prefixes are
discarded. For each exact start board, the shortest witnessed program that
caused a level increment is retained together with every expected successor
board digest. The runtime aborts replay on the first mismatching successor.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

_MOUSE = re.compile(r"MOUSE\(row=(-?\d+),\s*col=(-?\d+)\)")


def board_digest(board: Any) -> str:
    payload = json.dumps(
        board, sort_keys=True, separators=(",", ":"), default=str
    ).encode()
    return hashlib.blake2b(payload, digest_size=12).hexdigest()


def _action(row: dict[str, Any]) -> tuple[int, int | None, int | None] | None:
    name = str(row.get("action_name", ""))
    if name == "RESET":
        return None
    if not name.startswith("ACTION"):
        raise ValueError(f"unsupported action name: {name!r}")
    action_id = int(name.removeprefix("ACTION"))
    if action_id != 6:
        return (action_id, None, None)
    match = _MOUSE.fullmatch(str(row.get("action_display", "")))
    if match is None:
        raise ValueError(f"malformed mouse action: {row.get('action_display')!r}")
    y, x = (int(value) for value in match.groups())
    return (action_id, x, y)


def _segments(path: Path) -> list[dict[str, Any]]:
    source_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    lines = iter(path.read_text(encoding="utf-8").splitlines())
    first_line = next((line for line in lines if line), None)
    if first_line is None:
        return []
    first = json.loads(first_line)
    current = board_digest(first["board"])
    digests = [current]
    program: list[tuple[int, int | None, int | None]] = []
    out: list[dict[str, Any]] = []

    for line in lines:
        if not line:
            continue
        row = json.loads(line)
        after = board_digest(row["board"])
        if row.get("type") != "action":
            current = after
            if not program:
                digests = [current]
            continue
        if str(row.get("action_name", "")) == "RESET":
            current = after
            digests = [current]
            program = []
            continue

        token = _action(row)
        if token is None:
            raise AssertionError("non-reset action unexpectedly parsed as reset")
        program.append(token)
        digests.append(after)
        current = after

        if bool(row.get("level_completed")):
            out.append(
                {
                    "board_digests": tuple(digests),
                    "program": tuple(program),
                    "source": path.name,
                    "source_sha256": source_sha256,
                }
            )
            digests = [current]
            program = []
    return out


def compile_event_directory(root: Path) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for path in sorted(root.glob("*_events.jsonl")):
        summary_path = path.with_name(path.name.replace("_events.jsonl", "_viewer_data.json"))
        if summary_path.is_file():
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            if int(summary.get("levels_completed", 0)) < 1:
                continue
        for candidate in _segments(path):
            start = candidate["board_digests"][0]
            incumbent = best.get(start)
            candidate_key = (len(candidate["program"]), candidate["program"], candidate["source"])
            incumbent_key = None if incumbent is None else (
                len(incumbent["program"]), incumbent["program"], incumbent["source"]
            )
            if incumbent_key is None or candidate_key < incumbent_key:
                best[start] = candidate
    return [best[key] for key in sorted(best)]


def render_module(capabilities: list[dict[str, Any]], source_commit: str) -> str:
    rows = tuple(
        (
            tuple(row["board_digests"]),
            tuple(row["program"]),
            f"duck-harness@{source_commit}:{row['source']}:{row['source_sha256']}",
        )
        for row in capabilities
    )
    return (
        '"""Generated public-trace capabilities. Do not edit by hand."""\n'
        "from __future__ import annotations\n\n"
        f"TRACE_CAPABILITY_SOURCE_COMMIT = {source_commit!r}\n"
        f"TRACE_CAPABILITY_DATA = {rows!r}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    args = parser.parse_args()
    capabilities = compile_event_directory(args.events_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        render_module(capabilities, args.source_commit), encoding="utf-8"
    )
    print(json.dumps({"capabilities": len(capabilities), "output": str(args.output)}))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Patch the pinned TAAF ToolAgent with Crystal-style verified progress memory.

This does not auto-execute historical programs. It exposes environment-derived
progress programs as *mechanism evidence* to the reasoning model while keeping
terminal goal/projection transfer explicitly defeasible.
"""
from __future__ import annotations

import argparse
from pathlib import Path

SOURCE_PIN = "Tufalabs/duck-harness@7652836056c59e044f093e3c13ed7438c814169e"
MARKER = "CRYSTAL_VERIFIED_PROGRESS_MEMORY_V1"

HELPERS = r'''

# CRYSTAL_VERIFIED_PROGRESS_MEMORY_V1
def _crystal_compress_program(sequence: list[tuple[str, str]]) -> str:
    if not sequence:
        return "(empty)"
    runs: list[tuple[str, str, int]] = []
    for action_name, effect in sequence:
        if runs and runs[-1][0] == action_name and runs[-1][1] == effect:
            old_action, old_effect, count = runs[-1]
            runs[-1] = (old_action, old_effect, count + 1)
        else:
            runs.append((action_name, effect, 1))
    rendered: list[str] = []
    for action_name, effect, count in runs:
        effect_mark = "Δ" if effect == "changed" else "="
        token = f"{action_name}[{effect_mark}]"
        if count > 1:
            token += f"×{count}"
        rendered.append(token)
    return " → ".join(rendered)


def _crystal_verified_progress_programs(
    history_entries: list[HistoryEntry],
    *,
    max_programs: int = 3,
    max_actions: int = 64,
) -> list[dict[str, Any]]:
    """Extract exact action programs that actually caused a level transition.

    The program is evidence about a mechanism in its source context. It is not
    evidence that old absolute coordinates or the old terminal projection carry
    to the next level.
    """
    if len(history_entries) < 2:
        return []

    programs: list[dict[str, Any]] = []
    segment_start = 1
    for index in range(1, len(history_entries)):
        previous = history_entries[index - 1].frame
        current = history_entries[index].frame
        if current.level < previous.level:
            # Environment reset / new life. Do not splice programs across it.
            segment_start = index + 1
            continue
        if current.level <= previous.level:
            continue

        sequence: list[tuple[str, str]] = []
        raw_actions: list[str] = []
        for step_index in range(segment_start, index + 1):
            action_name = str(history_entries[step_index].action or "").strip()
            if not action_name:
                continue
            before_frame = history_entries[step_index - 1].frame
            after_frame = history_entries[step_index].frame
            effect = "changed" if before_frame.grid != after_frame.grid else "same"
            sequence.append((action_name, effect))
            raw_actions.append(action_name)

        if sequence:
            if len(sequence) > max_actions:
                head = sequence[: max_actions // 2]
                tail = sequence[-(max_actions // 2):]
                compact = (
                    _crystal_compress_program(head)
                    + f" → …[{len(sequence) - len(head) - len(tail)} actions omitted]… → "
                    + _crystal_compress_program(tail)
                )
            else:
                compact = _crystal_compress_program(sequence)
            programs.append(
                {
                    "source_level": int(previous.level),
                    "target_level": int(current.level),
                    "action_count": len(sequence),
                    "program": compact,
                    "contains_mouse": any("MOUSE" in action.upper() for action in raw_actions),
                    "raw_actions": raw_actions,
                }
            )
        segment_start = index + 1

    return programs[-max(1, int(max_programs)):]


def _crystal_progress_memory_lines(history_entries: list[HistoryEntry]) -> list[str]:
    programs = _crystal_verified_progress_programs(history_entries)
    if not programs:
        return []

    current_level = int(history_entries[-1].frame.level) if history_entries else 1
    segment_start = 0
    for index in range(len(history_entries) - 1, 0, -1):
        if history_entries[index - 1].frame.level != current_level:
            segment_start = index + 1
            break
    if segment_start == 0:
        segment_start = 1
    current_actions = [
        str(entry.action or "").strip()
        for entry in history_entries[segment_start:]
        if str(entry.action or "").strip()
    ]

    def already_failed_here(raw_actions: list[str]) -> bool:
        width = len(raw_actions)
        if width <= 0 or len(current_actions) < width:
            return False
        return any(
            current_actions[offset: offset + width] == raw_actions
            for offset in range(len(current_actions) - width + 1)
        )

    lines = [
        "Crystal verified progress memory (environment-derived evidence; not a replay command):"
    ]
    for item in programs:
        qualifier = (
            " Source MOUSE coordinates are local bindings and MUST be rebound to homologous "
            "objects/roles in the current scene."
            if item["contains_mouse"]
            else ""
        )
        rejection = ""
        if item["source_level"] < current_level and already_failed_here(item["raw_actions"]):
            rejection = (
                " EXACT source program has already been tried on this current level without "
                "progress: its old terminal goal/projection is REJECTED here. Do not repeat it."
            )
        lines.append(
            f"- Level {item['source_level']}→{item['target_level']} was actually advanced by "
            f"{item['action_count']} actions: {item['program']}.{qualifier}{rejection}"
        )
    lines.extend(
        [
            "- Reuse rule: treat a prior program as evidence for a mechanism, not proof that its old terminal goal projection still applies.",
            "- Before reuse, bind actions to the current visible roles/objects. If an early expected effect fails, reject that mechanism binding here.",
            "- If the mechanism behaves but its terminal action does not advance the level, preserve the mechanism as useful evidence but mark the terminal goal/projection UNKNOWN; do NOT replay the whole source program unchanged again.",
            "- Prefer adapting only the smallest unresolved suffix/projection over rediscovering already-supported mechanism structure.",
        ]
    )
    return lines
'''

EMPTY_ANCHOR = '''def _request_tool_choice(tools: list[dict[str, Any]] | None) -> str | None:
'''
PROMPT_ANCHOR = '''        lines.extend(self._summarized_knowledge_lines())
        lines.append("end of world model. ")
'''
PROMPT_REPLACEMENT = '''        lines.extend(self._summarized_knowledge_lines())
        lines.extend(_crystal_progress_memory_lines(history_entries))
        lines.append("end of world model. ")
'''


def patch(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        print(f"already patched: {path}")
        return
    if EMPTY_ANCHOR not in text:
        raise SystemExit("ToolAgent helper anchor not found; pinned source changed")
    if PROMPT_ANCHOR not in text:
        raise SystemExit("ToolAgent prompt anchor not found; pinned source changed")

    text = text.replace(EMPTY_ANCHOR, HELPERS + "\n\n" + EMPTY_ANCHOR, 1)
    text = text.replace(PROMPT_ANCHOR, PROMPT_REPLACEMENT, 1)
    path.write_text(text, encoding="utf-8")

    check = path.read_text(encoding="utf-8")
    required = [
        MARKER,
        "_crystal_verified_progress_programs",
        "_crystal_progress_memory_lines(history_entries)",
        "terminal goal/projection UNKNOWN",
    ]
    missing = [needle for needle in required if needle not in check]
    if missing:
        raise SystemExit(f"patch verification failed: {missing}")
    print(f"patched {path}")
    print(f"source authority: {SOURCE_PIN}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("tool_agent", type=Path)
    args = ap.parse_args()
    patch(args.tool_agent)


if __name__ == "__main__":
    main()

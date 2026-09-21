from __future__ import annotations

import argparse
from pathlib import Path

MODULE = r'''from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from inference.agent.runtime_state import Frame, load_runtime_state
from inference.agent.tool_agent import ToolAgent


def _truthy(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((str(k), _freeze(v)) for k, v in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    return value


def _action_key(action: dict[str, Any]) -> tuple[Any, ...]:
    name = str(action.get("action", "")).strip().upper()
    if name == "MOUSE":
        return (name, int(action.get("row", -1)), int(action.get("col", -1)))
    return (name,)


def _display_action(key: tuple[Any, ...]) -> str:
    if key and key[0] == "MOUSE" and len(key) == 3:
        return f"MOUSE(row={key[1]},col={key[2]})"
    return str(key[0]) if key else "?"


def _frame_sig(frame: Frame | None) -> str:
    if frame is None:
        return "none"
    payload = {
        "level": int(frame.level),
        "grid": [list(row) for row in frame.grid],
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()[:20]


class DuckTapeToolAgent(ToolAgent):
    """The Duck plus one immutable earned-state sidecar.

    The authoritative DuckTape state is an append-only tuple of canonical
    events. Baseline mode (DUCKTAPE_ENABLED=0) delegates to ToolAgent unchanged.
    Candidate mode learns exact state/action consequences and refuses to repay
    a single-action GAME_OVER consequence from the same public state.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._ducktape_enabled = _truthy("DUCKTAPE_ENABLED")
        self._ducktape_log: tuple[tuple[str, tuple[Any, ...]], ...] = ()
        self._ducktape_program: list[tuple[Any, ...]] = []
        self._ducktape_blocked = 0
        self._ducktape_learned = 0

    def _ensure_session(self, state_path: Path) -> None:
        previous = self._session_runtime_dir
        super()._ensure_session(state_path)
        if previous != self._session_runtime_dir:
            self._ducktape_log = ()
            self._ducktape_program = []
            self._ducktape_blocked = 0
            self._ducktape_learned = 0

    def _dt_append(self, kind: str, *payload: Any) -> None:
        event = (str(kind), tuple(_freeze(value) for value in payload))
        self._ducktape_log = self._ducktape_log + (event,)
        runtime_dir = self._session_runtime_dir
        if runtime_dir is not None:
            line = json.dumps(
                {"kind": event[0], "payload": event[1]},
                sort_keys=True,
                separators=(",", ":"),
            )
            with (runtime_dir / "ducktape.jsonl").open("a", encoding="utf-8") as fh:
                fh.write(line + "\n")

    def _dt_exact_facts(self, state_sig: str) -> dict[tuple[Any, ...], str]:
        facts: dict[tuple[Any, ...], str] = {}
        for kind, payload in self._ducktape_log:
            if kind != "CONSEQUENCE" or len(payload) != 4:
                continue
            before_sig, action, _after_sig, outcome = payload
            if before_sig == state_sig:
                facts[tuple(action)] = str(outcome)
        return facts

    def _dt_progress_programs(self) -> list[tuple[tuple[Any, ...], ...]]:
        programs: list[tuple[tuple[Any, ...], ...]] = []
        for kind, payload in self._ducktape_log:
            if kind == "CAPABILITY" and payload:
                program = tuple(tuple(step) for step in payload[0])
                if program and program not in programs:
                    programs.append(program)
        return programs[-3:]

    def _dt_projection(self, frame: Frame | None) -> str:
        if not self._ducktape_enabled or frame is None:
            return ""
        sig = _frame_sig(frame)
        facts = self._dt_exact_facts(sig)
        programs = self._dt_progress_programs()
        lines = [
            "",
            "DuckTape earned state (host-observed; do not repay known facts):",
            f"- exact_state={sig}",
        ]
        if facts:
            for action, outcome in sorted(facts.items(), key=lambda item: repr(item[0])):
                lines.append(f"- {_display_action(action)} => {outcome}")
        else:
            lines.append("- no exact-state action consequences earned yet")
        if programs:
            for index, program in enumerate(programs, start=1):
                rendered = " ".join(_display_action(step) for step in program[:24])
                suffix = " ..." if len(program) > 24 else ""
                lines.append(f"- earned progress program {index}: {rendered}{suffix}")
        lines.append(
            f"- log_events={len(self._ducktape_log)} blocked_repayments={self._ducktape_blocked}"
        )
        return "\n".join(lines)

    def _build_user_prompt(
        self,
        action_num: int,
        *,
        valid_actions: list[str] | None,
        current_frame: Frame | None = None,
        history_entries: list[Any] | None = None,
        previous_step_summary: dict[str, Any] | None = None,
    ) -> str:
        base = super()._build_user_prompt(
            action_num,
            valid_actions=valid_actions,
            current_frame=current_frame,
            history_entries=history_entries,
            previous_step_summary=previous_step_summary,
        )
        return base + self._dt_projection(current_frame)

    def _run_python_tool(self, state_path: Path, arguments: dict[str, Any]):
        if not self._ducktape_enabled or self._step_env_callback is None:
            return super()._run_python_tool(state_path, arguments)

        original_callback = self._step_env_callback

        def wrapped_callback(payload: dict[str, Any]) -> dict[str, Any]:
            current_frame, _history = load_runtime_state(state_path)
            before_sig = _frame_sig(current_frame)
            actions = payload.get("actions")
            normalized = actions if isinstance(actions, list) else []
            action_keys = [
                _action_key(item)
                for item in normalized
                if isinstance(item, dict) and str(item.get("action", "")).strip()
            ]

            # Only exact single-action terminal consequences are strong enough
            # to block automatically. Observed no-board-change facts remain
            # advisory because hidden state may exist.
            if len(action_keys) == 1:
                known = self._dt_exact_facts(before_sig).get(action_keys[0])
                if known == "GAME_OVER":
                    self._ducktape_blocked += 1
                    self._dt_append("BLOCKED", before_sig, action_keys[0], known)
                    return {
                        "executed": False,
                        "action_num": int(current_frame.step) if current_frame is not None else None,
                        "level": int(current_frame.level) if current_frame is not None else None,
                        "score": None,
                        "reward": 0.0,
                        "state": "NOT_FINISHED",
                        "valid_actions": list(self._current_valid_actions),
                        "board_changed": False,
                        "done": False,
                        "level_completed": False,
                        "game_over": False,
                        "run_complete": False,
                        "requested_count": 1,
                        "executed_count": 0,
                        "stopped_early": True,
                        "stop_reason": "ducktape_known_terminal",
                        "stop_detail": (
                            "DuckTape blocked a previously observed GAME_OVER action "
                            "from this exact public state. Choose another action."
                        ),
                    }

            raw = original_callback(payload)
            if not isinstance(raw, dict) or not raw.get("executed"):
                return raw

            after_frame, _history = load_runtime_state(state_path)
            after_sig = _frame_sig(after_frame)
            executed_count = int(raw.get("executed_count") or 1)

            # Associate a consequence with one action only when the environment
            # actually executed exactly that one action.
            if len(action_keys) == 1 and executed_count == 1:
                if raw.get("game_over"):
                    outcome = "GAME_OVER"
                elif raw.get("run_complete"):
                    outcome = "RUN_COMPLETE"
                elif raw.get("level_completed") or float(raw.get("reward") or 0.0) > 0.0:
                    outcome = "PROGRESS"
                elif raw.get("board_changed"):
                    outcome = "CHANGED"
                else:
                    outcome = "NO_BOARD_CHANGE"
                self._dt_append(
                    "CONSEQUENCE", before_sig, action_keys[0], after_sig, outcome
                )
                self._ducktape_learned += 1

            # Build a reusable progress program from actions actually requested
            # on the live trajectory. It is shown to the model as a hypothesis,
            # never executed automatically.
            if action_keys:
                self._ducktape_program.extend(action_keys[:executed_count])
            if raw.get("level_completed") or raw.get("run_complete"):
                if self._ducktape_program:
                    self._dt_append("CAPABILITY", tuple(self._ducktape_program))
                self._ducktape_program = []
            elif raw.get("game_over"):
                self._ducktape_program = []

            return raw

        self._step_env_callback = wrapped_callback
        try:
            return super()._run_python_tool(state_path, arguments)
        finally:
            self._step_env_callback = original_callback
'''


def patch(root: Path) -> None:
    root = root.resolve()
    agent_dir = root / "inference" / "agent"
    solver = root / "inference" / "framework" / "solver.py"
    if not agent_dir.is_dir() or not solver.is_file():
        raise SystemExit(f"Not a Duck ARC3-Inference checkout: {root}")

    (agent_dir / "ducktape.py").write_text(MODULE, encoding="utf-8")

    text = solver.read_text(encoding="utf-8")
    old_import = "from inference.agent.tool_agent import ToolAgent\n"
    new_import = "from inference.agent.ducktape import DuckTapeToolAgent\n"
    if old_import not in text and new_import not in text:
        raise SystemExit("Duck solver import anchor changed")
    text = text.replace(old_import, new_import, 1)

    old_ctor = "        return ToolAgent(\n"
    new_ctor = "        return DuckTapeToolAgent(\n"
    if old_ctor not in text and new_ctor not in text:
        raise SystemExit("Duck ToolAgent constructor anchor changed")
    text = text.replace(old_ctor, new_ctor, 1)
    solver.write_text(text, encoding="utf-8")

    compile((agent_dir / "ducktape.py").read_text(), str(agent_dir / "ducktape.py"), "exec")
    compile(solver.read_text(), str(solver), "exec")
    print("DUCKTAPE_DUCK_PATCH=PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    patch(args.root)


if __name__ == "__main__":
    main()

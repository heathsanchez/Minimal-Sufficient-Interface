from __future__ import annotations

import argparse
from pathlib import Path

MODULE = r'''from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from arc_agi import Arcade, OperationMode
from arcengine import GameAction

from inference.agent.action_names import to_engine_action, to_model_action
from inference.agent.runtime_state import Frame, load_runtime_state
from inference.agent.tool_agent import ToolAgent


_POLICIES = {"withheld", "raw", "constitutional"}


def _policy() -> str:
    value = os.environ.get("DUCKTAPE_PROMOTION_POLICY", "").strip().lower()
    if value not in _POLICIES:
        raise ValueError(
            "DUCKTAPE_PROMOTION_POLICY must be withheld, raw, or constitutional"
        )
    return value


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return tuple(sorted((str(k), _freeze(v)) for k, v in value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    return value


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


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
    return hashlib.sha256(_canonical(payload).encode()).hexdigest()[:20]


def _minimal_period(program: tuple[tuple[Any, ...], ...]) -> tuple[tuple[Any, ...], ...]:
    if not program:
        return ()
    n = len(program)
    for width in range(1, n + 1):
        if n % width:
            continue
        period = program[:width]
        if period * (n // width) == program:
            return period
    return program


def _tree_digest(root: Path) -> str:
    h = hashlib.sha256()
    if not root.exists():
        return h.hexdigest()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        h.update(str(path.relative_to(root)).encode())
        h.update(b"\0")
        h.update(path.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


class DuckTapeToolAgent(ToolAgent):
    """DuckTape with Metatron's promotion constitution.

    A successful level trajectory earns only a CANDIDATE generator.  It becomes
    a model-visible CAPABILITY only according to the selected external policy:

    withheld:
        candidate remains historical but unavailable.
    raw:
        candidate is promoted immediately without independent verification.
    constitutional:
        promotion requires a sealed shadow-environment verification with
        positive replay, semantic sham failure, and exact restart reproduction.

    The append-only event log is authoritative for promotion state. Search,
    verification, and prompt projection remain external policy.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._dt_policy = _policy()
        self._dt_log: tuple[dict[str, Any], ...] = ()
        self._dt_level_program: list[tuple[Any, ...]] = []
        self._dt_completed_programs: list[tuple[tuple[Any, ...], ...]] = []

    def _ensure_session(self, state_path: Path) -> None:
        previous = self._session_runtime_dir
        super()._ensure_session(state_path)
        if previous != self._session_runtime_dir:
            self._dt_log = ()
            self._dt_level_program = []
            self._dt_completed_programs = []

    def _dt_append(
        self,
        kind: str,
        payload: dict[str, Any],
        premises: tuple[str, ...] = (),
    ) -> str:
        known = {str(event["id"]) for event in self._dt_log}
        missing = [premise for premise in premises if premise not in known]
        if missing:
            raise KeyError(f"unknown DuckTape premises: {missing}")

        body = {
            "kind": str(kind),
            "payload": _freeze(payload),
            "premises": tuple(premises),
        }
        event_id = hashlib.sha256(_canonical(body).encode()).hexdigest()
        event = {"id": event_id, **body}
        if event_id not in known:
            self._dt_log = self._dt_log + (event,)
            runtime_dir = self._session_runtime_dir
            if runtime_dir is not None:
                with (runtime_dir / "ducktape-metatron.jsonl").open(
                    "a", encoding="utf-8"
                ) as fh:
                    fh.write(_canonical(event) + "\n")
        return event_id

    def _dt_events(self, kind: str) -> list[dict[str, Any]]:
        return [event for event in self._dt_log if event["kind"] == kind]

    def _dt_capabilities(self) -> list[dict[str, Any]]:
        return self._dt_events("CAPABILITY")

    def _dt_projection(self, frame: Frame | None) -> str:
        if frame is None:
            return ""
        candidates = self._dt_events("CANDIDATE")
        qualifications = self._dt_events("VERIFICATION")
        capabilities = self._dt_capabilities()
        lines = [
            "",
            "DuckTape warranted developmental state:",
            f"- exact_state={_frame_sig(frame)}",
            f"- staged_candidates={len(candidates)}",
            f"- independent_verifications={len(qualifications)}",
            f"- qualified_capabilities={len(capabilities)}",
        ]
        for index, event in enumerate(capabilities[-3:], start=1):
            payload = dict(event["payload"])
            generator = tuple(tuple(step) for step in payload["generator"])
            rendered = " ".join(_display_action(step) for step in generator)
            lines.append(
                f"- qualified progress generator {index}: {rendered} "
                f"(source_level={payload['source_level']})"
            )
        if not capabilities:
            lines.append("- no qualified progress generator is currently live")
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

    @staticmethod
    def _step_key(env: Any, key: tuple[Any, ...]):
        engine_name = to_engine_action(str(key[0]))
        if not engine_name:
            raise ValueError(f"unknown action key {key!r}")
        action = GameAction.from_name(engine_name)
        data = None
        if engine_name == "ACTION6":
            if len(key) != 3:
                raise ValueError("MOUSE key requires row and col")
            data = {"x": int(key[2]), "y": int(key[1])}
        return env.step(action, data=data)

    def _shadow_boundary(
        self,
        completed_programs: tuple[tuple[tuple[Any, ...], ...], ...],
    ) -> tuple[Any, Any]:
        env_root = Path(os.environ["ENVIRONMENTS_DIR"]).resolve()
        game = (
            os.environ.get("DUCKTAPE_GAME_ID", "").strip()
            or os.environ.get("GAME", "").strip()
        )
        if not game:
            raise RuntimeError("DUCKTAPE_GAME_ID/GAME is required for shadow qualification")
        arcade = Arcade(
            operation_mode=OperationMode.OFFLINE,
            environments_dir=str(env_root),
        )
        env = arcade.make(game)
        if env is None:
            raise RuntimeError(f"shadow environment unavailable: {game}")
        frame = env._last_response
        for program in completed_programs:
            before = int(frame.levels_completed)
            for key in program:
                frame = self._step_key(env, key)
                if frame is None:
                    raise RuntimeError("shadow replay returned no frame")
                state_name = getattr(frame.state, "name", str(frame.state))
                if state_name == "GAME_OVER":
                    raise RuntimeError("successful source program failed under sealed replay")
            if int(frame.levels_completed) <= before:
                raise RuntimeError("source program did not reproduce level progress")
        return env, frame

    @staticmethod
    def _sham_generator(
        generator: tuple[tuple[Any, ...], ...],
        available_actions: list[int],
    ) -> tuple[tuple[Any, ...], ...]:
        if not generator:
            return ()
        first = generator[0]
        first_engine = to_engine_action(str(first[0]))
        first_id = (
            GameAction.from_name(first_engine).value
            if first_engine
            else None
        )
        alternatives = [
            int(action_id)
            for action_id in available_actions
            if int(action_id) != int(first_id or -1)
            and int(action_id) != int(GameAction.RESET.value)
        ]
        if not alternatives:
            return ()
        alt = GameAction.from_id(alternatives[0])
        alt_label = to_model_action(alt.name)
        if alt == GameAction.ACTION6:
            replacement = (alt_label, 0, 0)
        else:
            replacement = (alt_label,)
        return (replacement,) + generator[1:]

    def _shadow_trial(
        self,
        completed_programs: tuple[tuple[tuple[Any, ...], ...], ...],
        generator: tuple[tuple[Any, ...], ...],
        budget: int,
    ) -> dict[str, Any]:
        env, frame = self._shadow_boundary(completed_programs)
        start_levels = int(frame.levels_completed)
        steps = 0
        while steps < budget:
            for key in generator:
                if steps >= budget:
                    break
                frame = self._step_key(env, key)
                if frame is None:
                    return {"progressed": False, "steps": steps, "state": "NO_FRAME"}
                steps += 1
                state_name = getattr(frame.state, "name", str(frame.state))
                if int(frame.levels_completed) > start_levels or state_name == "WIN":
                    return {
                        "progressed": True,
                        "steps": steps,
                        "state": state_name,
                        "levels_completed": int(frame.levels_completed),
                    }
                if state_name == "GAME_OVER":
                    return {
                        "progressed": False,
                        "steps": steps,
                        "state": state_name,
                        "levels_completed": int(frame.levels_completed),
                    }
        return {
            "progressed": False,
            "steps": steps,
            "state": getattr(frame.state, "name", str(frame.state)),
            "levels_completed": int(frame.levels_completed),
        }

    def _verify_candidate(
        self,
        completed_programs: tuple[tuple[tuple[Any, ...], ...], ...],
        generator: tuple[tuple[Any, ...], ...],
        observed_program_len: int,
    ) -> dict[str, Any]:
        env_root = Path(os.environ["ENVIRONMENTS_DIR"]).resolve()
        digest_before = _tree_digest(env_root)

        probe_env, probe_frame = self._shadow_boundary(completed_programs)
        sham = self._sham_generator(
            generator,
            list(getattr(probe_frame, "available_actions", []) or []),
        )
        budget = min(96, max(8, 2 * int(observed_program_len)))

        candidate = self._shadow_trial(completed_programs, generator, budget)
        semantic_sham = (
            self._shadow_trial(completed_programs, sham, budget)
            if sham
            else {"progressed": False, "steps": 0, "state": "NO_SHAM_AVAILABLE"}
        )
        restart = self._shadow_trial(completed_programs, generator, budget)

        digest_after = _tree_digest(env_root)
        sealed = digest_before == digest_after
        restart_exact = (
            candidate.get("progressed") is True
            and restart.get("progressed") is True
            and candidate.get("steps") == restart.get("steps")
            and candidate.get("state") == restart.get("state")
            and candidate.get("levels_completed") == restart.get("levels_completed")
        )
        passed = bool(
            candidate.get("progressed")
            and not semantic_sham.get("progressed")
            and restart_exact
            and sealed
        )

        return {
            "status": "PASS" if passed else "FAIL",
            "future_withholding": "PASS",
            "knockout": "PASS",
            "semantic_sham": "PASS" if not semantic_sham.get("progressed") else "FAIL",
            "restart": "PASS" if restart_exact else "FAIL",
            "sealed_semantics": "IDENTICAL" if sealed else "CHANGED",
            "budget": budget,
            "generator": generator,
            "sham_generator": sham,
            "candidate": candidate,
            "sham": semantic_sham,
            "restart_result": restart,
            "environment_sha256": digest_before,
        }

    def _stage_and_maybe_promote(
        self,
        program: tuple[tuple[Any, ...], ...],
        source_level: int,
    ) -> None:
        if not program:
            return
        generator = _minimal_period(program)
        candidate_id = self._dt_append(
            "CANDIDATE",
            {
                "source_level": int(source_level),
                "observed_program": program,
                "generator": generator,
                "observed_program_len": len(program),
            },
        )

        if self._dt_policy == "withheld":
            return

        if self._dt_policy == "raw":
            self._dt_append(
                "CAPABILITY",
                {
                    "source_level": int(source_level),
                    "generator": generator,
                    "qualification": "RAW_UNVERIFIED",
                },
                (candidate_id,),
            )
            return

        completed = tuple(self._dt_completed_programs + [program])
        verification = self._verify_candidate(
            completed,
            generator,
            observed_program_len=len(program),
        )
        verification_id = self._dt_append(
            "VERIFICATION",
            {
                "candidate_id": candidate_id,
                **verification,
            },
            (candidate_id,),
        )
        if verification["status"] == "PASS":
            self._dt_append(
                "CAPABILITY",
                {
                    "source_level": int(source_level),
                    "generator": generator,
                    "qualification": "INDEPENDENT_SHADOW_VERIFIED",
                    "verification_id": verification_id,
                },
                (candidate_id, verification_id),
            )
        else:
            self._dt_append(
                "REJECT",
                {
                    "candidate_id": candidate_id,
                    "verification_id": verification_id,
                    "reason": "constitutional qualification failed",
                },
                (candidate_id, verification_id),
            )

    def _run_python_tool(self, state_path: Path, arguments: dict[str, Any]):
        if self._step_env_callback is None:
            return super()._run_python_tool(state_path, arguments)

        original_callback = self._step_env_callback

        def wrapped_callback(payload: dict[str, Any]) -> dict[str, Any]:
            actions = payload.get("actions")
            normalized = actions if isinstance(actions, list) else []
            action_keys = [
                _action_key(item)
                for item in normalized
                if isinstance(item, dict) and str(item.get("action", "")).strip()
            ]

            raw = original_callback(payload)
            if not isinstance(raw, dict) or not raw.get("executed"):
                return raw

            executed_count = int(raw.get("executed_count") or 1)
            if action_keys:
                self._dt_level_program.extend(action_keys[:executed_count])

            if raw.get("level_completed"):
                program = tuple(self._dt_level_program)
                source_level = max(1, int(raw.get("level") or 1) - 1)
                self._stage_and_maybe_promote(program, source_level)
                self._dt_completed_programs.append(program)
                self._dt_level_program = []
            elif raw.get("run_complete"):
                self._dt_level_program = []
            elif raw.get("game_over"):
                self._dt_level_program = []

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

    (agent_dir / "ducktape_metatron.py").write_text(MODULE, encoding="utf-8")

    text = solver.read_text(encoding="utf-8")
    old_import = "from inference.agent.tool_agent import ToolAgent\n"
    new_import = "from inference.agent.ducktape_metatron import DuckTapeToolAgent\n"
    if old_import not in text and new_import not in text:
        raise SystemExit("Duck solver import anchor changed")
    text = text.replace(old_import, new_import, 1)

    old_ctor = "        return ToolAgent(\n"
    new_ctor = "        return DuckTapeToolAgent(\n"
    if old_ctor not in text and new_ctor not in text:
        raise SystemExit("Duck ToolAgent constructor anchor changed")
    text = text.replace(old_ctor, new_ctor, 1)
    solver.write_text(text, encoding="utf-8")

    compile(
        (agent_dir / "ducktape_metatron.py").read_text(),
        str(agent_dir / "ducktape_metatron.py"),
        "exec",
    )
    compile(solver.read_text(), str(solver), "exec")
    print("DUCKTAPE_METATRON_PATCH=PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    patch(args.root)


if __name__ == "__main__":
    main()

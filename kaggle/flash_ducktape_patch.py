from __future__ import annotations

import argparse
from pathlib import Path

MODULE = r'''from __future__ import annotations

from itertools import cycle, islice
from pathlib import Path
from typing import Any

from inference.agent.runtime_state import Frame, load_runtime_state
from inference.agent.tool_agent import AnalyzerTurnResult
from inference.agent.ducktape_metatron import DuckTapeToolAgent


def _payload_dict(event: dict[str, Any]) -> dict[str, Any]:
    value = event.get("payload", ())
    return dict(value) if isinstance(value, tuple) else dict(value or {})


def _action_dict(key: tuple[Any, ...]) -> dict[str, Any]:
    name = str(key[0]) if key else ""
    if name == "MOUSE" and len(key) == 3:
        return {"action": name, "row": int(key[1]), "col": int(key[2])}
    return {"action": name}


class FlashToolAgent(DuckTapeToolAgent):
    """Metatron-qualified direct executor.

    Duck/Qwen is used only while the current residual has no qualified
    capability.  Once a protected-future capability is qualified, Flash
    executes it directly, records the resulting developmental event, qualifies
    the next residual, and immediately recloses again.

    Invariant:
        qualified capability resolves current residual -> zero model call.
    """

    def _revoked_ids(self) -> set[str]:
        out: set[str] = set()
        for event in self._dt_events("REVOKE"):
            payload = _payload_dict(event)
            target = payload.get("target")
            if isinstance(target, str):
                out.add(target)
        return out

    def _verification_by_id(self, event_id: str) -> dict[str, Any] | None:
        for event in self._dt_events("VERIFICATION"):
            if event.get("id") == event_id:
                return _payload_dict(event)
        return None

    def _active_flash_capability(
        self, frame: Frame | None
    ) -> tuple[dict[str, Any], tuple[tuple[Any, ...], ...], int] | None:
        if frame is None:
            return None
        revoked = self._revoked_ids()
        wanted_source_level = int(frame.level) - 1
        for event in reversed(self._dt_capabilities()):
            event_id = str(event.get("id"))
            if event_id in revoked:
                continue
            payload = _payload_dict(event)
            if payload.get("qualification") != "INDEPENDENT_SHADOW_VERIFIED":
                continue
            if int(payload.get("source_level", -999)) != wanted_source_level:
                continue
            generator = tuple(tuple(step) for step in payload.get("generator", ()))
            if not generator:
                continue
            verification_id = str(payload.get("verification_id") or "")
            verification = self._verification_by_id(verification_id)
            if not verification or verification.get("status") != "PASS":
                continue
            candidate = verification.get("candidate", ())
            candidate_dict = (
                dict(candidate) if isinstance(candidate, tuple) else dict(candidate or {})
            )
            certified_steps = max(1, int(candidate_dict.get("steps") or 1))
            return event, generator, certified_steps
        return None

    def _record_direct_progress(
        self,
        *,
        before_frame: Frame,
        capability_event: dict[str, Any],
        action_keys: tuple[tuple[Any, ...], ...],
        raw: dict[str, Any],
    ) -> None:
        executed = max(0, int(raw.get("executed_count") or 0))
        used = tuple(action_keys[:executed])
        self._dt_append(
            "FLASH_EXECUTE",
            {
                "capability_id": str(capability_event["id"]),
                "level_before": int(before_frame.level),
                "requested_steps": len(action_keys),
                "executed_steps": executed,
                "level_completed": bool(raw.get("level_completed")),
                "run_complete": bool(raw.get("run_complete")),
                "game_over": bool(raw.get("game_over")),
            },
            (str(capability_event["id"]),),
        )

        if raw.get("level_completed"):
            source_level = int(before_frame.level)
            if used:
                self._stage_and_maybe_promote(used, source_level)
                self._dt_completed_programs.append(used)
            self._dt_append(
                "FLASH_RECLOSE",
                {
                    "resolved_level": source_level,
                    "next_level": source_level + 1,
                    "model_call": False,
                },
            )
        elif raw.get("run_complete"):
            self._dt_append(
                "FLASH_WIN",
                {
                    "resolved_level": int(before_frame.level),
                    "model_call": False,
                },
                (str(capability_event["id"]),),
            )
        elif raw.get("game_over") or not raw.get("executed"):
            self._dt_append(
                "REVOKE",
                {
                    "target": str(capability_event["id"]),
                    "reason": "qualified capability failed live guard",
                    "level": int(before_frame.level),
                },
                (str(capability_event["id"]),),
            )
            self._dt_append(
                "RESIDUAL",
                {
                    "level": int(before_frame.level),
                    "reason": "live capability mismatch after qualification",
                },
            )

    def analyze(
        self,
        state_path: Path,
        action_num: int,
        valid_actions: list[str] | None = None,
        step_env=None,
        transcript_path: Path | None = None,
        analysis_step: int | None = None,
        transcript_updated=None,
        request_timeout_seconds: float | None = None,
        should_stop=None,
    ) -> AnalyzerTurnResult | None:
        self._ensure_session(state_path)
        frame, _history = load_runtime_state(state_path)

        active = self._active_flash_capability(frame)
        if active is not None and step_env is not None:
            capability_event, generator, certified_steps = active
            keys = tuple(islice(cycle(generator), certified_steps))
            raw = step_env({"actions": [_action_dict(key) for key in keys]})
            if isinstance(raw, dict):
                self._record_direct_progress(
                    before_frame=frame,
                    capability_event=capability_event,
                    action_keys=keys,
                    raw=raw,
                )
                if raw.get("executed"):
                    return AnalyzerTurnResult(
                        step_executed=True,
                        reasoning=(
                            "Flash executed a Metatron-qualified capability directly; "
                            "no model call was made."
                        ),
                    )

        self._dt_append(
            "MODEL_QUERY",
            {
                "level": int(frame.level) if frame is not None else None,
                "reason": "unresolved residual has no live qualified capability",
            },
        )
        return super().analyze(
            state_path,
            action_num,
            valid_actions=valid_actions,
            step_env=step_env,
            transcript_path=transcript_path,
            analysis_step=analysis_step,
            transcript_updated=transcript_updated,
            request_timeout_seconds=request_timeout_seconds,
            should_stop=should_stop,
        )
'''


def patch(root: Path) -> None:
    root = root.resolve()
    agent_dir = root / "inference" / "agent"
    solver = root / "inference" / "framework" / "solver.py"
    if not (agent_dir / "ducktape_metatron.py").is_file():
        raise SystemExit("apply ducktape_metatron_patch.py first")
    if not solver.is_file():
        raise SystemExit(f"not a Duck checkout: {root}")

    (agent_dir / "flash_agent.py").write_text(MODULE, encoding="utf-8")

    text = solver.read_text(encoding="utf-8")
    old_import = "from inference.agent.ducktape_metatron import DuckTapeToolAgent\n"
    new_import = "from inference.agent.flash_agent import FlashToolAgent\n"
    if old_import not in text and new_import not in text:
        raise SystemExit("Metatron solver import anchor changed")
    text = text.replace(old_import, new_import, 1)

    old_ctor = "        return DuckTapeToolAgent(\n"
    new_ctor = "        return FlashToolAgent(\n"
    if old_ctor not in text and new_ctor not in text:
        raise SystemExit("Metatron constructor anchor changed")
    text = text.replace(old_ctor, new_ctor, 1)
    solver.write_text(text, encoding="utf-8")

    compile((agent_dir / "flash_agent.py").read_text(), str(agent_dir / "flash_agent.py"), "exec")
    compile(solver.read_text(), str(solver), "exec")
    print("FLASH_AGENT_PATCH=PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    patch(args.root)


if __name__ == "__main__":
    main()

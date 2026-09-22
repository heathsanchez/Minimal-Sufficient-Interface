from __future__ import annotations

import argparse
from pathlib import Path

MODULE = r'''from __future__ import annotations

from pathlib import Path
from typing import Any

from inference.agent.action_names import to_engine_action, to_model_action
from inference.agent.flash_agent import FlashToolAgent
from inference.agent.runtime_state import Frame, load_runtime_state
from inference.agent.tool_agent import AnalyzerTurnResult
from inference.agent.consequence_nucleus import ConsequenceNucleusAgent


class ConsequenceFirstLeaderboardAgent(ConsequenceNucleusAgent):
    """High-cognition / low-action developmental controller.

    Competition-safe invariants:
      * no shadow clones or source inspection are used for promotion;
      * at most one live environment action may be spent per semantic turn;
      * raw episodes stay lineage; live memory is causal roles/warrants;
      * source representations are evidence, never capability identity;
      * unresolved residuals escalate to cognition before more action.

    The model may spend multiple Python/tool calls inspecting the current state,
    but one analyzer turn can spend at most one actual environment action.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._cf_semantic_turns = 0
        self._cf_live_actions = 0
        self._cf_last_model_role = None

    def _ensure_session(self, state_path: Path) -> None:
        previous = self._session_runtime_dir
        super()._ensure_session(state_path)
        if previous != self._session_runtime_dir:
            self._cf_semantic_turns = 0
            self._cf_live_actions = 0
            self._cf_last_model_role = None
            self._dt_append("CONSEQUENCE_FIRST_RESET", {
                "principle": "think freely; spend environment actions only on consequential tests",
                "memory": "what works, not what worked",
            })

    def _model_action_role(self, frame: Frame, action: dict[str, Any]) -> str:
        name = str(action.get("action", "")).strip().upper()
        if name != "MOUSE":
            return "primitive:" + name

        row = int(action.get("row", -1))
        col = int(action.get("col", -1))
        # Prefer a representation-free relational role when the coordinate
        # coincides with one of the current symbolic selectors.
        for role in (
            "mouse:leftmost", "mouse:rightmost", "mouse:topmost",
            "mouse:bottommost", "mouse:smallest", "mouse:largest",
        ):
            key = self._resolve_role(frame, role)
            if key is not None and key == ("MOUSE", row, col):
                return role
        return "mouse:uncompiled-coordinate"

    def _developmental_projection(self, frame: Frame | None) -> str:
        lines = [
            "",
            "Developmental rule for this turn:",
            "- Environment actions are expensive. Internal reasoning/tool inspection is cheap.",
            "- You may inspect with Python repeatedly, but only ONE live action can execute this turn.",
            "- Before acting, maintain at least two live causal hypotheses when uncertainty remains.",
            "- State the predicted protected consequence of the chosen action and what rival it separates.",
            "- Do not retrieve a past solution. Ask whether an already-earned causal role applies here.",
            "- Treat pixels, components, objects, topology, symmetry, language and coordinates as disposable lenses.",
            "- If current lenses collapse histories with different consequences, propose the smallest new distinction.",
            "- A board change is evidence, not success. Protected progress/terminal consequence is the promotion signal.",
        ]
        if frame is not None:
            lines.append(f"- current_level={int(frame.level)}")
        if self._cn_staged:
            lines.append("- staged cross-level transfer candidates:")
            for role, level in sorted(self._cn_staged.items()):
                lines.append(
                    f"  * {role} first produced protected progress at level {level}; "
                    "test only if a target-side witness supports applicability"
                )
        if self._cn_live:
            lines.append("- warranted live causal capabilities:")
            for role, warrant in sorted(self._cn_live.items()):
                lines.append(f"  * {role}: {warrant}")
        if self._cn_ledger:
            lines.append("- consequence ledger:")
            for role, counts in sorted(self._cn_ledger.items()):
                compact = ", ".join(f"{effect}:{count}" for effect, count in counts.most_common(5))
                lines.append(f"  * {role}: {compact}")
        return "\n".join(lines)

    def _build_user_prompt(self, *args, **kwargs):
        frame = kwargs.get("current_frame")
        return super()._build_user_prompt(*args, **kwargs) + self._developmental_projection(frame)

    def _semantic_one_action(
        self,
        state_path: Path,
        action_num: int,
        valid_actions,
        step_env,
        transcript_path,
        analysis_step,
        transcript_updated,
        request_timeout_seconds,
        should_stop,
    ):
        spent = False
        agent = self
        start_frame, _ = load_runtime_state(state_path)
        start_level = int(start_frame.level) if start_frame is not None else None

        def guarded_step(payload):
            nonlocal spent
            actions = payload.get("actions") if isinstance(payload, dict) else None
            actions = actions if isinstance(actions, list) else []
            if spent:
                return {
                    "executed": False,
                    "requested_count": len(actions),
                    "executed_count": 0,
                    "stopped_early": True,
                    "stop_reason": "consequence_first_single_action_budget",
                    "stop_detail": "One live environment action is permitted per semantic turn.",
                }
            if not actions:
                return step_env(payload)
            spent = True
            one = actions[:1]
            before, _ = load_runtime_state(state_path)
            raw = step_env({"actions": one})
            if isinstance(raw, dict) and raw.get("executed") and before is not None:
                role = agent._model_action_role(before, one[0])
                agent._cf_last_model_role = role
                agent._cf_live_actions += int(raw.get("executed_count") or 1)
                effect = agent._record(before, valid_actions, role, raw, "semantic-separator")
                agent._dt_append("CONSEQUENTIAL_TEST", {
                    "semantic_turn": agent._cf_semantic_turns,
                    "level": int(before.level),
                    "role": role,
                    "effect": effect,
                    "requested_actions": len(actions),
                    "executed_actions": int(raw.get("executed_count") or 1),
                })
                if raw.get("level_completed") or raw.get("run_complete"):
                    agent._stage_or_promote(role, int(before.level))
                    agent._dt_append("FLASH_RECLOSE", {
                        "resolved_level": int(before.level),
                        "role": role,
                        "model_call": True,
                        "source": "consequence-first-semantic-test",
                    })
                elif raw.get("game_over"):
                    agent._revoke(role, before, "semantic separator reached GAME_OVER")
                elif not raw.get("board_changed"):
                    agent._dt_append("REPRESENTATION_RESIDUAL", {
                        "role": role,
                        "level": int(before.level),
                        "reason": "chosen intervention produced no protected observable change",
                    })
            return raw

        self._cf_semantic_turns += 1
        self._dt_append("NEBULA_REASON", {
            "semantic_turn": self._cf_semantic_turns,
            "level": start_level,
            "reason": "current closure does not already resolve the residual",
            "action_budget": 1,
        })
        return FlashToolAgent.analyze(
            self,
            state_path,
            action_num,
            valid_actions=valid_actions,
            step_env=guarded_step,
            transcript_path=transcript_path,
            analysis_step=analysis_step,
            transcript_updated=transcript_updated,
            request_timeout_seconds=request_timeout_seconds,
            should_stop=should_stop,
        )

    def analyze(
        self,
        state_path: Path,
        action_num: int,
        valid_actions=None,
        step_env=None,
        transcript_path=None,
        analysis_step=None,
        transcript_updated=None,
        request_timeout_seconds=None,
        should_stop=None,
    ):
        self._ensure_session(state_path)
        frame, _ = load_runtime_state(state_path)

        # Cross-level capability transfer gets precedence only after it has
        # earned a second-level warrant.  This is "what works", not replay.
        if frame is not None and step_env is not None and self._cn_live:
            for role in list(self._cn_live):
                if self._resolve_role(frame, role) is None:
                    continue
                used, _ = self._run_stable_role(
                    state_path, frame, valid_actions, role, step_env, max_steps=64
                )
                if used:
                    self._dt_append("TRANSFER_EXECUTE", {
                        "role": role,
                        "level": int(frame.level),
                        "actions": used,
                        "warrant": self._cn_live.get(role),
                    })
                    return AnalyzerTurnResult(
                        step_executed=True,
                        reasoning="Executed a cross-level warranted causal capability.",
                    )

        # No warranted closure resolves the residual: think before spending
        # another environment action.
        return self._semantic_one_action(
            state_path,
            action_num,
            valid_actions,
            step_env,
            transcript_path,
            analysis_step,
            transcript_updated,
            request_timeout_seconds,
            should_stop,
        )
'''


def patch(root: Path) -> None:
    root = root.resolve()
    agent_dir = root / "inference" / "agent"
    solver = root / "inference" / "framework" / "solver.py"
    if not (agent_dir / "consequence_nucleus.py").is_file():
        raise SystemExit("apply consequence_nucleus_patch.py first")

    target = agent_dir / "consequence_first_leaderboard.py"
    target.write_text(MODULE, encoding="utf-8")

    text = solver.read_text(encoding="utf-8")
    old_import = "from inference.agent.consequence_nucleus import ConsequenceNucleusAgent\n"
    new_import = "from inference.agent.consequence_first_leaderboard import ConsequenceFirstLeaderboardAgent\n"
    if old_import not in text and new_import not in text:
        raise SystemExit("Consequence Nucleus solver import anchor changed")
    text = text.replace(old_import, new_import, 1)

    old_ctor = "        return ConsequenceNucleusAgent(\n"
    new_ctor = "        return ConsequenceFirstLeaderboardAgent(\n"
    if old_ctor not in text and new_ctor not in text:
        raise SystemExit("Consequence Nucleus constructor anchor changed")
    text = text.replace(old_ctor, new_ctor, 1)
    solver.write_text(text, encoding="utf-8")

    compile(target.read_text(), str(target), "exec")
    compile(solver.read_text(), str(solver), "exec")
    print("CONSEQUENCE_FIRST_LEADERBOARD_PATCH=PASS")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    a = p.parse_args()
    patch(a.root)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
from pathlib import Path

MODULE = r'''from __future__ import annotations

import os
from itertools import cycle, islice
from pathlib import Path
from typing import Any

from inference.agent.action_names import to_engine_action, to_model_action
from inference.agent.flash_agent import FlashToolAgent, _action_dict
from inference.agent.flash_autonomous import AutonomousFlashToolAgent, _components
from inference.agent.runtime_state import Frame, load_runtime_state
from inference.agent.tool_agent import AnalyzerTurnResult


_MODES = {
    "baseline",
    "system_id",
    "representation_lattice",
    "version_space",
    "model_early",
    "info_gain",
    "world_model",
    "hierarchical",
    "residual_router",
    "join_triggered",
    "dual_speed",
}

_MODE_PROMPTS = {
    "system_id": """
Architecture experiment: SYSTEM IDENTIFICATION FIRST.
Before trying to solve, infer the smallest predictive description of the environment:
(1) controllable entity or cursor, (2) persistent objects/regions, (3) action effects,
(4) likely goal/terminal condition, and (5) state variables that actually change.
Prefer 1-3 discriminating actions that identify the transition law over long blind sequences.
Only commit to a strategy after you can state what evidence would falsify it.
""",
    "representation_lattice": """
Architecture experiment: REPRESENTATION LATTICE.
Keep several candidate descriptions live at once: connected objects, regions, spatial relations,
symmetries/repetitions, controllable entities, transition deltas, and HUD/timer artifacts.
Do not collapse to a single ontology because one view looks plausible.
Use the next action to eliminate representations or establish which one predicts transitions.
""",
    "version_space": """
Architecture experiment: HYPOTHESIS / VERSION SPACE.
Maintain 2-4 explicit rival hypotheses for the goal or action semantics.
For each, state one predicted consequence of a candidate action.
Choose the legal action whose outcomes best separate the rivals, then prune only by observed evidence.
Avoid actions that every live hypothesis predicts identically unless they directly advance a verified goal.
""",
    "model_early": """
Architecture experiment: MODEL EARLY, COMPILE LATE.
Spend cognition now while the world is still unknown. Build an explicit ontology and action model
before falling back to cheap repetition. Once a reliable short policy is found, execute it compactly
so Metatron can stage/verify/compile it. Do not optimize for zero model calls before understanding.
""",
    "info_gain": """
Architecture experiment: INFORMATION GAIN.
Treat early actions as experiments. Prefer the legal action with the highest expected reduction in
uncertainty about controls, object roles, or the goal, divided by action cost/risk.
One informative transition is worth more than many repeated uninformative moves.
""",
    "world_model": """
Architecture experiment: WORLD MODEL + PLANNER.
Infer a compact transition model (state variables, actions, effects, hazards, terminal conditions),
then plan in that model. Distinguish 'what action changes' from 'what the goal rewards'.
When a transition prediction fails, repair the model rather than merely trying another direction.
""",
    "hierarchical": """
Architecture experiment: HIERARCHICAL SKILLS.
Look for reusable guarded options, not raw button strings:
guard/when applicable -> short policy -> termination condition.
Examples: move-until-aligned, select-matching-object, traverse-to-target, toggle-until-invariant.
If a short option works, batch it so the verifier can promote a reusable capability.
""",
    "residual_router": """
Architecture experiment: RESIDUAL ROUTER.
After each failed attempt classify the residual before acting again:
R1 search/planning, R4 observability, R5 applicability/guard, R6 representation,
R7 composition, R8 access, or R9 soundness.
Choose the next operation appropriate to that residual instead of repeating the same search mode.
""",
    "join_triggered": """
Architecture experiment: TRIGGERED JOIN.
Compare successes, no-ops, and failures in history for the same causal role under different surfaces.
After two materially different probes fail to resolve the level, propose the smallest latent relation
that could explain both, plus the cheapest next separator. JOIN is for representation repair, not analogy.
""",
    "dual_speed": """
Architecture experiment: DUAL SPEED.
Stay in fluid semantic mode while the ontology/action model is uncertain.
Use the model and discriminating experiments until a predictive controller exists.
Then switch aggressively to verified/compiled execution; if prediction breaks, return to fluid mode.
The switching criterion is predictive confidence, not merely the existence of a legal action.
""",
}


def _mode() -> str:
    value = os.environ.get("FLASH_ARCH_MODE", "baseline").strip().lower()
    if value not in _MODES:
        raise ValueError(f"FLASH_ARCH_MODE must be one of {sorted(_MODES)}, got {value!r}")
    return value


def _normalize_actions(valid_actions: list[str] | None) -> list[str]:
    out: list[str] = []
    for raw in valid_actions or []:
        name = to_model_action(to_engine_action(str(raw)) or str(raw))
        if name and name not in out:
            out.append(name)
    return out


class ArchitectureTournamentAgent(AutonomousFlashToolAgent):
    """Small separators for ten candidate front-end architectures.

    This module is deliberately an experiment harness, not a production merge.
    Every arm keeps the same Metatron/Flash back-end and changes only how a novel
    residual is approached before the first reusable capability exists.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._arch_mode = _mode()
        self._arch_turn = 0
        self._arch_probe_count = 0
        self._arch_force_semantic = False
        self._arch_last_residual = ""

    def _ensure_session(self, state_path: Path) -> None:
        previous = self._session_runtime_dir
        super()._ensure_session(state_path)
        if previous != self._session_runtime_dir:
            self._arch_turn = 0
            self._arch_probe_count = 0
            self._arch_force_semantic = False
            self._arch_last_residual = ""
            self._dt_append("ARCH_MODE", {"mode": self._arch_mode})

    def _build_user_prompt(
        self,
        action_num: int,
        *,
        valid_actions: list[str] | None,
        current_frame: Frame | None = None,
        history_entries=None,
        previous_step_summary=None,
    ) -> str:
        base = super()._build_user_prompt(
            action_num,
            valid_actions=valid_actions,
            current_frame=current_frame,
            history_entries=history_entries,
            previous_step_summary=previous_step_summary,
        )
        addon = _MODE_PROMPTS.get(self._arch_mode, "")
        if self._arch_last_residual:
            addon += f"\nCurrent routed residual: {self._arch_last_residual}\n"
        return base + ("\n\n" + addon.strip() if addon.strip() else "")

    def _semantic(
        self,
        state_path: Path,
        action_num: int,
        valid_actions: list[str] | None,
        step_env,
        transcript_path,
        analysis_step,
        transcript_updated,
        request_timeout_seconds,
        should_stop,
        *,
        reason: str,
    ) -> AnalyzerTurnResult | None:
        frame, _ = load_runtime_state(state_path)
        self._dt_append(
            "ARCH_SEMANTIC",
            {
                "mode": self._arch_mode,
                "turn": self._arch_turn,
                "level": int(frame.level) if frame is not None else None,
                "reason": reason,
            },
        )
        # Call Flash directly: retain verified capability execution but skip
        # AutonomousFlash's blind pre-model probe on this turn.
        return FlashToolAgent.analyze(
            self,
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

    def _single_probe(
        self,
        frame: Frame,
        valid_actions: list[str] | None,
        step_env,
        *,
        reason: str,
    ) -> AnalyzerTurnResult | None:
        key = self._probe_key(frame, valid_actions)
        if key is None:
            return None
        raw = step_env({"actions": [_action_dict(key)]})
        if not isinstance(raw, dict) or not raw.get("executed"):
            return None
        self._arch_probe_count += 1
        self._dt_append(
            "ARCH_PROBE",
            {
                "mode": self._arch_mode,
                "turn": self._arch_turn,
                "level": int(frame.level),
                "action": key,
                "reason": reason,
                "board_changed": bool(raw.get("board_changed")),
                "level_completed": bool(raw.get("level_completed")),
                "game_over": bool(raw.get("game_over")),
            },
        )

        if raw.get("level_completed") or raw.get("run_complete"):
            program = (key,)
            source_level = int(frame.level)
            self._stage_and_maybe_promote(program, source_level)
            self._dt_completed_programs.append(program)
            self._dt_append(
                "PROBE_COMPILE",
                {
                    "source_level": source_level,
                    "action": key,
                    "program_len": 1,
                    "qualified_after_probe": True,
                    "architecture_mode": self._arch_mode,
                },
            )
        elif raw.get("game_over"):
            self._arch_last_residual = "R9/R5: the probe violated a live soundness or applicability guard."
        elif raw.get("board_changed"):
            self._arch_last_residual = "R1/R6: transition observed but goal/model remains unresolved."
        else:
            self._arch_last_residual = "R4/R5: no observable gameplay effect; observability or applicability is unresolved."

        return AnalyzerTurnResult(
            step_executed=True,
            reasoning=f"{self._arch_mode}: executed one discriminating probe.",
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
        self._arch_turn += 1
        frame, _ = load_runtime_state(state_path)

        # Baseline = current pruned architecture exactly.
        if self._arch_mode == "baseline":
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

        # Never suppress a genuinely qualified capability.
        active = self._active_flash_capability(frame)
        if active is not None:
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

        if frame is None or step_env is None:
            return self._semantic(
                state_path, action_num, valid_actions, step_env, transcript_path,
                analysis_step, transcript_updated, request_timeout_seconds, should_stop,
                reason="no structured frame available",
            )

        if self._arch_mode == "system_id":
            # Two semantic observe/model turns, then one clean experiment, repeat.
            if self._arch_turn <= 2 or self._arch_turn % 3 != 0:
                return self._semantic(
                    state_path, action_num, valid_actions, step_env, transcript_path,
                    analysis_step, transcript_updated, request_timeout_seconds, should_stop,
                    reason="identify controllables, transition law, and goal before cheap execution",
                )
            probe = self._single_probe(frame, valid_actions, step_env, reason="system-identification separator")
            return probe or self._semantic(
                state_path, action_num, valid_actions, step_env, transcript_path,
                analysis_step, transcript_updated, request_timeout_seconds, should_stop,
                reason="no legal identification probe",
            )

        if self._arch_mode == "representation_lattice":
            # Keep semantic reasoning hot; insert a single physical separator
            # after each semantic turn rather than repeating one action.
            if self._arch_turn % 2 == 1:
                return self._semantic(
                    state_path, action_num, valid_actions, step_env, transcript_path,
                    analysis_step, transcript_updated, request_timeout_seconds, should_stop,
                    reason="compare multiple live representations",
                )
            probe = self._single_probe(frame, valid_actions, step_env, reason="representation separator")
            return probe or self._semantic(
                state_path, action_num, valid_actions, step_env, transcript_path,
                analysis_step, transcript_updated, request_timeout_seconds, should_stop,
                reason="representation lattice has no cheap physical separator",
            )

        if self._arch_mode == "version_space":
            if self._arch_turn == 1 or self._arch_force_semantic:
                self._arch_force_semantic = False
                return self._semantic(
                    state_path, action_num, valid_actions, step_env, transcript_path,
                    analysis_step, transcript_updated, request_timeout_seconds, should_stop,
                    reason="construct/prune explicit rival hypotheses",
                )
            probe = self._single_probe(frame, valid_actions, step_env, reason="version-space disagreement test")
            self._arch_force_semantic = True
            return probe or self._semantic(
                state_path, action_num, valid_actions, step_env, transcript_path,
                analysis_step, transcript_updated, request_timeout_seconds, should_stop,
                reason="no version-space separator available",
            )

        if self._arch_mode == "model_early":
            if self._arch_turn <= 3:
                return self._semantic(
                    state_path, action_num, valid_actions, step_env, transcript_path,
                    analysis_step, transcript_updated, request_timeout_seconds, should_stop,
                    reason="front-load semantic cognition while ontology is open",
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

        if self._arch_mode == "info_gain":
            if self._arch_probe_count < 3:
                probe = self._single_probe(frame, valid_actions, step_env, reason="bounded information-gain probe")
                if probe is not None:
                    return probe
            return self._semantic(
                state_path, action_num, valid_actions, step_env, transcript_path,
                analysis_step, transcript_updated, request_timeout_seconds, should_stop,
                reason="interpret bounded probe evidence and choose next information-bearing experiment",
            )

        if self._arch_mode == "world_model":
            return self._semantic(
                state_path, action_num, valid_actions, step_env, transcript_path,
                analysis_step, transcript_updated, request_timeout_seconds, should_stop,
                reason="maintain predictive transition model and plan until capability exists",
            )

        if self._arch_mode == "hierarchical":
            return self._semantic(
                state_path, action_num, valid_actions, step_env, transcript_path,
                analysis_step, transcript_updated, request_timeout_seconds, should_stop,
                reason="discover a guarded option/skill rather than a raw repeated primitive",
            )

        if self._arch_mode == "residual_router":
            if self._arch_turn == 1 or self._arch_force_semantic:
                self._arch_force_semantic = False
                return self._semantic(
                    state_path, action_num, valid_actions, step_env, transcript_path,
                    analysis_step, transcript_updated, request_timeout_seconds, should_stop,
                    reason="route the current residual to the appropriate reasoning operation",
                )
            probe = self._single_probe(frame, valid_actions, step_env, reason="residual diagnosis probe")
            self._arch_force_semantic = True
            return probe or self._semantic(
                state_path, action_num, valid_actions, step_env, transcript_path,
                analysis_step, transcript_updated, request_timeout_seconds, should_stop,
                reason="residual router found no cheap probe",
            )

        if self._arch_mode == "join_triggered":
            if self._arch_probe_count < 2:
                probe = self._single_probe(frame, valid_actions, step_env, reason="collect distinct causal evidence before JOIN")
                if probe is not None:
                    return probe
            return self._semantic(
                state_path, action_num, valid_actions, step_env, transcript_path,
                analysis_step, transcript_updated, request_timeout_seconds, should_stop,
                reason="two probes accumulated; trigger semantic JOIN/representation repair",
            )

        if self._arch_mode == "dual_speed":
            # Fluid until the verifier has something reusable; compiled after.
            return self._semantic(
                state_path, action_num, valid_actions, step_env, transcript_path,
                analysis_step, transcript_updated, request_timeout_seconds, should_stop,
                reason="fluid mode until predictive capability is earned",
            )

        raise AssertionError(self._arch_mode)
'''


def patch(root: Path) -> None:
    root = root.resolve()
    agent_dir = root / "inference" / "agent"
    solver = root / "inference" / "framework" / "solver.py"
    if not (agent_dir / "flash_autonomous.py").is_file():
        raise SystemExit("apply flash_autonomous_patch.py first")

    target = agent_dir / "flash_architecture_tournament.py"
    target.write_text(MODULE, encoding="utf-8")

    text = solver.read_text(encoding="utf-8")
    old_import = "from inference.agent.flash_autonomous import AutonomousFlashToolAgent\n"
    new_import = "from inference.agent.flash_architecture_tournament import ArchitectureTournamentAgent\n"
    if old_import not in text and new_import not in text:
        raise SystemExit("Autonomous Flash solver import anchor changed")
    text = text.replace(old_import, new_import, 1)

    old_ctor = "        return AutonomousFlashToolAgent(\n"
    new_ctor = "        return ArchitectureTournamentAgent(\n"
    if old_ctor not in text and new_ctor not in text:
        raise SystemExit("Autonomous Flash constructor anchor changed")
    text = text.replace(old_ctor, new_ctor, 1)
    solver.write_text(text, encoding="utf-8")

    compile(target.read_text(), str(target), "exec")
    compile(solver.read_text(), str(solver), "exec")
    print("FLASH_ARCHITECTURE_TOURNAMENT_PATCH=PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    patch(args.root)


if __name__ == "__main__":
    main()

from __future__ import annotations

from typing import Any

from .memory_graph import ActionKey, ArcMemoryGraph, ContextKey
from .runtime import ActionToken, Observation, OnlineController, normalize_frame


class MemoryGraphController(OnlineController):
    """Online controller whose retained developmental present is ARC .mg.

    The base controller still owns action grounding, exact archived capability
    replay, progress retention, and bounded option reuse. This layer owns facts
    that must survive RESET: purchased interventions, observed legal branching,
    and exact terminally refuted programs.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.memory = ArcMemoryGraph()
        self._episode_context: ContextKey | None = None
        self._episode_program: list[ActionKey] = []
        super().__init__(*args, **kwargs)

    @staticmethod
    def _action_key(token: ActionToken) -> ActionKey:
        return (token.action_id, token.x, token.y)

    @staticmethod
    def _memory_context(obs: Observation) -> ContextKey:
        # Exact public state guard: a failure in one visual/task state must not
        # silently ban the same action sequence in a different state.
        return (
            obs.levels_completed,
            obs.state,
            obs.available_actions,
            obs.height,
            obs.width,
            obs.frame_digest,
        )

    def reset_episode(self) -> None:
        # Intentionally does NOT clear self.memory.
        super().reset_episode()
        self._episode_context = None
        self._episode_program = []

    def _process_previous_outcome(self, obs: Observation) -> None:
        previous_level = self._previous.levels_completed if self._previous is not None else None
        super()._process_previous_outcome(obs)
        if previous_level is not None and obs.levels_completed > previous_level:
            # Everything before this boundary earned progress, so a later loss
            # must only refute the new level suffix.
            self._episode_context = self._memory_context(obs)
            self._episode_program = []

    def record_terminal_failure(self, consequence: str = "GAME_OVER") -> None:
        if self._episode_context is None or not self._episode_program:
            return
        self.memory.add_refuted(
            self._episode_context,
            tuple(self._episode_program),
            consequence=consequence,
        )

    def observe_and_choose(self, frame: Any) -> ActionToken | None:
        obs = normalize_frame(frame)
        if self._episode_context is None:
            self._episode_context = self._memory_context(obs)

        token = super().observe_and_choose(frame)
        if token is None:
            return None

        # Archived/retained operations remain governed by their own evidence
        # gates. MemoryGraph filters only developmental exploration.
        if token.source == "explore":
            prefix = tuple(self._episode_program)
            catalog = self._action_catalog(obs)
            legal_keys = tuple(self._action_key(candidate) for candidate in catalog)
            self.memory.note_legal(self._episode_context, prefix, legal_keys)
            forbidden = self.memory.forbidden_next(self._episode_context, prefix)
            selected_key = self._action_key(token)
            allowed = [
                candidate
                for candidate in catalog
                if self._action_key(candidate) not in forbidden
            ]

            if selected_key in forbidden and allowed:
                guard = self._exploration_guard(obs)
                token = min(
                    allowed,
                    key=lambda candidate: (
                        self.memory.attempt_count(guard, self._action_key(candidate)),
                        self._candidate_key(candidate),
                    ),
                )
                selected_key = self._action_key(token)
                self._last_action = token

            guard = self._exploration_guard(obs)
            self.memory.note_attempt(guard, selected_key)

        self._episode_program.append(self._action_key(token))
        return token

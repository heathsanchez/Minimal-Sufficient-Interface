from __future__ import annotations

from typing import Any

from .memory_graph import ActionKey, ArcMemoryGraph, ContextKey, ProgramKey
from .runtime import ActionToken, Observation, OnlineController, normalize_frame


class MemoryGraphController(OnlineController):
    """Online controller whose retained developmental present is ARC .mg.

    Exact-context retention remains the authority for replaying a capability in
    the state where it was witnessed.  MG-ARC4 additionally exposes witnessed
    progress programs as *prospective constructors* at later levels.  Those
    constructors are hypotheses only: exact refutation evidence may override a
    transfer action at the first closed child, and no target-context success is
    installed without an observed level increment. Target-scoped issued-action
    caps persist across RESET and memory restart; exhaustion is unconfirmed, not
    semantic refutation.
    """

    def __init__(
        self,
        *args: Any,
        max_transfer_depth: int = 32,
        **kwargs: Any,
    ) -> None:
        if max_transfer_depth < 1:
            raise ValueError("max_transfer_depth must be positive")
        self.max_transfer_depth = int(max_transfer_depth)
        self.memory = ArcMemoryGraph()
        self._episode_context: ContextKey | None = None
        self._episode_program: list[ActionKey] = []
        super().__init__(*args, **kwargs)

    @staticmethod
    def _action_key(token: ActionToken) -> ActionKey:
        return (token.action_id, token.x, token.y)

    @staticmethod
    def _memory_context(obs: Observation) -> ContextKey:
        return (
            obs.levels_completed,
            obs.state,
            obs.available_actions,
            obs.height,
            obs.width,
            obs.frame_digest,
        )

    @staticmethod
    def _token(program_action: ActionKey, source: str) -> ActionToken:
        action_id, x, y = program_action
        return ActionToken(action_id, x, y, source)

    def _clear_transfer(self) -> None:
        self._active_transfer: ProgramKey = ()
        self._transfer_index = 0
        self._transfer_base: ProgramKey = ()
        self._transfer_level: int | None = None

    def reset_episode(self) -> None:
        # Intentionally does NOT clear self.memory.
        super().reset_episode()
        self._episode_context = None
        self._episode_program = []
        self._clear_transfer()

    def _process_previous_outcome(self, obs: Observation) -> None:
        previous_level = self._previous.levels_completed if self._previous is not None else None
        progressed = previous_level is not None and obs.levels_completed > previous_level
        source_context = self._episode_context
        witnessed_program = tuple(self._episode_program) if progressed else ()

        super()._process_previous_outcome(obs)

        if progressed:
            if self._transfer_base and self._transfer_level is not None:
                self.memory.finish_transfer(
                    self._transfer_level, self._transfer_base, "WITNESSED_PROGRESS")
            if source_context is not None and witnessed_program:
                self.memory.add_capability(
                    source_context,
                    witnessed_program,
                    source_level=int(previous_level),
                    target_level=int(obs.levels_completed),
                )
            # Everything before this boundary earned progress, so future
            # failure evidence belongs only to the new level suffix.
            self._episode_context = self._memory_context(obs)
            self._episode_program = []
            self._clear_transfer()

    def record_terminal_failure(self, consequence: str = "GAME_OVER") -> None:
        if self._episode_context is None or not self._episode_program:
            return
        self.memory.add_refuted(
            self._episode_context,
            tuple(self._episode_program),
            consequence=consequence,
        )

    def _start_transfer(self, obs: Observation) -> None:
        if self._active_transfer:
            return
        programs = self.memory.capability_programs(for_level=obs.levels_completed)
        if not programs:
            return

        # The freshest witnessed program is the first hypothesis.  Repetition
        # is a generic constructor from the frozen multilevel ARC lineage.  It
        # is bounded by primitive length and remains interruptible by external
        # progress, terminal consequence, illegality, or exact trie closure.
        base = next((program for program in programs
                     if self.memory.transfer_remaining(
                         obs.levels_completed, program, self.max_transfer_depth)), ())
        if not base:
            return
        repeats = max(1, self.max_transfer_depth // len(base))
        expanded = base * repeats
        remaining = self.memory.transfer_remaining(
            obs.levels_completed, base, self.max_transfer_depth)
        self._active_transfer = expanded[:remaining]
        self._transfer_base = base
        self._transfer_level = obs.levels_completed
        self._transfer_index = 0

    def _next_transfer(self, obs: Observation) -> ActionToken | None:
        self._start_transfer(obs)
        if not self._active_transfer or self._transfer_index >= len(self._active_transfer):
            if self._transfer_base and self._transfer_level is not None:
                self.memory.finish_transfer(self._transfer_level, self._transfer_base)
            self._clear_transfer()
            return None
        action = self._active_transfer[self._transfer_index]
        if action[0] not in self._legal_ids(obs):
            self._clear_transfer()
            return None
        if not self.memory.issue_transfer(
                obs.levels_completed, self._transfer_base, self.max_transfer_depth):
            self.memory.finish_transfer(obs.levels_completed, self._transfer_base)
            self._clear_transfer()
            return None
        self._transfer_index += 1
        return self._token(action, "transfer")

    def _next_retained(self, obs: Observation) -> ActionToken | None:
        # Exact replay always outranks speculative cross-level transfer.
        retained = super()._next_retained(obs)
        if retained is not None:
            return retained
        return self._next_transfer(obs)

    def observe_and_choose(self, frame: Any) -> ActionToken | None:
        obs = normalize_frame(frame)
        if self._episode_context is None:
            self._episode_context = self._memory_context(obs)

        token = super().observe_and_choose(frame)
        if token is None:
            return None

        # Archived and exact retained operations keep their own evidence gates.
        # Both primitive exploration and prospective transfer are target-context
        # hypotheses and therefore pass through the exact refutation trie.
        if token.source in ("explore", "transfer"):
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
                # Once exact consequence evidence forces a sibling, the
                # speculative macro no longer describes the live path.
                self._clear_transfer()

            guard = self._exploration_guard(obs)
            self.memory.note_attempt(guard, selected_key)

        self._episode_program.append(self._action_key(token))
        return token

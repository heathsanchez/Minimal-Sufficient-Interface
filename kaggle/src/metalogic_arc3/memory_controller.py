from __future__ import annotations

from typing import Any

from .memory_graph import ActionKey, ArcMemoryGraph, ContextKey, ProgramKey
from .runtime import ActionToken, Observation, OnlineController, normalize_frame


class MemoryGraphController(OnlineController):
    """DuckTape controller: all retained developmental state comes from the log.

    The inherited controller supplies public observation normalization, archived
    evidence gates and bounded action catalogues. Cross-episode attempts,
    refutations and learned progress programs are authoritative only when they
    are derivable from self.memory. The inherited mutable visit/retained stores
    are cleared at every reset and never used for retained replay.
    """

    def __init__(
        self,
        *args: Any,
        max_transfer_depth: int = 32,
        preserve_memory: bool = True,
        **kwargs: Any,
    ) -> None:
        if max_transfer_depth < 1:
            raise ValueError("max_transfer_depth must be positive")
        self.max_transfer_depth = int(max_transfer_depth)
        self.preserve_memory = bool(preserve_memory)
        self.memory = ArcMemoryGraph()
        self._episode_context: ContextKey | None = None
        self._episode_program: list[ActionKey] = []
        self._exact_replay: ProgramKey = ()
        self._exact_replay_index = 0
        self._active_transfer: ProgramKey = ()
        self._transfer_index = 0
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

    def _clear_exact(self) -> None:
        self._exact_replay = ()
        self._exact_replay_index = 0

    def _clear_transfer(self) -> None:
        self._active_transfer = ()
        self._transfer_index = 0

    def reset_episode(self) -> None:
        if not self.preserve_memory:
            self.memory = ArcMemoryGraph()

        super().reset_episode()

        # The inherited stores are deliberately not developmental authority in
        # DuckTape. Clearing them makes that falsifiable rather than rhetorical.
        self._retained = {}
        self._visits = {}

        self._episode_context = None
        self._episode_program = []
        self._clear_exact()
        self._clear_transfer()

    def _process_previous_outcome(self, obs: Observation) -> None:
        previous_level = self._previous.levels_completed if self._previous is not None else None
        progressed = previous_level is not None and obs.levels_completed > previous_level
        source_context = self._episode_context
        witnessed_program = tuple(self._episode_program) if progressed else ()

        super()._process_previous_outcome(obs)

        if progressed:
            if source_context is not None and witnessed_program:
                self.memory.add_capability(
                    source_context,
                    witnessed_program,
                    source_level=int(previous_level),
                    target_level=int(obs.levels_completed),
                )
            self._episode_context = self._memory_context(obs)
            self._episode_program = []
            self._clear_exact()
            self._clear_transfer()

    def record_terminal_failure(self, consequence: str = "GAME_OVER") -> None:
        if self._episode_context is None or not self._episode_program:
            return
        self.memory.add_refuted(
            self._episode_context,
            tuple(self._episode_program),
            consequence=consequence,
        )

    def _next_exact(self, obs: Observation) -> ActionToken | None:
        if self._exact_replay and self._exact_replay_index < len(self._exact_replay):
            action = self._exact_replay[self._exact_replay_index]
            if action[0] not in self._legal_ids(obs):
                self._clear_exact()
                return None
            self._exact_replay_index += 1
            return self._token(action, "retained")

        self._clear_exact()
        programs = self.memory.capability_programs_for_source(self._memory_context(obs))
        if not programs:
            return None
        self._exact_replay = programs[0]
        if not self._exact_replay:
            return None
        action = self._exact_replay[0]
        if action[0] not in self._legal_ids(obs):
            self._clear_exact()
            return None
        self._exact_replay_index = 1
        return self._token(action, "retained")

    def _start_transfer(self, obs: Observation) -> None:
        if self._active_transfer:
            return
        programs = self.memory.capability_programs(for_level=obs.levels_completed)
        if not programs:
            return

        base = programs[0]
        if not base:
            return
        repeats = max(1, self.max_transfer_depth // len(base))
        expanded = base * repeats
        self._active_transfer = expanded[: self.max_transfer_depth]
        self._transfer_index = 0

    def _next_transfer(self, obs: Observation) -> ActionToken | None:
        self._start_transfer(obs)
        if not self._active_transfer or self._transfer_index >= len(self._active_transfer):
            self._clear_transfer()
            return None
        action = self._active_transfer[self._transfer_index]
        if action[0] not in self._legal_ids(obs):
            self._clear_transfer()
            return None
        self._transfer_index += 1
        return self._token(action, "transfer")

    def _next_retained(self, obs: Observation) -> ActionToken | None:
        exact = self._next_exact(obs)
        if exact is not None:
            return exact
        return self._next_transfer(obs)

    def observe_and_choose(self, frame: Any) -> ActionToken | None:
        obs = normalize_frame(frame)
        if self._episode_context is None:
            self._episode_context = self._memory_context(obs)

        token = super().observe_and_choose(frame)
        if token is None:
            return None

        if token.source in ("explore", "transfer"):
            prefix = tuple(self._episode_program)
            catalog = self._action_catalog(obs)
            legal_keys = tuple(self._action_key(candidate) for candidate in catalog)
            self.memory.note_legal(self._episode_context, prefix, legal_keys)
            forbidden = self.memory.forbidden_next(self._episode_context, prefix)
            allowed = [
                candidate
                for candidate in catalog
                if self._action_key(candidate) not in forbidden
            ]
            guard = self._exploration_guard(obs)

            if token.source == "explore" and catalog:
                # Keep the successful two-stage search geometry, but encode
                # both stages in the single immutable DuckTape log:
                #
                #   proposal pressure -> exact consequence override -> actual attempt.
                #
                # The first signal controls broad exploration. The second says
                # which sibling has really been paid for when a known-dead
                # branch is skipped.
                proposal = min(
                    catalog,
                    key=lambda candidate: (
                        self.memory.proposal_count(guard, self._action_key(candidate)),
                        self._candidate_key(candidate),
                    ),
                )
                self.memory.note_proposal(guard, self._action_key(proposal))
                token = proposal
                if self._action_key(proposal) in forbidden and allowed:
                    token = min(
                        allowed,
                        key=lambda candidate: (
                            self.memory.attempt_count(guard, self._action_key(candidate)),
                            self._candidate_key(candidate),
                        ),
                    )
                self._last_action = token
            elif self._action_key(token) in forbidden and allowed:
                token = min(
                    allowed,
                    key=lambda candidate: (
                        self.memory.attempt_count(guard, self._action_key(candidate)),
                        self._candidate_key(candidate),
                    ),
                )
                self._last_action = token
                self._clear_transfer()

            self.memory.note_attempt(guard, self._action_key(token))

        self._episode_program.append(self._action_key(token))
        return token

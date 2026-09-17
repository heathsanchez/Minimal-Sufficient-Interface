from __future__ import annotations

import hashlib
from math import gcd
from typing import Any

from .certified_memory import CertifiedArcMemoryGraph, Checkpoint
from .consequence_controller import ConsequenceController, effect_signature, settled_grid
from .memory_graph import ActionKey, ProgramKey
from .runtime import ActionToken, Observation, normalize_frame


class CertifiedConsequenceController(ConsequenceController):
    """Consequence controller with finite source-contract requalification.

    A witnessed source program does not automatically authorize full reuse at a
    new target. Initial target actions are `transfer_probe` actions. Their
    observed *process* effects must match stored source checkpoints before the
    remainder of the macro can use ordinary `transfer`. The observation that
    crosses a level boundary is kept separate as protected endpoint outcome,
    not misclassified as an intermediate process checkpoint.
    """

    def __init__(self, *args: Any, requalification_prefix: int = 8, **kwargs: Any) -> None:
        if requalification_prefix < 1:
            raise ValueError("requalification_prefix must be positive")
        self.requalification_prefix = int(requalification_prefix)
        super().__init__(*args, **kwargs)
        self.memory = CertifiedArcMemoryGraph()
        self._episode_certificate: list[Checkpoint] = []
        self._active_contract: dict[str, Any] | None = None
        self._pending_probe_expected: Checkpoint | None = None

    @staticmethod
    def _structural_signature(before: Any, after: Any, action: ActionKey) -> tuple[int, int, int, int, int, int]:
        if len(before) == len(after) and (not before or not after or len(before[0]) == len(after[0])):
            signature = effect_signature(before, after, action)
            return tuple(int(value) for value in signature.structural())
        changed = max(sum(len(row) for row in before), sum(len(row) for row in after))
        return (int(changed), 0, 0, 0, 0, 0)

    @staticmethod
    def _structural_class(
        signature: tuple[int, int, int, int, int, int]
    ) -> tuple[int, ...]:
        """Quotient pixel scale while preserving effect topology.

        Absolute changed-cell counts and bounding-box dimensions are rendering-
        scale dependent. The retained invariants are changed-area density,
        bounding-box aspect ratio, intervention-relative direction and component
        count. Degenerate/no-op signatures remain exact.
        """
        changed, bbox_w, bbox_h, dx_sign, dy_sign, components = (
            int(value) for value in signature
        )
        if changed <= 0 or bbox_w <= 0 or bbox_h <= 0:
            return (changed, bbox_w, bbox_h, dx_sign, dy_sign, components)
        area = bbox_w * bbox_h
        density_gcd = gcd(changed, area)
        aspect_gcd = gcd(bbox_w, bbox_h)
        return (
            changed // density_gcd,
            area // density_gcd,
            bbox_w // aspect_gcd,
            bbox_h // aspect_gcd,
            dx_sign,
            dy_sign,
            components,
        )

    @classmethod
    def _checkpoint_matches(cls, observed: Checkpoint, expected: Checkpoint) -> bool:
        return (
            tuple(observed[1]) == tuple(expected[1])
            and str(observed[2]) == str(expected[2])
            and cls._structural_class(observed[3])
            == cls._structural_class(expected[3])
        )

    def _clear_transfer(self) -> None:
        super()._clear_transfer()
        self._active_contract = None
        self._pending_probe_expected = None

    def reset_episode(self) -> None:
        memory = getattr(self, "memory", None)
        base = getattr(self, "_transfer_base", ())
        level = getattr(self, "_transfer_level", None)
        if isinstance(memory, CertifiedArcMemoryGraph) and base and level is not None:
            trial = memory.transfer_trial(level, base)
            if trial is not None and trial["status"] == "OPEN_PROBE":
                memory.finish_transfer(level, base, "EXPIRED_UNCONFIRMED")
        super().reset_episode()
        self._episode_certificate = []
        self._active_contract = None
        self._pending_probe_expected = None

    def _record_effect(self, frame: Any, obs: Observation) -> None:
        pending = getattr(self, "_pending_effect", None)
        source = getattr(getattr(self, "_last_action", None), "source", None)
        grid = settled_grid(frame)
        checkpoint: Checkpoint | None = None
        if pending is not None:
            _context, action, before, descriptor, _history = pending
            structural = self._structural_signature(before, grid, action)
            checkpoint = (
                len(self._episode_certificate),
                tuple(action),
                str(descriptor),
                structural,
            )

        super()._record_effect(frame, obs)

        if checkpoint is not None:
            self._episode_certificate.append(checkpoint)
            if source == "transfer_probe" and self._pending_probe_expected is not None:
                expected = self._pending_probe_expected
                self._pending_probe_expected = None
                matches = self._checkpoint_matches(checkpoint, expected)
                if self._transfer_base and self._transfer_level is not None:
                    if matches:
                        contract = self._active_contract
                        if contract is None:
                            raise RuntimeError("probe has no active source contract")
                        count = min(
                            self.requalification_prefix,
                            len(contract["checkpoints"]),
                            len(contract["program"]),
                        )
                        self.memory.mark_probe_match(
                            self._transfer_level,
                            self._transfer_base,
                            contract_digest=contract["digest"],
                            checkpoint_count=count,
                        )
                    else:
                        self.memory.mark_contract_mismatch(
                            self._transfer_level,
                            self._transfer_base,
                        )
                        self._clear_transfer()

    def _process_previous_outcome(self, obs: Observation) -> None:
        previous_level = self._previous.levels_completed if self._previous is not None else None
        progressed = previous_level is not None and obs.levels_completed > previous_level
        source_context = self._episode_context
        witnessed_program = tuple(self._episode_program) if progressed else ()
        witnessed = tuple(self._episode_certificate) if progressed else ()

        super()._process_previous_outcome(obs)

        if progressed and source_context is not None and witnessed_program and witnessed:
            # The last observed transition is exactly the action whose successor
            # observation establishes LEVEL_INCREMENT. Its raster may be a new
            # level/camera/state representation, so it is endpoint evidence, not
            # an intermediate process effect that a longer target must reproduce.
            process_witness = witnessed[:-1]
            if process_witness:
                limit = min(
                    self.requalification_prefix,
                    len(witnessed_program) - 1,
                    len(process_witness),
                )
                checkpoints = tuple(
                    (index, process_witness[index][1], process_witness[index][2], process_witness[index][3])
                    for index in range(limit)
                )
                if checkpoints:
                    self.memory.add_capability_contract(
                        source_context,
                        witnessed_program,
                        source_level=int(previous_level),
                        target_level=int(obs.levels_completed),
                        checkpoints=checkpoints,
                    )
            self._episode_certificate = []

    def _start_transfer(self, obs: Observation) -> None:
        if self._active_transfer:
            return
        candidates = self.memory.certified_capability_candidates(obs.levels_completed)
        candidate = next(
            (
                row for row in candidates
                if self.memory.transfer_remaining(
                    obs.levels_completed,
                    row["program"],
                    self.max_transfer_depth,
                )
            ),
            None,
        )
        if candidate is None:
            return
        base: ProgramKey = candidate["program"]
        remaining = self.memory.transfer_remaining(
            obs.levels_completed,
            base,
            self.max_transfer_depth,
        )
        repeats = max(1, self.max_transfer_depth // len(base))
        self._active_transfer = (base * repeats)[:remaining]
        self._transfer_base = base
        self._transfer_level = obs.levels_completed
        self._transfer_index = 0
        self._active_contract = candidate
        self._pending_probe_expected = None

    def _next_transfer(self, obs: Observation) -> ActionToken | None:
        self._start_transfer(obs)
        if not self._active_transfer or self._transfer_index >= len(self._active_transfer):
            if self._transfer_base and self._transfer_level is not None:
                self.memory.finish_transfer(
                    self._transfer_level,
                    self._transfer_base,
                    "EXPIRED_UNCONFIRMED",
                )
            self._clear_transfer()
            return None

        action = self._active_transfer[self._transfer_index]
        if action[0] not in self._legal_ids(obs):
            if self._transfer_base and self._transfer_level is not None:
                self.memory.mark_contract_mismatch(self._transfer_level, self._transfer_base)
            self._clear_transfer()
            return None

        if not self.memory.issue_transfer(
            obs.levels_completed,
            self._transfer_base,
            self.max_transfer_depth,
        ):
            if self._transfer_base and self._transfer_level is not None:
                self.memory.finish_transfer(
                    self._transfer_level,
                    self._transfer_base,
                    "EXPIRED_UNCONFIRMED",
                )
            self._clear_transfer()
            return None

        trial = self.memory.transfer_trial(obs.levels_completed, self._transfer_base)
        if trial is None:
            raise RuntimeError("issued transfer action has no target trial")

        source = "transfer"
        if trial["status"] == "OPEN_PROBE":
            contract = self._active_contract
            if contract is None:
                raise RuntimeError("open probe has no source contract")
            matched = int(trial["matched"])
            count = min(
                self.requalification_prefix,
                len(contract["checkpoints"]),
                len(contract["program"]),
            )
            if matched >= count:
                raise RuntimeError("probe status did not advance after all checkpoints")
            expected: Checkpoint = contract["checkpoints"][matched]
            if action != expected[1]:
                self.memory.mark_contract_mismatch(obs.levels_completed, self._transfer_base)
                self._clear_transfer()
                return None
            self._pending_probe_expected = expected
            source = "transfer_probe"
        elif trial["status"] != "PREFIX_REQUALIFIED":
            self._clear_transfer()
            return None

        self._transfer_index += 1
        return self._token(action, source)

    def observe_and_choose(self, frame: Any) -> ActionToken | None:
        obs = normalize_frame(frame)
        self._record_effect(frame, obs)
        previous_level = self._previous.levels_completed if self._previous is not None else None
        self._process_previous_outcome(obs)
        if previous_level is not None and obs.levels_completed > previous_level:
            self._repeat = None
            self._repeat_left = 0
        if self._episode_context is None:
            self._episode_context = self._memory_context(obs)
        if self._level_start_guard is None:
            self._level_start_guard = self._retention_guard(obs)
        if obs.state == "WIN":
            self._previous = obs
            self._last_action = None
            return None

        token = self._next_archive(obs)
        if token is None:
            token = self._next_continuation(obs)
        if token is None:
            token = self._next_retained(obs)
        self._decision_tick += 1

        if token is None or token.source in ("transfer", "transfer_probe"):
            catalog = self._catalog(obs)
            prefix = tuple(self._episode_program)
            self.memory.note_legal(
                self._episode_context,
                prefix,
                tuple(self._action_key(candidate) for candidate in catalog),
            )
            forbidden = self.memory.forbidden_next(self._episode_context, prefix)
            allowed = tuple(
                candidate
                for candidate in catalog
                if self._action_key(candidate) not in forbidden
            )
            candidates = allowed or catalog
            if token is None or self._action_key(token) in forbidden:
                self._clear_transfer()
                token = self._select_probe(obs, candidates)
            key = self._action_key(token)
            guard = self._exploration_guard(obs)
            self._visits[(guard, key)] = self._visits.get((guard, key), 0) + 1
            self.memory.note_attempt(self._memory_context(obs), key)

        key = self._action_key(token)
        history = hashlib.sha256(repr(tuple(self._episode_program[-8:])).encode()).hexdigest()
        self._pending_effect = (
            obs.evidence_sha256,
            key,
            self._grid,
            self._descriptor(token),
            history,
        )
        self._episode_program.append(key)
        self._previous = obs
        self._last_action = token
        return token

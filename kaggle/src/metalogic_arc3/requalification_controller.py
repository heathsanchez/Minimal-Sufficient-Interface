from __future__ import annotations

from typing import Any

from .certified_memory import CertifiedArcMemoryGraph, Checkpoint
from .consequence_controller import ConsequenceController, effect_signature, settled_grid
from .memory_graph import ActionKey, ProgramKey
from .runtime import ActionToken, Observation, normalize_frame


class CertifiedConsequenceController(ConsequenceController):
    """Consequence controller with finite source-contract requalification.

    A witnessed source program does not automatically authorize full reuse at a
    new target. Initial target actions are `transfer_probe` actions. Their
    observed structural effects must match the stored source checkpoints before
    the remainder of the macro can use the ordinary `transfer` source.
    """

    def __init__(self, *args: Any, requalification_prefix: int = 8, **kwargs: Any) -> None:
        if requalification_prefix < 1:
            raise ValueError("requalification_prefix must be positive")
        self.requalification_prefix = int(requalification_prefix)
        super().__init__(*args, **kwargs)
        # Preserve all base behavior but upgrade the canonical retained memory.
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

    def _clear_transfer(self) -> None:
        super()._clear_transfer()
        self._active_contract = None
        self._pending_probe_expected = None

    def reset_episode(self) -> None:
        # A partial probe cannot be resumed across a reset because its earlier
        # checkpoints belonged to the pre-reset trajectory. Its spent allowance
        # remains charged and the source capability remains intact.
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
                actual = checkpoint
                self._pending_probe_expected = None
                matches = (
                    actual[1] == expected[1]
                    and actual[2] == expected[2]
                    and actual[3] == expected[3]
                )
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
            limit = min(self.requalification_prefix, len(witnessed_program), len(witnessed))
            checkpoints = []
            for index in range(limit):
                _old_index, action, descriptor, structural = witnessed[index]
                checkpoints.append((index, action, descriptor, structural))
            self.memory.add_capability_contract(
                source_context,
                witnessed_program,
                source_level=int(previous_level),
                target_level=int(obs.levels_completed),
                checkpoints=tuple(checkpoints),
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

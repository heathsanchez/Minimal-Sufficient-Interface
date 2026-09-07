"""Typed-residual developmental OS candidate.

This candidate leaves the verified baseline controller untouched and adds a
provenance-level gate for scope transport.  A local verified result may enter
the Lawbook, but it cannot be globally promoted or wake non-attachment work
until an explicit attachment certificate bridges local_scope -> target_scope.
"""
from __future__ import annotations
from dataclasses import dataclass
from developmental_operating_system import DevelopmentalOperatingSystem, Action
from typed_residual_protocol import ResidualEnvelope


@dataclass
class TypedRoutingState:
    envelope: ResidualEnvelope | None = None
    global_promotion_blocked: bool = False


class TypedDevelopmentalOperatingSystem(DevelopmentalOperatingSystem):
    """Candidate OS with a typed scope/attachment promotion boundary."""

    def __init__(self):
        super().__init__()
        self.typed = TypedRoutingState()

    def install_residual_envelope(self, state, envelope: ResidualEnvelope) -> None:
        self.typed.envelope = envelope
        state.residual = envelope.statement
        state.residual_type = envelope.kind()
        state.residual_type_scores = {'typed': 1}
        self.typed.global_promotion_blocked = not envelope.safe_for_global_promotion()
        state.provenance_graph.append({
            'id': 'residual-envelope:' + str(len(state.provenance_graph)),
            'kind': 'typed-residual',
            'parents': list(envelope.evidence_ids),
            'evidence': envelope.to_dict(),
        })

    def invariant_guard(self, state) -> None:
        # ATTACHMENT is a candidate residual kind not present in the frozen v1 enum.
        # Run all baseline invariants except the old enum membership assertion.
        from developmental_operating_system import CONSTITUTION
        missing = set(CONSTITUTION) - set(state.lock.constitution)
        if missing:
            raise RuntimeError(f'constitutional invariant missing: {sorted(missing)}')
        if not state.target or not state.lock.verifier:
            raise RuntimeError('target/verifier must be frozen')
        if any(v < 0 for v in state.lock.budget.values()):
            raise RuntimeError('negative locked budget')
        if any(v < -1e-9 for v in state.remaining_budget.values()):
            raise RuntimeError('budget overspend')
        allowed = {
            'SEARCH','REPRESENTATION','OBSERVABLE','OPERATOR','COMPOSITION',
            'SCOPE','VERIFIER','DERIVATION','INFRA','UNKNOWN','ATTACHMENT'
        }
        if state.residual_type not in allowed:
            raise RuntimeError('unknown residual type')
        if self.typed.envelope and self.typed.envelope.kind() == 'ATTACHMENT':
            if not self.typed.global_promotion_blocked:
                raise RuntimeError('attachment residual cannot be globally promotable')

    def wake_actions(self, state) -> None:
        super().wake_actions(state)
        if state.residual_type == 'ATTACHMENT':
            triggers = tuple(p['id'] for p in state.provenance_graph[-8:])
            # ATTACH is the only action licensed to change global scope while blocked.
            attach = Action(
                'act:attach','ATTACH',
                'Construct an externally checkable certificate mapping the verified local result into the live target frontier.',
                triggers,5.0,5.0,1.0,residual_types=('ATTACHMENT',)
            )
            state.action_queue = [a for a in state.action_queue if a.id == 'act:attach']
            if not state.action_queue:
                state.action_queue.append(attach)

    def can_promote_globally(self) -> bool:
        return not self.typed.global_promotion_blocked

    def promote_global(self, capability_id: str) -> str:
        if not self.can_promote_globally():
            raise RuntimeError(
                f'unsafe global promotion blocked for {capability_id}: attachment certificate missing'
            )
        return capability_id

    def attach(self, state, certified_envelope: ResidualEnvelope) -> None:
        if not certified_envelope.attachment_certificate:
            raise RuntimeError('ATTACH action requires an attachment certificate')
        self.install_residual_envelope(state, certified_envelope)
        self.typed.global_promotion_blocked = False

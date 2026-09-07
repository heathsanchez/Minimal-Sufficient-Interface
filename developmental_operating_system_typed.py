"""Typed-residual developmental OS — authenticated promotion transition.

A local verified result may enter the Lawbook, but it cannot be globally
promoted until the promotion transition is satisfied by evidence COMPUTED from
the frozen verifier and the actual retained state.  Caller-supplied Boolean
flags (``attachment_certificate``, ``verified_local_result``) are advisory and
are NEVER trusted as proof.

The four promotion obligations are distinct and each is computed, never supplied:

* ``passed``     -- the frozen verifier's verdict on the capability's claim.
* ``attached``   -- the capability's provenance references the motivating residual.
* ``scope_ok``   -- the promoted scope does not exceed the capability's authorized scope.
* ``preserves``  -- the prior capability is still retained in the installed set.

Compatibility change (explicit): ``promote_global`` and ``attach`` now take the
OS state and compute evidence from the frozen verifier + state, instead of
reading a Boolean flag off the envelope.  The old ``attach(state, envelope)``
Boolean bypass is removed; callers must supply the capability being attached
and it must be verified by the configured authority.
"""
from __future__ import annotations
from dataclasses import dataclass
from developmental_operating_system import (
    DevelopmentalOperatingSystem, Action, Capability,
)
from typed_residual_protocol import ResidualEnvelope, Verdict


@dataclass
class TypedRoutingState:
    envelope: ResidualEnvelope | None = None
    global_promotion_blocked: bool = False
    pre_transition_installed: tuple[str, ...] = ()


class TypedDevelopmentalOperatingSystem(DevelopmentalOperatingSystem):
    """Candidate OS with a typed scope/attachment promotion boundary."""

    def __init__(self, verifier=None):
        super().__init__()
        self.typed = TypedRoutingState()
        # Frozen authority: a callable (state, capability) -> bool giving the
        # external verdict on a capability's claim.  Configured once; the OS
        # invokes it, it never trusts a caller-supplied Boolean.
        self._verifier = verifier

    # -- residual envelope / routing (unchanged semantics) --------------------

    def install_residual_envelope(self, state, envelope: ResidualEnvelope) -> None:
        self.typed.envelope = envelope
        state.residual = envelope.statement
        state.residual_type = envelope.kind()
        state.residual_type_scores = {'typed': 1}
        self.typed.global_promotion_blocked = not envelope.safe_for_global_promotion()
        # Snapshot the retained capability set at residual-install time so that
        # preservation is checked against the ACTUAL prior state, not a caller
        # boolean.
        self.typed.pre_transition_installed = tuple(c.id for c in state.installed_capabilities)
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
            'SEARCH', 'REPRESENTATION', 'OBSERVABLE', 'OPERATOR', 'COMPOSITION',
            'SCOPE', 'VERIFIER', 'DERIVATION', 'INFRA', 'UNKNOWN', 'ATTACHMENT'
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
                'act:attach', 'ATTACH',
                'Construct an externally checkable certificate mapping the verified local result into the live target frontier.',
                triggers, 5.0, 5.0, 1.0, residual_types=('ATTACHMENT',)
            )
            state.action_queue = [a for a in state.action_queue if a.id == 'act:attach']
            if not state.action_queue:
                state.action_queue.append(attach)

    # -- authenticated promotion transition ----------------------------------

    def _capability(self, state, capability_id):
        return next((c for c in state.installed_capabilities if c.id == capability_id), None)

    def _residual_witness_ids(self, state):
        return {
            p['id'] for p in state.provenance_graph
            if p['kind'] in ('residual-envelope', 'typed-residual', 'residual')
        }

    def _compute_verdict(self, state, capability: Capability, promoted_scope: str) -> Verdict:
        """Compute all four obligations from the frozen verifier + actual state."""
        # 1. verdict: invoke the frozen authority (never a caller-supplied bool)
        passed = bool(self._verifier is not None and self._verifier(state, capability))
        # 2. attachment: provenance references the motivating residual witness
        attached = bool(self._residual_witness_ids(state) & set(capability.provenance))
        # 3. scope: promoted scope must equal the capability's authorized scope
        scope_ok = (promoted_scope == capability.scope)
        # 4. preservation: every capability retained at residual-install time is
        #    still present in the actual installed set.
        installed_ids = {c.id for c in state.installed_capabilities}
        preserves = all(pid in installed_ids for pid in self.typed.pre_transition_installed)
        return Verdict(passed=passed, attached=attached, scope_ok=scope_ok, preserves=preserves)

    def promote_global(self, state, capability_id: str, promoted_scope: str | None = None) -> str:
        """Promote a capability iff every obligation is met by computed evidence."""
        cap = self._capability(state, capability_id)
        if cap is None:
            raise RuntimeError(f'unknown capability {capability_id}')
        scope = promoted_scope if promoted_scope is not None else cap.scope
        verdict = self._compute_verdict(state, cap, scope)
        if not verdict.accepts():
            raise RuntimeError(
                f'promotion rejected for {capability_id}: passed={verdict.passed} '
                f'attached={verdict.attached} scope_ok={verdict.scope_ok} '
                f'preserves={verdict.preserves}'
            )
        self.typed.global_promotion_blocked = False
        return capability_id

    def attach(self, state, envelope: ResidualEnvelope, capability: Capability | None = None) -> None:
        """Attach a capability to the residual.  The envelope's Boolean
        ``attachment_certificate`` is NOT trusted: the capability must be verified
        by the frozen authority and its provenance must reference the residual."""
        if self._verifier is None:
            raise RuntimeError('ATTACH requires a frozen verifier (no authority configured)')
        if capability is None:
            raise RuntimeError('ATTACH requires the capability being attached')
        verdict = self._compute_verdict(state, capability, capability.scope)
        if not (verdict.passed and verdict.attached):
            raise RuntimeError(
                f'ATTACH rejected: passed={verdict.passed} attached={verdict.attached}'
            )
        if capability.id not in {c.id for c in state.installed_capabilities}:
            state.installed_capabilities.append(capability)
        self.install_residual_envelope(state, envelope)
        self.typed.global_promotion_blocked = False

    def can_promote_globally(self) -> bool:
        return not self.typed.global_promotion_blocked

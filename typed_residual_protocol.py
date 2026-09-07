"""Typed residual protocol for verified developmental routing.

Residual kind is compiled from verifier/provenance state, not inferred from prose.
Free text remains an explanation for humans and optional fallback only.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class ResidualEnvelope:
    statement: str
    stage: str
    local_scope: str
    target_scope: str
    verified_local_result: bool = False
    attachment_certificate: bool = False
    failed_gate: str | None = None
    evidence_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None

    def kind(self) -> str:
        # Attachment is a causal/provenance property: a verified result exists in
        # one scope, but no certified bridge transports it to the target scope.
        if (self.verified_local_result
                and self.local_scope != self.target_scope
                and not self.attachment_certificate):
            return 'ATTACHMENT'
        if self.failed_gate == 'attachment':
            return 'ATTACHMENT'
        gate_map = {
            'verification': 'VERIFIER', 'infrastructure': 'INFRA',
            'representation': 'REPRESENTATION', 'observable': 'OBSERVABLE',
            'operator': 'OPERATOR', 'composition': 'COMPOSITION', 'scope': 'SCOPE',
            'derivation': 'DERIVATION', 'search': 'SEARCH',
        }
        return gate_map.get(self.failed_gate or '', 'UNKNOWN')

    def safe_for_global_promotion(self) -> bool:
        return not (self.kind() == 'ATTACHMENT')

    def to_dict(self):
        d = asdict(self)
        d['kind'] = self.kind()
        d['safe_for_global_promotion'] = self.safe_for_global_promotion()
        return d


@dataclass(frozen=True)
class Verdict:
    """The four promotion obligations, each COMPUTED by the OS from the frozen
    verifier and the actual retained state.  None is caller-supplied.

    passed     -- the frozen verifier's verdict on the capability's claim.
    attached   -- the capability's provenance references the motivating residual.
    scope_ok   -- the promoted scope does not exceed the capability's authorized scope.
    preserves  -- the prior capability is still retained in the installed set.
    """
    passed: bool
    attached: bool
    scope_ok: bool
    preserves: bool

    def accepts(self) -> bool:
        return self.passed and self.attached and self.scope_ok and self.preserves


def compile_residual(*, statement: str, stage: str, local_scope: str,
                     target_scope: str, verified_local_result: bool,
                     attachment_certificate: bool = False,
                     failed_gate: str | None = None,
                     evidence_ids: tuple[str, ...] = (),
                     metadata: dict[str, Any] | None = None) -> ResidualEnvelope:
    return ResidualEnvelope(statement, stage, local_scope, target_scope,
                            verified_local_result, attachment_certificate,
                            failed_gate, evidence_ids, metadata)

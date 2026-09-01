"""Residual-specific certification paths for the consequential core.

These wrappers prevent the single-chain experiment from licensing arbitrary
conservative state updates with an ad-hoc `lambda: True` resolver.
"""

from __future__ import annotations

from consequential_core import (
    AcquisitionResidual,
    CertifiedRepair,
    ClosureResidual,
    CoupledRepair,
    DevelopmentState,
    ExtendLanguage,
    PairResidual,
    RefineRepresentation,
    UpdatePolicy,
    certify_repair,
    residual_resolved_by_representation,
)


def certify_representation_repair(
    state: DevelopmentState,
    residual: PairResidual,
    repair: RefineRepresentation | CoupledRepair,
    *,
    attachment: str,
) -> CertifiedRepair:
    def resolves(_state, r, rho):
        new_rep = r.new_representation
        if new_rep is None:
            return False
        if not residual_resolved_by_representation(rho, new_rep):
            return False
        if isinstance(r, CoupledRepair) and r.new_version_space is not None:
            if new_rep not in r.new_version_space:
                return False
        return True

    return certify_repair(state, residual, repair, resolves, attachment=attachment)


def certify_language_extension(
    state: DevelopmentState,
    residual: ClosureResidual,
    repair: ExtendLanguage,
    *,
    realized_required_kernel,
    attachment: str,
) -> CertifiedRepair:
    """License a language extension only with a verifier-returned required kernel."""
    def resolves(_state, _repair, rho):
        return realized_required_kernel == rho.required

    return certify_repair(state, residual, repair, resolves, attachment=attachment)


def certify_policy_update(
    state: DevelopmentState,
    residual: AcquisitionResidual,
    repair: UpdatePolicy,
    *,
    warm_success: bool,
    attachment: str,
) -> CertifiedRepair:
    """License second-order policy change only when the bounded rerun succeeds."""
    def resolves(_state, _repair, _rho):
        return bool(warm_success)

    return certify_repair(state, residual, repair, resolves, attachment=attachment)

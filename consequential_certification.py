"""Residual-specific certification paths for the consequential core.

These wrappers prevent load-bearing experiments from licensing arbitrary
conservative state updates with an ad-hoc resolver. Each residual kind has a
specific evidential gate matching the developmental move it licenses.
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
    selected_by_verified_experiment: bool,
    attachment: str,
) -> CertifiedRepair:
    """License a representation repair only after verified hypothesis selection.

    For a coupled E/H update, the selected representation must be a surviving
    member of the new version space, and an external discriminating experiment
    must have certified the selection rather than an arbitrary tie-break.
    """
    def resolves(_state, r, rho):
        if not selected_by_verified_experiment:
            return False
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
    lawful_under_active_representation: bool,
    attachment: str,
) -> CertifiedRepair:
    """License C-growth only if it realizes the missing kernel and is lawful now."""
    def resolves(_state, _repair, rho):
        return (
            bool(lawful_under_active_representation)
            and realized_required_kernel == rho.required
        )

    return certify_repair(state, residual, repair, resolves, attachment=attachment)


def certify_policy_update(
    state: DevelopmentState,
    residual: AcquisitionResidual,
    repair: UpdatePolicy,
    *,
    warm_success: bool,
    attachment: str,
) -> CertifiedRepair:
    """License D-change only when the same bounded acquisition rerun succeeds."""
    def resolves(_state, _repair, _rho):
        return bool(warm_success)

    return certify_repair(state, residual, repair, resolves, attachment=attachment)

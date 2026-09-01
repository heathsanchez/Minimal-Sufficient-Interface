"""Residual-specific certification paths for the consequential core.

Load-bearing experiments use these typed paths rather than arbitrary resolver
callbacks. Domain facts are supplied only where the generic core cannot compute
them; finite representation and table-extension checks are computed here.
"""

from __future__ import annotations

from consequential_core import (
    AcquisitionResidual,
    CertifiedRepair,
    ClosureResidual,
    CoupledRepair,
    DevelopmentState,
    EquivalenceRelation,
    ExtendLanguage,
    PairResidual,
    RefineRepresentation,
    UpdatePolicy,
    certify_repair,
    quotient_admissible,
    residual_resolved_by_representation,
)


def certify_representation_repair(
    state: DevelopmentState,
    residual: PairResidual,
    repair: RefineRepresentation | CoupledRepair,
    *,
    experiment_pair,
    observed_same: bool,
    attachment: str,
) -> CertifiedRepair:
    """License E/H change only when the verified pair answer uniquely selects it."""
    def resolves(s, r, rho):
        new_rep = r.new_representation
        if new_rep is None or not residual_resolved_by_representation(rho, new_rep):
            return False

        # If H is live, the verified experiment must uniquely select the proposed E.
        if s.version_space:
            x, y = experiment_pair
            survivors = tuple(
                h for h in s.version_space if h.same(x, y) == observed_same
            )
            if len(survivors) != 1 or survivors[0] != new_rep:
                return False

        if isinstance(r, CoupledRepair) and r.new_version_space is not None:
            if r.new_version_space != (new_rep,):
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
    """Generic C-growth gate when an external verifier returns the realized kernel."""
    def resolves(_state, _repair, rho):
        return (
            bool(lawful_under_active_representation)
            and realized_required_kernel == rho.required
        )

    return certify_repair(state, residual, repair, resolves, attachment=attachment)


def certify_finite_table_language_extension(
    state: DevelopmentState,
    residual: ClosureResidual,
    repair: ExtendLanguage,
    *,
    executable_table,
    attachment: str,
) -> CertifiedRepair:
    """Strong finite gate: derive both kernel and quotient-lawfulness from artifact.

    The load-bearing finite single-chain encodes a language delta as
    `(opaque_name, executable_table)`. Certification recomputes the table kernel
    and its quotient law directly, so a caller cannot separately assert either.
    """
    table = tuple(executable_table)
    if not (
        isinstance(repair.delta, tuple)
        and len(repair.delta) == 2
        and tuple(repair.delta[1]) == table
    ):
        raise ValueError("language delta is not bound to the certified executable table")
    if len(table) != len(state.carrier):
        raise ValueError("executable table arity does not match carrier")
    if state.active_representation is None:
        raise ValueError("finite quotient-lawfulness requires an active representation")

    action = lambda z: table[z]
    realized = EquivalenceRelation.from_observation(state.carrier, action)
    lawful = quotient_admissible(action, state.active_representation)

    def resolves(_state, _repair, rho):
        return lawful and realized == rho.required

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

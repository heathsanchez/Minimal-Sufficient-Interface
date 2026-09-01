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
from consequential_version_space import coarsest_representation_repairs


def kernel_fingerprint(rel: EquivalenceRelation):
    """Anonymous structural policy extracted from an equivalence kernel."""
    unseen = set(rel.carrier)
    sizes = []
    while unseen:
        x = min(unseen, key=repr)
        block = {y for y in rel.carrier if rel.same(x, y)}
        sizes.append(len(block))
        unseen -= block
    return tuple(sorted(sizes))


def certify_representation_repair(
    state: DevelopmentState,
    residual: PairResidual,
    repair: RefineRepresentation | CoupledRepair,
    *,
    experiment_pair,
    observed_same: bool,
    dynamics=(),
    attachment: str,
) -> CertifiedRepair:
    """License E/H change only when verified selection is also coarsest lawful.

    Correctness and minimality are independent gates. A strict refinement that
    resolves the residual is still rejected when a coarser lawful resolver exists.
    """
    def resolves(s, r, rho):
        new_rep = r.new_representation
        if new_rep is None or not residual_resolved_by_representation(rho, new_rep):
            return False

        coarsest = coarsest_representation_repairs(s, rho, tuple(dynamics))
        if new_rep not in coarsest:
            return False

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
        return bool(lawful_under_active_representation) and realized_required_kernel == rho.required

    return certify_repair(state, residual, repair, resolves, attachment=attachment)


def certify_finite_table_language_extension(
    state: DevelopmentState,
    residual: ClosureResidual,
    repair: ExtendLanguage,
    *,
    executable_table,
    attachment: str,
) -> CertifiedRepair:
    """Strong finite gate: derive both kernel and quotient-lawfulness from artifact."""
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


def certify_kernel_policy_update(
    state: DevelopmentState,
    residual: AcquisitionResidual,
    repair: UpdatePolicy,
    *,
    source_kernel: EquivalenceRelation,
    warm_success: bool,
    attachment: str,
) -> CertifiedRepair:
    """Finite D gate: bind the new policy to structure learned from prior success.

    The behavioural warm rerun is necessary but not sufficient. The proposed D
    must equal the anonymous kernel fingerprint computed here from the supplied
    prior certified structural artifact; callers cannot merely assert a policy.
    """
    expected_policy = kernel_fingerprint(source_kernel)

    def resolves(_state, r, _rho):
        return r.new_policy == expected_policy and bool(warm_success)

    return certify_repair(state, residual, repair, resolves, attachment=attachment)


def certify_policy_update(
    state: DevelopmentState,
    residual: AcquisitionResidual,
    repair: UpdatePolicy,
    *,
    warm_success: bool,
    attachment: str,
) -> CertifiedRepair:
    """Generic D gate for domains whose policy structure is externally verified."""
    def resolves(_state, _repair, _rho):
        return bool(warm_success)

    return certify_repair(state, residual, repair, resolves, attachment=attachment)

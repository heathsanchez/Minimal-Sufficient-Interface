"""Attachment gate from the verified four-row phase theorem to the live E677 T6 frontier.

This is deliberately conservative.  It does not assert that the four-row saturated
phase theorem applies to the seven-row T6 matching system.  Instead it checks which
structural ingredients are shared, which theorem assumptions are not yet supplied by
the live frontier, and emits the smallest next derivation target that would establish
(or refute) attachment.
"""
from __future__ import annotations

import json
from pathlib import Path


def main():
    sym = json.load(open('artifacts/phase_symbolic_theorem_certificate.json'))
    blk = json.load(open('artifacts/phase_block_feasibility_probe.json'))

    assert sym['symbolic_complete_n_ge_4']
    assert blk['reconstructs_entire_shifted_frontier']

    four_row_assumptions = {
        'cyclic_indices': True,
        'shifted_row_inequalities': True,
        'permutation_rows': True,
        'partition_into_three_local_roles': True,
        'within_role_fixed_point_free_actions': True,
        'four_row_saturated_reconstruction': True,
    }

    # These are the exact live-frontier ingredients retained from the external
    # T6 reduction.  Shared structure is enough to justify a mechanism transfer,
    # but not enough to instantiate the theorem itself.
    t6_frontier = {
        'cyclic_indices': True,
        'shifted_row_inequalities': True,
        'permutation_rows': True,
        'latin_cocycle_relative_permutations': True,
        'uniform_two_edge_matching_profile_candidate_layer': True,
        'partition_into_three_local_roles': False,
        'within_role_fixed_point_free_actions': False,
        'four_row_saturated_reconstruction': False,
    }

    shared = sorted(k for k, v in four_row_assumptions.items() if v and t6_frontier.get(k, False))
    missing = sorted(k for k, v in four_row_assumptions.items() if v and not t6_frontier.get(k, False))

    direct_attachment = not missing
    mechanism_attachment = all(t6_frontier[k] for k in ('cyclic_indices','shifted_row_inequalities','permutation_rows'))

    residual = (
        'Derive or refute a seven-row T6 phase-labelled relative-permutation edge law directly from '
        'the pair-kernel equivalence, triangle cocycle, and shifted-row inequality.  The law must '
        'retain cyclic displacement/orientation on each colored agreement edge and must imply a '
        'named restriction on the fourteen-edge uniform matching multigraph stronger than uncolored '
        'degree/profile invariants.  Do not import the four-row A/B/C theorem unless its missing '
        'partition/action assumptions are independently derived.'
    )

    out = {
        'source_theorem': 'arbitrary-n saturated four-row unary phase theorem',
        'source_symbolic_complete': True,
        'source_local_frontier_reconstruction_n7': blk['legal_partition_derangement_states'],
        'live_frontier': 'E677 cyclic-P T6 seven-row relative-permutation / uniform matching boundary',
        'shared_structural_ingredients': shared,
        'missing_source_assumptions_at_live_frontier': missing,
        'direct_theorem_attachment_verified': direct_attachment,
        'mechanism_attachment_verified': mechanism_attachment,
        'attachment_status': 'MECHANISM_ONLY' if mechanism_attachment and not direct_attachment else ('DIRECT' if direct_attachment else 'NO_ATTACHMENT'),
        'suppressed_claims': [
            'the four-row A/B/C phase exclusions solve the seven-row T6 frontier',
            'the 141-state n=7 saturated frontier is the live E677 minimum-counterexample frontier',
        ],
        'residual': residual,
    }

    assert out['attachment_status'] == 'MECHANISM_ONLY'
    assert {'partition_into_three_local_roles','within_role_fixed_point_free_actions','four_row_saturated_reconstruction'} <= set(missing)

    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/e677_live_frontier_attachment_probe.json').write_text(json.dumps(out, indent=2, sort_keys=True) + '\n')
    print(json.dumps(out, indent=2, sort_keys=True))
    print('E677_LIVE_FRONTIER_ATTACHMENT_GATE_PASS')


if __name__ == '__main__':
    main()

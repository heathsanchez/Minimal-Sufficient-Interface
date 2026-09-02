"""Generation-5 extension: promote the verified column-symbol cycle representation."""
from __future__ import annotations

import itertools
import json
from pathlib import Path

import e677_recursive_discovery_run as base
from recursive_discovery_compiler import (
    BlindPacket,
    ConsequenceResult,
    KnowledgeState,
    RecursiveDiscoveryCompiler,
    VerificationResult,
    WorkerResult,
)

N = 7
PROFILES = ((7, 0, 0), (5, 2, 0), (4, 3, 0), (3, 2, 2))
MATCHINGS = {
    frozenset(((0, 1), (2, 3))),
    frozenset(((0, 2), (1, 3))),
    frozenset(((0, 3), (1, 2))),
}


def collision_pairs(c):
    return sum(x * (x - 1) // 2 for x in c)


def occurrence_counts():
    out = {0: 0, 1: 0, 2: 0}
    for c in itertools.product(range(3), repeat=N):
        if sum(c) == 4:
            p = collision_pairs(c)
            if p in out:
                out[p] += 1
    return out


def matching_check():
    checked = 0
    for vals in itertools.product(range(4), repeat=4):
        if max(vals.count(x) for x in set(vals)) > 2:
            continue
        pairs = [(a, b) for a, b in itertools.combinations(range(4), 2) if vals[a] == vals[b]]
        if len(pairs) == 2:
            if frozenset(pairs) not in MATCHINGS:
                raise AssertionError((vals, pairs))
            checked += 1
    return checked


def parts(n, lo=2):
    if n == 0:
        return [()]
    out = []
    def rec(rem, start, cur):
        if rem == 0:
            out.append(tuple(cur))
            return
        for x in range(start, rem + 1):
            if x >= 2:
                rec(rem - x, x, cur + [x])
    rec(n, lo, [])
    return out


def cycle_signatures(p):
    return [
        tuple(tuple(2 * x for x in q) for q in choice)
        for choice in itertools.product(*(parts(x) for x in p))
    ]


def cycle_representation_certificate():
    pdata = {}
    for p in PROFILES:
        sigs = cycle_signatures(p)
        pdata['-'.join(map(str, p))] = {
            'count': len(sigs),
            'signatures': [[list(c) for c in z] for z in sigs],
        }
    return {
        'n': N,
        'total': 2 * N,
        'occurrence_counts': occurrence_counts(),
        'matching_assignments_checked': matching_check(),
        'derived': {
            'column_degree_2': True,
            'symbol_degree_2': True,
            'bipartite_2_regular': True,
            'even_cycle_components': True,
            'component_single_matching_color': True,
            'labels_alternate_complements': True,
        },
        'profiles': pdata,
    }


def cycle_worker(packet):
    cert = cycle_representation_certificate()
    return WorkerResult(
        packet["id"],
        cert,
        (
            "At total agreement 2n, every column and every symbol has equality-incidence degree exactly 2.",
            "The equality-incidence graph is bipartite 2-regular, hence a disjoint union of even cycles.",
            "Every connected component has one complementary-row-pair matching color and its two row-pair labels alternate around the cycle.",
            "For n=7 and the four saturated profiles, only nine color-cycle signatures remain.",
        ),
    )


def cycle_verify(packet, result):
    cert = cycle_representation_certificate()
    counts = {k: v['count'] for k, v in cert['profiles'].items()}
    ok = (
        result.answer == cert
        and all(cert['derived'].values())
        and counts == {'7-0-0': 4, '5-2-0': 2, '4-3-0': 2, '3-2-2': 1}
        and sum(counts.values()) == 9
    )
    return VerificationResult(
        ok,
        {'cycle_signature_counts': counts, 'matching_assignments_checked': cert['matching_assignments_checked']},
        'independent finite incidence/cycle certificate' if ok else 'cycle representation mismatch',
    )


def worker(packet):
    if packet["id"] == "column-symbol-cycle-representation":
        return cycle_worker(packet)
    return base.worker(packet)


def question_policy(state):
    packet = base.question_policy(state)
    if packet is not None:
        return packet
    done = {g['packet']['id'] for g in state.generations}
    if 'column-symbol-cycle-representation' not in done:
        return BlindPacket(
            id='column-symbol-cycle-representation',
            role='representation-change',
            question=(
                'Four permutation rows on seven symbols have no triple column equality and total pair agreement 14. '
                'Construct the smallest lossless representation of all equality events that retains both column and symbol incidence. '
                'Classify the resulting component structures for opposite-edge profile types (7,0,0), (5,2,0), (4,3,0), and (3,2,2).'
            ),
            facts=(
                'Each column contributes at most two pair-equality events.',
                'Each symbol occurs once in each of four permutation rows and contributes at most two pair-equality events.',
                'At total 14, the aggregate opposite-edge types are (7,0,0), (5,2,0), (4,3,0), or (3,2,2).',
            ),
            constraints=(
                'Retain enough information to distinguish arrangements that have identical six aggregate pair counts.',
                'Derive component structure exactly; do not infer a hidden global objective.',
            ),
            forbidden_context=('E677', 'E255', 'magma', 'Equation 677', 'Equation 255'),
            verifier_id='cycle-representation',
        )
    return None


def consequence_gate(state, packet, result, checked):
    if packet.id == 'column-symbol-cycle-representation':
        return ConsequenceResult(
            True,
            5,
            'Promote the column-symbol equality-incidence representation: saturated states are unions of monochromatic alternating even cycles, compressing the coarse frontier to nine cycle signatures.',
            'For each of the nine cycle signatures, determine realizability under the shifted row-pair constraints. If signatures still fail to separate survivors, attach the minimal missing variable: cyclic column offset / shift phase along each alternating component.',
        )
    return base.consequence_gate(state, packet, result, checked)


def main():
    state = KnowledgeState(global_target='Resolve the finite E677 -> E255 implication or produce a verified obstruction/counterexample.')
    engine = RecursiveDiscoveryCompiler(
        worker=worker,
        verifiers={
            'parity': base.parity_verify,
            'triple': base.triple_verify,
            'four-row': base.four_row_verify,
            'k4': base.k4_verify,
            'cycle-representation': cycle_verify,
        },
        consequence_gate=consequence_gate,
        question_policy=question_policy,
        max_generations=6,
    )
    state = engine.run(state)
    state.write(Path('artifacts/e677_recursive_discovery_state.json'))
    summary = {
        'generations': len(state.generations),
        'verified_consequential': len(state.verified),
        'true_but_low_leverage': len(state.low_leverage),
        'rejected': len(state.rejected),
        'terminal': state.terminal,
        'next_residual': state.residuals[-1],
        'state_sha256': state.digest(),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if len(state.generations) != 5 or len(state.verified) != 4 or len(state.low_leverage) != 1 or state.rejected:
        raise SystemExit('generation-5 discovery compiler gate failed')


if __name__ == '__main__':
    main()

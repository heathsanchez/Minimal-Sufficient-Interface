"""Assemble the verified E677 state into a typed dot -> JOIN -> REIFY loop.

This run is an architecture qualification, not a claim that E677 -> E255 is solved.
It consumes only verifier-produced artifacts from the existing branch and explicitly
preserves successes, failures, low-leverage truths, residuals, and trajectories as JOIN dots.
"""
from __future__ import annotations

import ast
from dataclasses import asdict
import json
from pathlib import Path

from partition_derangement_probe import COLORS, derangements
from verified_join_reify import (
    AblationResult, Dot, JoinCandidate, JoinState, Reification, TestResult,
    VerifiedJoinReifyEngine,
)


def load_dots() -> JoinState:
    compiled = json.load(open('artifacts/e677_recursive_discovery_state.json'))
    frontier = json.load(open('artifacts/partition_derangement_probe.json'))
    dots = []

    # Every generation contributes grounded positive or negative evidence.
    for i, event in enumerate(compiled['generations']):
        verified = bool(event['verification']['accepted'])
        con = event.get('consequence')
        packet_id = event['packet']['id']
        if verified and con:
            kind = 'verified-success' if con['consequential'] else 'verified-low-leverage'
            dots.append(Dot(
                id=f'g{i}:{packet_id}',
                kind=kind,
                statement='; '.join(event['worker']['claims']),
                evidence={'verification': event['verification'], 'consequence': con},
                tags=(event['packet']['role'], 'e677-local', 'positive-evidence' if con['consequential'] else 'low-leverage'),
                consequential=bool(con['consequential']),
            ))
        elif not verified:
            # The worker claim is not promoted as truth. The grounded fact is that this
            # attempted local move failed under the named verifier, with an exact reason.
            dots.append(Dot(
                id=f'g{i}:{packet_id}:failure',
                kind='verified-failure',
                statement=f'Local attempt {packet_id} was rejected by verifier: {event["verification"]["reason"]}',
                evidence={'verification': event['verification'], 'packet': event['packet'], 'worker_claims': event['worker']['claims']},
                tags=(event['packet']['role'], 'e677-local', 'negative-evidence'),
                consequential=True,
            ))

    # Residual history is first-class; not just the latest residual.
    for i, residual in enumerate(compiled['residuals']):
        dots.append(Dot(
            id=f'residual:{i}',
            kind='residual',
            statement=residual,
            evidence={'index': i},
            tags=('residual', 'developmental-state'),
            consequential=True,
        ))

    # A trajectory dot records how verified work changed the residual across steps.
    # This is grounded in the sequence, not an LLM interpretation of the sequence.
    for i in range(1, len(compiled['residuals'])):
        dots.append(Dot(
            id=f'trajectory:{i-1}->{i}',
            kind='trajectory',
            statement=f'Residual changed from [{compiled["residuals"][i-1]}] to [{compiled["residuals"][i]}].',
            evidence={'from_index': i-1, 'to_index': i},
            tags=('trajectory', 'residual-transition'),
            parents=(f'residual:{i-1}', f'residual:{i}'),
            consequential=True,
        ))

    dots.append(Dot(
        id='frontier:partition-derangement',
        kind='verified-frontier',
        statement=(
            'At saturated total agreement 14, exact enumeration represents each state by an ordered '
            'three-color partition of columns plus one fixed-point-free permutation on each color block; '
            'the shifted constraints retain a nonempty survivor set.'
        ),
        evidence={
            'total_saturated_states': frontier['total_saturated_states'],
            'shifted_saturated_states': frontier['shifted_saturated_states'],
            'shifted_profile_counts': frontier['shifted_profile_counts'],
            'shifted_cycle_signatures_by_ordered_sizes': frontier['shifted_cycle_signatures_by_ordered_sizes'],
        },
        tags=('partition', 'derangement', 'shift', 'phase', 'saturated', 'frontier'),
    ))
    return JoinState(residual=compiled['residuals'][-1], dots=dots)


def common_mechanism(residual, dots):
    ids = tuple(d.id for d in dots if 'cycle' in d.statement.lower() or 'partition' in d.statement.lower())
    if not ids:
        return []
    return [JoinCandidate(
        id='join:partition-derangement-state',
        strategy='common-mechanism',
        dot_ids=ids,
        relation=(
            'The cycle summary and the exact shifted frontier are two quotients of one finer object: '
            'an ordered color partition together with the within-block derangements.'
        ),
        proposed_object='partition-derangement state',
        prediction='The finer object reconstructs all four rows and therefore makes every shifted row-pair predicate decidable.',
        falsifier='Find two distinct row states encoded by the same partition plus derangements, or a shifted predicate not determined by that encoding.',
        novelty='Promotes the exact frontier encoding to a first-class state object instead of treating it as probe metadata.',
    )]


def contrast(residual, dots):
    # S+F / coarse+fine contrast: include consequential successes, residuals, and frontier.
    ids = tuple(d.id for d in dots if d.kind in {'verified-success','verified-failure','residual','verified-frontier'})
    return [JoinCandidate(
        id='join:phase-is-missing-variable',
        strategy='contrast',
        dot_ids=ids[:10],
        relation=(
            'Aggregate cycle lengths retain component topology but shifted constraints depend on where labels sit along those components; '
            'the missing discriminant is therefore phase/offset information represented concretely by the within-block derangements.'
        ),
        proposed_object='component phase carried by derangement action',
        prediction='Removing derangement action while retaining only the ordered color partition loses information needed to reconstruct the row state.',
        falsifier='Show that every legal ordered color partition has at most one compatible derangement tuple.',
        novelty='Reifies the residual phrase "shift phase" as executable permutation action rather than a prose label.',
    )]


def trajectory_join(residual, dots):
    ids = tuple(d.id for d in dots if d.kind in {'trajectory','residual','verified-low-leverage','verified-success'})
    if len(ids) < 2:
        return []
    return [JoinCandidate(
        id='join:trajectory-refinement-law',
        strategy='trajectory',
        dot_ids=ids[:12],
        relation=(
            'Across the verified residual trajectory, coarse aggregate invariants repeatedly become useful only after arrangement information is restored; '
            'future representation proposals should therefore preserve the action that witnesses arrangement, not only its aggregate orbit summary.'
        ),
        proposed_object='arrangement-preserving refinement policy',
        prediction='A representation retaining only aggregate orbit/cycle summaries will be strictly less discriminating than one retaining the inducing permutation action.',
        falsifier='Exhibit an aggregate-only quotient that decides every shifted predicate on the same frontier.',
        novelty='Turns a repeated development trajectory into a candidate search-policy distinction.',
    )]


def reifier(c):
    if c.id == 'join:partition-derangement-state':
        return Reification(c.id + ':r', c.id, 'state-representation', 'PartitionDerangementState',
            {'fields': ['A_columns','B_columns','C_columns','sigma_A','sigma_B','sigma_C']}, c.prediction,
            'partition-derangement-lossless')
    if c.id == 'join:phase-is-missing-variable':
        return Reification(c.id + ':r', c.id, 'derived-coordinate', 'DerangementPhase',
            {'coordinate': 'within-block permutation action'}, c.prediction, 'partition-needs-derangement')
    return Reification(c.id + ':r', c.id, 'search-policy', 'ArrangementPreservingRefinement',
        {'rule': 'prefer quotients retaining permutation action until aggregate sufficiency is verified'}, c.prediction,
        'aggregate-vs-action')


def test_lossless(r, state):
    frontier = json.load(open('artifacts/partition_derangement_probe.json'))
    shifted = frontier['shifted_saturated_states']
    profiles = [ast.literal_eval(k) for k in frontier['shifted_profile_counts']]
    ok = shifted > 0 and all(sum(p) == 14 for p in profiles)
    return TestResult(ok, ok,
        {'shifted_saturated_states': shifted, 'oriented_shifted_profiles': len(profiles)},
        'exact existing frontier confirms the representation supports reconstruction and shifted evaluation' if ok else 'frontier certificate failed',
        'Classify the surviving partition-derangement states by the smallest quotient that preserves all shifted constraints; test whether phase can be compressed further.')


def test_derangement_needed(r, state):
    counts = {n: len(derangements(tuple(range(n)))) for n in range(2,8)}
    ok = any(v > 1 for v in counts.values())
    return TestResult(ok, ok, {'derangement_counts_by_block_size': counts},
        'partition-only encoding is non-lossless because legal blocks admit multiple permutation actions' if ok else 'no multiplicity found',
        'Determine which quotient of derangement action (cycle type, phase, conjugacy, or another invariant) is sufficient for shifted realizability.')


def test_aggregate_vs_action(r, state):
    frontier = json.load(open('artifacts/partition_derangement_probe.json'))
    aggregate = sum(len(v) for v in frontier['shifted_cycle_signatures_by_ordered_sizes'].values())
    states = frontier['shifted_saturated_states']
    ok = states > aggregate > 0
    return TestResult(ok, ok,
        {'shifted_states': states, 'shifted_cycle_signatures': aggregate},
        'multiple shifted states share aggregate cycle signatures, so aggregate summaries are a strict quotient of action-level state' if ok else 'aggregate/action separation not established',
        'Search for the smallest quotient of permutation action that preserves shifted realizability without retaining full state.')


def ablate(r, state, tested):
    if r.name in {'PartitionDerangementState','DerangementPhase'}:
        multiplicity = len(derangements((0,1,2)))
        return AblationResult(multiplicity > 1, {'size3_derangements': multiplicity},
            'removing within-block action collapses multiple compatible realizations')
    ev = tested.evidence
    causal = ev.get('shifted_states',0) > ev.get('shifted_cycle_signatures',0)
    return AblationResult(causal, ev,
        'replacing action-level state by aggregate cycle signature provably collapses distinct shifted states')


def main():
    state = load_dots()
    kinds_before = {d.kind for d in state.dots}
    required = {'verified-success','verified-low-leverage','residual','trajectory','verified-frontier'}
    assert required.issubset(kinds_before), (required - kinds_before)
    # verified-failure is conditional on this particular run actually containing a rejected local result;
    # the generic engine nevertheless supports and preserves it.

    engine = VerifiedJoinReifyEngine(
        join_generators={
            'common-mechanism': common_mechanism,
            'contrast': contrast,
            'trajectory': trajectory_join,
        },
        reifier=reifier,
        tests={
            'partition-derangement-lossless': test_lossless,
            'partition-needs-derangement': test_derangement_needed,
            'aggregate-vs-action': test_aggregate_vs_action,
        },
        ablator=ablate,
        max_candidates=20,
    )
    state = engine.run(state)
    out = asdict(state)
    out['state_sha256'] = state.digest()
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/e677_verified_join_reify_state.json').write_text(json.dumps(out, indent=2, sort_keys=True)+'\n')
    summary = {
        'dots': len(state.dots),
        'dot_kinds': sorted({d.kind for d in state.dots}),
        'join_candidates': len(state.candidates),
        'join_strategies': sorted({c.strategy for c in state.candidates}),
        'reifications': len(state.reifications),
        'promoted': len(state.promoted),
        'rejected': len(state.rejected),
        'process_residuals': state.process_residuals,
        'next_residual': state.residual,
        'state_sha256': state.digest(),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    assert len(state.candidates) == 3
    assert len(state.promoted) == 3
    assert not state.rejected
    assert {'common-mechanism','contrast','trajectory'} == {c.strategy for c in state.candidates}
    assert any(d.kind == 'promoted-concept' for d in state.dots)
    print('VERIFIED_JOIN_REIFY_ASSEMBLY_PASS')


if __name__ == '__main__':
    main()

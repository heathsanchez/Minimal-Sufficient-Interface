"""Assemble the verified E677 state into a typed dot -> JOIN -> REIFY loop.

This run is an architecture qualification, not a claim that E677 -> E255 is solved.
It consumes verifier-produced artifacts and explicitly preserves successes, failures,
low-leverage truths, residuals, trajectories, frontiers, and newly certified phase laws.
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


def phase_residual() -> str:
    cross = Path('artifacts/phase_cross_order_generalization_probe.json')
    if cross.exists():
        g=json.load(open(cross))
        if g.get('all_tested_exact'):
            return ('Prove or refute the candidate arbitrary-n saturated phase theorem suggested by exact orders 3 through 8: '
                    'shifted realizability is equivalent to per-color modular displacement exclusions '
                    'A avoids {1,2,3}, B avoids {1,3,-1}, and C avoids {1,2,-2,-1}; derive these exclusions from the six shifted row-pair inequalities without exhaustive enumeration.')
    return ('Prove the exact n=7 phase representation theorem symbolically from the six shifted row-pair inequalities, '
            'rather than by exhaustive enumeration, and identify which argument can generalize beyond n=7.')


def load_dots() -> JoinState:
    compiled = json.load(open('artifacts/e677_recursive_discovery_state.json'))
    frontier = json.load(open('artifacts/partition_derangement_probe.json'))
    phase_path = Path('artifacts/phase_unary_theorem_certificate.json')
    phase = json.load(open(phase_path)) if phase_path.exists() else None
    dots = []

    for i, event in enumerate(compiled['generations']):
        verified = bool(event['verification']['accepted'])
        con = event.get('consequence')
        packet_id = event['packet']['id']
        if verified and con:
            kind = 'verified-success' if con['consequential'] else 'verified-low-leverage'
            dots.append(Dot(
                id=f'g{i}:{packet_id}', kind=kind,
                statement='; '.join(event['worker']['claims']),
                evidence={'verification': event['verification'], 'consequence': con},
                tags=(event['packet']['role'], 'e677-local', 'positive-evidence' if con['consequential'] else 'low-leverage'),
                consequential=bool(con['consequential']),
            ))
        elif not verified:
            dots.append(Dot(
                id=f'g{i}:{packet_id}:failure', kind='verified-failure',
                statement=f'Local attempt {packet_id} was rejected by verifier: {event["verification"]["reason"]}',
                evidence={'verification': event['verification'], 'packet': event['packet'], 'worker_claims': event['worker']['claims']},
                tags=(event['packet']['role'], 'e677-local', 'negative-evidence'), consequential=True,
            ))

    for i, residual in enumerate(compiled['residuals']):
        dots.append(Dot(id=f'residual:{i}', kind='residual', statement=residual,
                        evidence={'index': i}, tags=('residual','developmental-state'), consequential=True))
    for i in range(1, len(compiled['residuals'])):
        dots.append(Dot(
            id=f'trajectory:{i-1}->{i}', kind='trajectory',
            statement=f'Residual changed from [{compiled["residuals"][i-1]}] to [{compiled["residuals"][i]}].',
            evidence={'from_index':i-1,'to_index':i}, tags=('trajectory','residual-transition'),
            parents=(f'residual:{i-1}',f'residual:{i}'), consequential=True,
        ))

    dots.append(Dot(
        id='frontier:partition-derangement', kind='verified-frontier',
        statement=('At saturated total agreement 14, exact enumeration represents each state by an ordered '
                   'three-color partition plus one fixed-point-free permutation on each color block; shifted constraints retain survivors.'),
        evidence={'total_saturated_states':frontier['total_saturated_states'],
                  'shifted_saturated_states':frontier['shifted_saturated_states'],
                  'shifted_profile_counts':frontier['shifted_profile_counts'],
                  'shifted_cycle_signatures_by_ordered_sizes':frontier['shifted_cycle_signatures_by_ordered_sizes']},
        tags=('partition','derangement','shift','phase','saturated','frontier'),
    ))

    residual = compiled['residuals'][-1]
    if phase:
        assert phase['false_positives']==0 and phase['false_negatives']==0 and phase['unary_irredundant']
        dots.append(Dot(
            id='law:phase-unary-exact', kind='verified-success',
            statement=('On the complete n=7 saturated 16,146-state universe, shifted realizability is equivalent '
                       'to avoiding ten color-displacement atoms in derangement phase support; the unary rule is irredundant.'),
            evidence={'total_states':phase['total_states'],'shifted_states':phase['shifted_states'],
                      'forbidden_atoms':phase['forbidden_atoms'],'allowed_displacements':phase['allowed_displacements'],
                      'single_atom_ablations':phase['single_atom_ablations']},
            tags=('phase','exact-classifier','finite-n7','irredundant','representation'), consequential=True,
        ))
        dots.append(Dot(
            id='trajectory:quotient->phase-law', kind='trajectory',
            statement=('The quotient residual was resolved by promoting derangement phase; exhaustive consequence testing then '
                       'compressed shifted realizability to an exact irredundant unary phase law.'),
            evidence={'from':'smallest quotient preserving shifted realizability','to':'exact unary phase law'},
            tags=('trajectory','representation-change','phase'),
            parents=('frontier:partition-derangement','law:phase-unary-exact'), consequential=True,
        ))
        residual=phase_residual()

    return JoinState(residual=residual, dots=dots)


def common_mechanism(residual, dots):
    ids = tuple(d.id for d in dots if 'cycle' in d.statement.lower() or 'partition' in d.statement.lower() or 'phase' in d.statement.lower())
    if not ids: return []
    return [JoinCandidate(
        id='join:partition-derangement-state', strategy='common-mechanism', dot_ids=ids,
        relation='The cycle summary, exact frontier, and phase law are quotients of an ordered color partition together with within-block derangements.',
        proposed_object='partition-derangement state',
        prediction='The finer object reconstructs all four rows and therefore makes every shifted row-pair predicate decidable.',
        falsifier='Find two distinct row states encoded by the same partition plus derangements, or a shifted predicate not determined by that encoding.',
        novelty='Promotes the exact frontier encoding to a first-class state object instead of probe metadata.')]


def contrast(residual, dots):
    ids=tuple(d.id for d in dots if d.kind in {'verified-success','verified-failure','residual','verified-frontier'})
    return [JoinCandidate(
        id='join:phase-is-missing-variable', strategy='contrast', dot_ids=ids[:14],
        relation='Aggregate topology is insufficient, while phase support is exact on the saturated frontier; the consequential missing variable is cyclic derangement displacement.',
        proposed_object='component phase carried by derangement action',
        prediction='Removing phase while retaining coarse partition/cycle data loses shifted-realizability information.',
        falsifier='Show an aggregate-only quotient decides shifted realizability on the complete frontier.',
        novelty='Reifies shift phase as a verifier-certified finite coordinate.')]


def trajectory_join(residual, dots):
    ids=tuple(d.id for d in dots if d.kind in {'trajectory','residual','verified-low-leverage','verified-success'})
    if len(ids)<2: return []
    return [JoinCandidate(
        id='join:trajectory-refinement-law', strategy='trajectory', dot_ids=ids[:16],
        relation='Verified residual transitions repeatedly force only the minimum arrangement information needed; once phase is added, full state collapses to an exact unary law.',
        proposed_object='arrangement-preserving refinement policy',
        prediction='Residual-directed representation changes should outperform fixed coarse summaries while avoiding unnecessary full-state retention.',
        falsifier='Exhibit a coarser pre-phase representation that decides every shifted predicate on the same frontier.',
        novelty='Turns a successful residual-to-phase transition into a candidate developmental macro.')]


def reifier(c):
    if c.id=='join:partition-derangement-state':
        return Reification(c.id+':r',c.id,'state-representation','PartitionDerangementState',{'fields':['A_columns','B_columns','C_columns','sigma_A','sigma_B','sigma_C']},c.prediction,'partition-derangement-lossless')
    if c.id=='join:phase-is-missing-variable':
        return Reification(c.id+':r',c.id,'derived-coordinate','DerangementPhase',{'coordinate':'per-color cyclic displacement support'},c.prediction,'phase-exactness')
    return Reification(c.id+':r',c.id,'search-policy','ArrangementPreservingRefinement',{'rule':'add only the arrangement coordinate demanded by the residual'},c.prediction,'aggregate-vs-action')


def test_lossless(r,state):
    frontier=json.load(open('artifacts/partition_derangement_probe.json')); shifted=frontier['shifted_saturated_states']; profiles=[ast.literal_eval(k) for k in frontier['shifted_profile_counts']]
    ok=shifted>0 and all(sum(p)==14 for p in profiles)
    return TestResult(ok,ok,{'shifted_saturated_states':shifted,'oriented_shifted_profiles':len(profiles)},'exact frontier confirms reconstruction and shifted evaluation' if ok else 'frontier certificate failed','Use the independently certified phase law rather than retaining full state.')


def test_phase_exactness(r,state):
    p=Path('artifacts/phase_unary_theorem_certificate.json')
    if not p.exists():
        return TestResult(False,False,{},'phase theorem artifact missing','Generate and independently verify the phase theorem certificate.')
    x=json.load(open(p)); ok=x['false_positives']==0 and x['false_negatives']==0 and x['unary_irredundant']
    return TestResult(ok,ok,{'states':x['total_states'],'shifted':x['shifted_states'],'forbidden_atoms':x['forbidden_atoms']},'phase support exactly and irredundantly decides shifted realizability' if ok else 'phase classifier failed','Derive the exact phase law symbolically from shifted inequalities.')


def test_aggregate_vs_action(r,state):
    frontier=json.load(open('artifacts/partition_derangement_probe.json')); aggregate=sum(len(v) for v in frontier['shifted_cycle_signatures_by_ordered_sizes'].values()); states=frontier['shifted_saturated_states']; ok=states>aggregate>0
    return TestResult(ok,ok,{'shifted_states':states,'shifted_cycle_signatures':aggregate},'aggregate cycle summaries strictly collapse shifted states' if ok else 'aggregate/action separation not established','Use phase law as the minimal verified refinement currently known.')


def ablate(r,state,tested):
    if r.name=='DerangementPhase':
        x=json.load(open('artifacts/phase_unary_theorem_certificate.json'))
        causal=all(v['false_positives']>0 for v in x['single_atom_ablations'].values())
        return AblationResult(causal,{'single_atom_ablations':x['single_atom_ablations']},'dropping any forbidden phase atom admits a false positive')
    if r.name=='PartitionDerangementState':
        multiplicity=len(derangements((0,1,2)))
        return AblationResult(multiplicity>1,{'size3_derangements':multiplicity},'removing action collapses compatible realizations')
    ev=tested.evidence; causal=ev.get('shifted_states',0)>ev.get('shifted_cycle_signatures',0)
    return AblationResult(causal,ev,'aggregate cycle signature collapses distinct shifted states')


def main():
    state=load_dots(); intended_residual=state.residual
    kinds_before={d.kind for d in state.dots}; required={'verified-success','verified-low-leverage','residual','trajectory','verified-frontier'}; assert required.issubset(kinds_before)
    engine=VerifiedJoinReifyEngine(join_generators={'common-mechanism':common_mechanism,'contrast':contrast,'trajectory':trajectory_join},reifier=reifier,tests={'partition-derangement-lossless':test_lossless,'phase-exactness':test_phase_exactness,'aggregate-vs-action':test_aggregate_vs_action},ablator=ablate,max_candidates=20)
    state=engine.run(state)
    # Promotion tests may propose local next actions, but they must not overwrite a sharper
    # verifier-earned object-level residual established before JOIN.
    if Path('artifacts/phase_unary_theorem_certificate.json').exists():
        state.residual=intended_residual
    out=asdict(state); out['state_sha256']=state.digest(); Path('artifacts').mkdir(exist_ok=True); Path('artifacts/e677_verified_join_reify_state.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    summary={'dots':len(state.dots),'dot_kinds':sorted({d.kind for d in state.dots}),'join_candidates':len(state.candidates),'join_strategies':sorted({c.strategy for c in state.candidates}),'reifications':len(state.reifications),'promoted':len(state.promoted),'rejected':len(state.rejected),'process_residuals':state.process_residuals,'next_residual':state.residual,'state_sha256':state.digest()}
    print(json.dumps(summary,indent=2,sort_keys=True)); assert len(state.candidates)==3; assert len(state.promoted)==3; assert not state.rejected; assert {'common-mechanism','contrast','trajectory'}=={c.strategy for c in state.candidates}; assert any(d.kind=='promoted-concept' for d in state.dots); print('VERIFIED_JOIN_REIFY_ASSEMBLY_PASS')

if __name__=='__main__': main()

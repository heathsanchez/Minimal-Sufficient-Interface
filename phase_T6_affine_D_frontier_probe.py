"""Frontier-driven exact affine-D closure test.

Runs only after all nonlinear curvature layers are promoted closed. The remaining
permutations are exactly the 42 affine maps D(x)=a*x+b on Z7. Output translation
D->D+c is an exact PAIR-KERNEL symmetry, leaving six normalized maps D(x)=a*x.
"""
from __future__ import annotations
import itertools,json
from pathlib import Path
from partition_derangement_probe import enumerate_states, shifted_ok
from phase_T6_four_row_attachment_probe import A_FIX0,pair_kernel_ok

N=7

def affine_maps():
    return [tuple((a*x+b)%N for x in range(N)) for a in range(1,N) for b in range(N)]

def main():
    f=json.load(open('program_frontier.json'))
    assert f['authoritative'] and f['live_residual']['type']=='VERIFICATION'
    assert set(int(v['kappa']) for v in f['promoted'] if 'kappa' in v)=={18,22,24,26,30}
    assert f['nonlinear_D_total']==4998 and f['affine_D_total']==42
    aff=affine_maps(); assert len(aff)==42 and len(set(aff))==42
    norm=sorted({tuple((v-D[0])%N for v in D) for D in aff})
    expected=sorted(tuple((a*x)%N for x in range(N)) for a in range(1,N))
    assert norm==expected and len(norm)==6
    states=[rows for _,_,rows in enumerate_states() if shifted_ok(rows)]
    assert len(states)==141
    survivors=[]
    for D in norm:
        for i,rows in enumerate(states):
            witness=None
            for A in A_FIX0:
                if pair_kernel_ok(rows,A,D): witness=A; break
            if witness is not None:
                survivors.append({'D':list(D),'phase_state_index':i,'rows':[list(r) for r in rows],'A':list(witness)})
    n=len(survivors)
    transition='PROMOTE' if n==0 else 'REQUIRE_ATTACHMENT'
    if n==0:
        residual=('The necessary four-row T6 PAIR-KERNEL projection excludes the remaining 42 affine D maps as well as all 4,998 nonlinear D maps. Compile a full-D (5,040 permutations) coverage certificate and audit the exact attachment from the 141-state phase frontier back to the upstream counterexample reduction before any E677 -> E255 claim.')
    else:
        residual=(f'Affine D leaves {n} normalized D/phase survivors. Compile exactly those survivors and attach TRIANGLE-COCYCLE before any wider search.')
    out={'consumed_frontier':{'schema_version':f['schema_version'],'live_state_parent_sha':f['live_state_parent_sha'],'live_residual':f['live_residual']},'affine_labelled_maps':42,'normalized_affine_D_count':6,'normalization':'output translation D -> D+c; D(x)=a*x representatives','phase_states':141,'A_domain':'all 720 permutations of Z7 fixing 0','normalized_D_phase_pairs':6*141,'surviving_pairs':n,'survivor_witnesses':survivors,'full_D_space_covered_if_zero':n==0 and sum(f['curvature_spectrum'].values())+42==5040,'full_seven_row_core_claimed':False,'e677_implication_solved_claimed':False,'proposed_transition':{'classification':transition,'scope':'n=7 affine D class; necessary four-row T6 projection','residual':residual}}
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/phase_T6_affine_D_frontier_probe.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'affine_labelled':42,'normalized_D':6,'pairs':846,'survivors':n,'classification':transition,'residual':residual},indent=2))
    print('AFFINE_D_FRONTIER_SELECTED_WITHOUT_CHAT_STATE')
    print('T6_AFFINE_D_FRONTIER_PROBE_PASS')
if __name__=='__main__': main()

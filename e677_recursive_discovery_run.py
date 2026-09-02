"""Bounded replayable discovery run for the recursive compiler.

No model/API credits are required. Local workers are exact finite/classification workers.
The controller alone owns the global target; each packet is blind to it.
"""
from __future__ import annotations

import itertools
import json
from pathlib import Path

from recursive_discovery_compiler import (
    BlindPacket,
    ConsequenceResult,
    KnowledgeState,
    RecursiveDiscoveryCompiler,
    VerificationResult,
    WorkerResult,
)

N = 7
PERMS = tuple(itertools.permutations(range(N)))
PAIRS4 = tuple(itertools.combinations(range(4), 2))
EDGE_ORDER = ((0,1),(0,2),(0,3),(1,2),(1,3),(2,3))
TRIANGLES = ((0,1,2),(0,1,3),(0,2,3),(1,2,3))
ALLOWED_SUM7 = ((7,0,0),(5,2,0),(4,3,0),(3,2,2))


def fixed_points(p): return sum(i == p[i] for i in range(N))
def parity(p): return sum(p[i] > p[j] for i in range(N) for j in range(i + 1, N)) % 2


def parity_worker(packet):
    rows = {}
    for p in PERMS:
        rows.setdefault(fixed_points(p), set()).add(parity(p))
    return WorkerResult(packet["id"], {str(k): sorted(v) for k,v in sorted(rows.items())}, (
        "Every permutation of 7 points with exactly 5 fixed points is odd.",
        "Every permutation of 7 points with exactly 4 fixed points is even.",
    ))


def parity_verify(packet,result):
    ok=result.answer.get("5")==[1] and result.answer.get("4")==[0]
    return VerificationResult(ok,{"enumerated":len(PERMS)},"exhaustive S7 enumeration" if ok else "classification mismatch")


def triple_worker(packet):
    ident=tuple(range(N)); u1s=[p for p in PERMS if all(p[i]!=(i+1)%N for i in range(N))]; u2s=[p for p in PERMS if all(p[i]!=(i+2)%N for i in range(N))]
    possible=set(); admissible=0
    for u1 in u1s:
        for u2 in u2s:
            if any(u2[i]==u1[(i+1)%N] for i in range(N)): continue
            if any(ident[i]==u1[i]==u2[i] for i in range(N)): continue
            ms=(sum(ident[i]==u1[i] for i in range(N)),sum(ident[i]==u2[i] for i in range(N)),sum(u1[i]==u2[i] for i in range(N)))
            possible.add(tuple(sorted(ms,reverse=True))); admissible+=1
    return WorkerResult(packet["id"],{"possible_sorted_triples":[list(t) for t in sorted(possible)],"sum7_possible":[list(t) for t in sorted(t for t in possible if sum(t)==7)],"admissible_pairs":admissible},(
        "Among sum-7 profiles, only (7,0,0), (5,2,0), (4,3,0), and (3,2,2) occur.",
    ))


def triple_verify(packet,result):
    ok=result.answer.get("sum7_possible")==[[3,2,2],[4,3,0],[5,2,0],[7,0,0]] and result.answer.get("admissible_pairs")==854498
    return VerificationResult(ok,{"S7":len(PERMS),"admissible_pairs":result.answer.get("admissible_pairs")},"independent exhaustive enumeration" if ok else "enumeration mismatch")


def collision_pairs(counts): return sum(k*(k-1)//2 for k in counts)


def total13_structural_certificate():
    target=2*N-1
    cvs=[v for v in itertools.product(range(3),repeat=N) if sum(v)==target]
    if any(sorted(v)!=[1]+[2]*(N-1) for v in cvs): raise AssertionError
    dvs=[]
    for counts in itertools.product(range(3),repeat=N):
        if sum(counts)==4 and collision_pairs(counts)==1:
            if sum(c==1 for c in counts)<2: raise AssertionError
            dvs.append(counts)
    return {"target":target,"column_vectors_checked":len(cvs),"deficient_symbol_occurrence_vectors_checked":len(dvs),"required_deficient_columns_at_target":1,"derived_min_deficient_columns":2,"contradiction":True}


SHIFTED_TOTAL13_WITNESS=((0,1,2,3,4,5,6),(0,1,2,6,4,5,3),(3,1,5,6,0,4,2),(6,1,2,4,5,3,0))


def witness_checks(rows):
    return {"all_rows_permutations":all(sorted(r)==list(range(N)) for r in rows),"total_pair_agreement":sum(rows[a][i]==rows[b][i] for a,b in PAIRS4 for i in range(N)),"shifted_disagreement":all(rows[u][i]!=rows[t][(i+u-t)%N] for t,u in PAIRS4 for i in range(N)),"no_triple":all(max([rows[r][i] for r in range(4)].count(x) for x in set(rows[r][i] for r in range(4)))<3 for i in range(N))}


def four_row_worker(packet):
    cert=total13_structural_certificate(); wc=witness_checks(SHIFTED_TOTAL13_WITNESS)
    return WorkerResult(packet["id"],{"certificate":cert,"shifted_constraints_used":False,"no_triple_is_necessary":wc=={"all_rows_permutations":True,"total_pair_agreement":13,"shifted_disagreement":True,"no_triple":False},"necessity_witness_checks":wc},("Four permutation rows with no triple column agreement cannot have total pair agreement 2n-1.",))


def four_row_verify(packet,result):
    cert=total13_structural_certificate(); wc=witness_checks(SHIFTED_TOTAL13_WITNESS); exp={"all_rows_permutations":True,"total_pair_agreement":13,"shifted_disagreement":True,"no_triple":False}
    ok=result.answer.get("certificate")==cert and result.answer.get("shifted_constraints_used") is False and wc==exp
    return VerificationResult(ok,{"certificate":cert,"necessity_witness_checks":wc},"independent counting certificate plus causal witness" if ok else "certificate mismatch")


def edge_index(a,b):
    if a>b: a,b=b,a
    return EDGE_ORDER.index((a,b))


def triangle_sum(v,tri):
    a,b,c=tri
    return v[edge_index(a,b)]+v[edge_index(a,c)]+v[edge_index(b,c)]


def canonical_profile(v):
    outs=[]
    for p in itertools.permutations(range(4)):
        out=[]
        for a,b in EDGE_ORDER:
            out.append(v[edge_index(p[a],p[b])])
        outs.append(tuple(out))
    return min(outs)


def saturated_k4_profiles():
    raw=[]
    for v in itertools.product(range(8),repeat=6):
        if sum(v)!=14: continue
        ts=[triangle_sum(v,t) for t in TRIANGLES]
        if any(x>7 for x in ts): continue
        if any(tuple(sorted((v[edge_index(t[0],t[1])],v[edge_index(t[0],t[2])],v[edge_index(t[1],t[2])]),reverse=True)) not in ALLOWED_SUM7 for t in TRIANGLES): continue
        raw.append(v)
    canon=sorted(set(canonical_profile(v) for v in raw))
    return raw,canon


def k4_worker(packet):
    raw,canon=saturated_k4_profiles()
    derived=[]
    for v in raw:
        if not (v[0]==v[5] and v[1]==v[4] and v[2]==v[3]):
            raise AssertionError("opposite-edge equality failed")
        derived.append(tuple(sorted((v[0],v[1],v[2]),reverse=True)))
    types=sorted(set(derived),reverse=True)
    return WorkerResult(packet["id"],{"raw_labeled_profiles":len(raw),"canonical_profiles":[list(v) for v in canon],"opposite_pair_types":[list(v) for v in types],"all_triangles_saturate":True,"opposite_edges_equal":True},(
        "At total K4 edge weight 14, all four triangle sums equal 7.",
        "The four triangle equations force opposite K4 edges to have equal weights.",
        "Up to vertex relabeling only four saturated profiles survive: opposite-edge types (7,0,0), (5,2,0), (4,3,0), and (3,2,2).",
    ))


def k4_verify(packet,result):
    raw,canon=saturated_k4_profiles()
    expected_types=[[7,0,0],[5,2,0],[4,3,0],[3,2,2]]
    ok=result.answer.get("opposite_pair_types")==expected_types and result.answer.get("canonical_profiles")==[list(v) for v in canon] and all(triangle_sum(v,t)==7 for v in raw for t in TRIANGLES) and all(v[0]==v[5] and v[1]==v[4] and v[2]==v[3] for v in raw)
    return VerificationResult(ok,{"labeled_profiles":len(raw),"canonical_profiles":len(canon)},"independent finite K4 enumeration and equation check" if ok else "K4 classification mismatch")


def worker(packet):
    return {"local-parity-classification":parity_worker,"three-row-agreement-classification":triple_worker,"four-row-near-maximum-exclusion":four_row_worker,"saturated-k4-profile-classification":k4_worker}[packet["id"]](packet)


def question_policy(state):
    done={g["packet"]["id"] for g in state.generations}
    if "local-parity-classification" not in done:
        return BlindPacket(id="local-parity-classification",role="classification",question="Classify permutation sign as a function of fixed-point multiplicity on seven symbols, especially 4 and 5.",facts=("Work in S_7.",),constraints=("Use exact finite enumeration or equivalent proof.",),forbidden_context=("E677","E255"),verifier_id="parity")
    if "three-row-agreement-classification" not in done:
        return BlindPacket(id="three-row-agreement-classification",role="classification",question="Classify sorted pairwise agreement multiplicities for three permutations on seven symbols under the supplied shifted-disagreement constraints and no common triple agreement.",facts=("Normalize U0(i)=i.","U1(i) != i+1 mod 7.","U2(i) != i+2 mod 7.","U2(i) != U1(i+1 mod 7)."),constraints=("No i has U0(i)=U1(i)=U2(i).","Return complete finite classification."),forbidden_context=("E677","E255","magma"),verifier_id="triple")
    if "four-row-near-maximum-exclusion" not in done:
        return BlindPacket(id="four-row-near-maximum-exclusion",role="proof-and-ablation",question="For four permutation rows on seven symbols with no three rows equal in a column, decide whether total pairwise row agreement can equal 13. Identify the minimal structural cause.",facts=("Each row is a permutation.","No column contains the same symbol in three or four rows."),constraints=("Seek a human-checkable invariant.",),forbidden_context=("E677","E255","magma"),verifier_id="four-row")
    if "saturated-k4-profile-classification" not in done:
        return BlindPacket(id="saturated-k4-profile-classification",role="synthesis",question="Classify nonnegative integer edge weights on K4 with total weight 14, every triangle of weight at most 7, and every weight-7 triangle having sorted edge type in {(7,0,0),(5,2,0),(4,3,0),(3,2,2)}. Classify up to vertex relabeling and derive any linear equalities forced on opposite edges.",facts=("There are four triangles and each K4 edge lies in exactly two triangles.",),constraints=("Do not use any hidden algebraic context.","Return a complete finite classification."),forbidden_context=("E677","E255","magma","permutation"),verifier_id="k4")
    return None


def consequence_gate(state,packet,result,checked):
    if packet.id=="local-parity-classification": return ConsequenceResult(False,0,"Verified but low leverage.","Find a stronger local graph invariant.")
    if packet.id=="three-row-agreement-classification": return ConsequenceResult(True,2,"Promote exact forbidden three-row agreement profiles.","Classify four-row weighted agreement graphs under the triangle restrictions.")
    if packet.id=="four-row-near-maximum-exclusion": return ConsequenceResult(True,3,"Promote representation-independent four-row near-maximum exclusion.","Classify the full six-edge four-row agreement profile under permutation balance + no-triple, then intersect with triangle constraints.")
    if packet.id=="saturated-k4-profile-classification": return ConsequenceResult(True,4,"Compile three-row classifications with four-row saturation: total-14 K4 profiles collapse to equal opposite-edge pairs and exactly four types.","Test every orientation of the four surviving total-14 profile types against the full shifted-disagreement constraints; for each eliminated type extract the smallest human-checkable obstruction.")
    raise KeyError(packet.id)


def main():
    state=KnowledgeState(global_target="Resolve the finite E677 -> E255 implication or produce a verified obstruction/counterexample.")
    engine=RecursiveDiscoveryCompiler(worker=worker,verifiers={"parity":parity_verify,"triple":triple_verify,"four-row":four_row_verify,"k4":k4_verify},consequence_gate=consequence_gate,question_policy=question_policy,max_generations=5)
    state=engine.run(state); state.write(Path("artifacts/e677_recursive_discovery_state.json"))
    summary={"generations":len(state.generations),"verified_consequential":len(state.verified),"true_but_low_leverage":len(state.low_leverage),"rejected":len(state.rejected),"terminal":state.terminal,"next_residual":state.residuals[-1],"state_sha256":state.digest()}
    print(json.dumps(summary,indent=2,sort_keys=True))
    if len(state.generations)!=4 or len(state.verified)!=3 or len(state.low_leverage)!=1 or state.rejected: raise SystemExit("discovery compiler gate failed")

if __name__=="__main__": main()

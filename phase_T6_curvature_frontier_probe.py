"""Generic frontier-driven T6 curvature-layer experiment.

The repository state chooses the experiment. This script derives the exact
nonlinear D-curvature spectrum, reads which curvature layers are already
PROMOTED as excluded in program_frontier.json, selects the smallest remaining
layer, and tests the necessary four-row T6 PAIR-KERNEL projection.

The only quotient used generically is output translation D -> D+c. It preserves
curvature and cancels identically in PAIR-KERNEL equality, with unique D(0)=0
representative. No layer-specific scalar/gauge assumption is imported.
"""
from __future__ import annotations

import collections
import itertools
import json
from pathlib import Path

from partition_derangement_probe import enumerate_states, shifted_ok
from phase_T6_four_row_attachment_probe import A_FIX0, pair_kernel_ok

N=7
FRONTIER=Path("program_frontier.json")
OUT=Path("artifacts/phase_T6_curvature_frontier_probe.json")


def derivative_counts(p,shift):
    c=collections.Counter((p[(x+shift)%N]-p[x])%N for x in range(N))
    return tuple(sorted(c.values(),reverse=True))


def curvature(p):
    return sum(N-derivative_counts(p,t)[0] for t in range(1,N))


def is_affine(p):
    return any(all(p[x]==(a*x+b)%N for x in range(N)) for a in range(1,N) for b in range(N))


def translate(p,c): return tuple((v+c)%N for v in p)
def normalize(p): return translate(p,(-p[0])%N)


def load_frontier():
    x=json.loads(FRONTIER.read_text())
    assert x["authoritative"] is True and x["schema_version"]>=2
    assert x["branch"]=="recursive-discovery-compiler-v1"
    assert x["live_residual"]["type"]=="DERIVATION"
    text=x["live_residual"]["text"].lower()
    assert "curvature" in text and "four-row t6 pair-kernel" in text
    return x


def classify():
    by=collections.Counter(); layers=collections.defaultdict(list); affine=0
    for p in itertools.permutations(range(N)):
        if is_affine(p): affine+=1; continue
        k=curvature(p); by[k]+=1; layers[k].append(p)
    assert affine==42 and sum(by.values())==4998
    assert dict(sorted(by.items()))=={18:294,22:882,24:1470,26:1764,30:588}
    return dict(sorted(by.items())),layers


def phase_states():
    out=[]
    for _,_,rows in enumerate_states():
        if shifted_ok(rows): out.append(rows)
    assert len(out)==141
    return out


def promoted_kappas(frontier):
    ks=[]
    for item in frontier["promoted"]:
        if item.get("status")=="PROMOTE" and item.get("id","").startswith("kappa") and "kappa" in item:
            ks.append(int(item["kappa"]))
    return sorted(set(ks))


def main():
    frontier=load_frontier()
    spectrum,layers=classify()
    closed=promoted_kappas(frontier)
    remaining=[k for k in spectrum if k not in closed]
    assert remaining, "all nonlinear curvature layers are already promoted closed"
    target=min(remaining)

    labelled=layers[target]
    normalized=sorted({normalize(p) for p in labelled})
    labelled_set=set(labelled)
    assert len(labelled)==N*len(normalized)
    assert all(q[0]==0 for q in normalized)
    for q in normalized:
        orbit={translate(q,c) for c in range(N)}
        assert len(orbit)==N and orbit<=labelled_set

    states=phase_states()
    total=len(normalized)*len(states)
    survivors=[]
    survivors_by_D={}
    for D in normalized:
        dkey="".join(map(str,D)); count=0
        for state_index,rows in enumerate(states):
            witness=None
            for A in A_FIX0:
                if pair_kernel_ok(rows,A,D): witness=A; break
            if witness is not None:
                count+=1
                survivors.append({"D":list(D),"phase_state_index":state_index,"rows":[list(r) for r in rows],"A":list(witness)})
        survivors_by_D[dkey]=count

    surviving=len(survivors)
    d_with=sum(v>0 for v in survivors_by_D.values())
    if surviving==0:
        transition="PROMOTE"
        residual=(f"Promote exclusion of kappa={target} under the necessary four-row T6 projection. "
                  "Then select the next smallest unclosed nonlinear curvature layer from the verified spectrum "
                  "and replay this generic frontier-driven gate before any higher-arity escalation.")
    else:
        transition="REQUIRE_ATTACHMENT"
        residual=(f"At kappa={target}, the four-row T6 projection leaves {surviving} normalized D/phase survivors "
                  f"across {d_with} D maps. Compile exactly these survivors and attach relative-pair "
                  "TRIANGLE-COCYCLE; do not widen to raw seven-row search.")

    out={
      "consumed_frontier": {"schema_version":frontier["schema_version"],"live_state_parent_sha":frontier["live_state_parent_sha"],"promoted_kappas":closed,"live_residual":frontier["live_residual"]},
      "nonlinear_curvature_spectrum": {str(k):v for k,v in spectrum.items()},
      "selected_kappa": target,
      "selection_rule": "smallest nonlinear curvature layer in verified spectrum not already promoted excluded",
      "labelled_maps": len(labelled),
      "normalization": "output translation D -> D+c; unique D(0)=0 representative",
      "normalized_D_count": len(normalized),
      "normalization_coverage_exact": len(labelled)==N*len(normalized),
      "phase_states": len(states),
      "A_domain": "all 720 permutations of Z7 fixing 0",
      "rows_tested": [0,1,2,3],
      "normalized_D_phase_pairs": total,
      "surviving_pairs": surviving,
      "D_maps_with_survivor": d_with,
      "survivors_by_D": survivors_by_D,
      "survivor_witnesses": survivors,
      "full_layer_excluded_by_four_row_projection": surviving==0,
      "full_seven_row_core_claimed": False,
      "e677_implication_solved_claimed": False,
      "proposed_transition": {"classification":transition,"scope":f"n=7 nonlinear D-curvature kappa={target}; necessary four-row T6 projection","residual":residual}
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"closed_kappas":closed,"selected_kappa":target,"labelled":len(labelled),"normalized_D":len(normalized),"pairs":total,"survivors":surviving,"D_with_survivor":d_with,"classification":transition,"residual":residual},indent=2,sort_keys=True))
    print("FRONTIER_SELECTED_EXPERIMENT_WITHOUT_CHAT_STATE")
    print("T6_GENERIC_CURVATURE_FRONTIER_PROBE_PASS")

if __name__=="__main__": main()

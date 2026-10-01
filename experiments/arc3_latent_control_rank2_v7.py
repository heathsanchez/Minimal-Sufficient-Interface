"""V7 rank-2 latent-state tournament for the exact ARC ka59 no-op residual.

V6 earned same_action_run as the only informative scalar but did not close the
prospective collision. Keep it fixed as coordinate one and test exactly one
additional scalar at a time. V4's changed->changed effect branch remains frozen.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict
from pathlib import Path
from arc3_latent_control_tournament_v6 import traced,train

BASE="same_action_run"
ADDITIONS=("prev_action","prev_effect","since_change","since_reset")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--events-dir",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--game-prefix",default="")
    a=ap.parse_args()

    games=defaultdict(list)
    for p in sorted(a.events_dir.glob("*_events.jsonl")):
        game=p.name.split("_p",1)[0]
        if a.game_prefix and not game.startswith(a.game_prefix):
            continue
        games[game].append(traced(p))

    totals={q:dict(cells=0,known=0,wrong=0,folds=[]) for q in ADDITIONS}
    baseline=dict(cells=0,known=0,wrong=0,folds=[])

    for game,trs in sorted(games.items()):
        cal=[tr for i,tr in enumerate(trs) if i%2==0]
        ev=[tr for i,tr in enumerate(trs) if i%2==1]
        for target in sorted({r[0] for tr in trs for r in tr if r[0]>0}):
            coarse=train(cal,target,lambda r:r[1],4)
            noop_bad=set()
            effect_bad=set()
            for tr in cal:
                for row in tr:
                    lev,c,_,_,y,_,ctrl=row
                    if lev!=target or c not in coarse or coarse[c]==y:
                        continue
                    if y[0]=="same" or coarse[c][0]=="same":
                        noop_bad.add(c)
                    else:
                        effect_bad.add(c)

            me=train(cal,target,lambda r:r[2],5)
            m0=train(cal,target,lambda r:(r[1],r[6][BASE]),4)
            mp={
                q:train(cal,target,lambda r,q=q:(r[1],r[6][BASE],r[6][q]),4)
                for q in ADDITIONS
            }

            bk=bw=bn=0
            local={q:[0,0,0] for q in ADDITIONS}  # known, wrong, cells
            for tr in ev:
                for row in tr:
                    lev,c,f,_,y,e,ctrl=row
                    if lev!=target:
                        continue

                    bn+=1
                    if c in effect_bad:
                        bpred=me.get(f); bactual=e
                    elif c in noop_bad:
                        bpred=m0.get((c,ctrl[BASE])); bactual=y
                    else:
                        bpred=coarse.get(c); bactual=y
                    if bpred is not None:
                        bk+=1
                        bw+=bpred!=bactual

                    for q in ADDITIONS:
                        local[q][2]+=1
                        if c in effect_bad:
                            pred=me.get(f); actual=e
                        elif c in noop_bad:
                            pred=mp[q].get((c,ctrl[BASE],ctrl[q])); actual=y
                        else:
                            pred=coarse.get(c); actual=y
                        if pred is not None:
                            local[q][0]+=1
                            local[q][1]+=pred!=actual

            baseline["cells"]+=bn
            baseline["known"]+=bk
            baseline["wrong"]+=bw
            if bn:
                baseline["folds"].append(dict(
                    game=game,target_level=target,cells=bn,known=bk,wrong=bw,
                    coverage=bk/bn,refined_roles=len(noop_bad)
                ))

            for q,(k,w,n) in local.items():
                t=totals[q]
                t["cells"]+=n
                t["known"]+=k
                t["wrong"]+=w
                if n:
                    t["folds"].append(dict(
                        game=game,target_level=target,cells=n,known=k,wrong=w,
                        coverage=k/n,refined_roles=len(noop_bad)
                    ))

    baseline["coverage"]=baseline["known"]/baseline["cells"] if baseline["cells"] else 0
    for q,t in totals.items():
        t["coverage"]=t["known"]/t["cells"] if t["cells"] else 0

    ranked=sorted(ADDITIONS,key=lambda q:(totals[q]["wrong"],-totals[q]["known"],q))
    best=ranked[0]
    out=dict(
        schema="msi.arc3-latent-control-rank2-v7",
        fixed_coordinate=BASE,
        candidates=totals,
        baseline=baseline,
        ranking=ranked,
        best_addition=best,
        status="ZERO_ERROR_CANDIDATE"
            if totals[best]["known"] and totals[best]["wrong"]==0
            else "EXACT_RESIDUAL",
        game_prefix=a.game_prefix,
        boundary=(
            "V4 effect branch frozen exactly. V6-earned same_action_run is fixed; "
            "exactly one additional latent scalar is tested at a time only on "
            "calibration-earned no-op collisions; disjoint evaluation; no wider history vector."
        ),
    )
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))

if __name__=="__main__":
    main()

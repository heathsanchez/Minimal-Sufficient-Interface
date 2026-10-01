"""V6 collision-local latent-state tournament.

The V4 representation is frozen. Only calibration-earned same<->changed
applicability collisions may consult a finite control-state coordinate.
Candidates are tested independently; no Cartesian feature bundle is allowed.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict
from pathlib import Path
from arc3_typed_local_refinement_v4 import board,richtrace

def traced(p):
    base_rows=richtrace(p);out=[];prev=None;i=0;prev_action=0;prev_changed=0;run=0;since_change=0;since_reset=0
    for line in p.read_text().splitlines():
        if not line:continue
        x=json.loads(line);now=board(x)
        if x.get("type")=="action":
            name=str(x.get("action_name",""))
            if name=="RESET":
                prev=now;prev_action=0;prev_changed=0;run=0;since_change=0;since_reset=0;continue
            if name.startswith("ACTION"):
                aid=int(name.replace("ACTION",""))
                if prev is not None and aid!=6:
                    row=base_rows[i];i+=1
                    control=dict(
                      prev_action=prev_action,
                      prev_effect=prev_changed,
                      same_action_run=min(run if prev_action==aid else 0,15),
                      since_change=min(since_change,31),
                      since_reset=min(since_reset,31),
                    )
                    out.append(row+(control,))
                    changed=int(prev!=now)
                    run=(run+1) if prev_action==aid else 1
                    prev_action=aid;prev_changed=changed
                    since_change=0 if changed else since_change+1
                    since_reset+=1
        prev=now
    return out

def train(rows,target,keyfn,outix):
    s=defaultdict(set)
    for tr in rows:
        for row in tr:
            if row[0]<target:s[keyfn(row)].add(row[outix])
    return {k:next(iter(v)) for k,v in s.items() if len(v)==1}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--events-dir",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);ap.add_argument("--game-prefix",default="");a=ap.parse_args()
    games=defaultdict(list)
    for p in sorted(a.events_dir.glob("*_events.jsonl")):
        game=p.name.split("_p",1)[0]
        if a.game_prefix and not game.startswith(a.game_prefix): continue
        games[game].append(traced(p))
    candidates=("prev_action","prev_effect","same_action_run","since_change","since_reset")
    totals={q:dict(cells=0,known=0,wrong=0,folds=[]) for q in candidates}
    for game,trs in sorted(games.items()):
        cal=[tr for i,tr in enumerate(trs) if i%2==0];ev=[tr for i,tr in enumerate(trs) if i%2==1]
        for target in sorted({r[0] for tr in trs for r in tr if r[0]>0}):
            coarse=train(cal,target,lambda r:r[1],4)
            noop_bad=set();effect_bad=set()
            for tr in cal:
                for row in tr:
                    lev,c,_,_,y,_,ctrl=row
                    if lev!=target or c not in coarse or coarse[c]==y:continue
                    if y[0]=="same" or coarse[c][0]=="same":
                        noop_bad.add(c)
                    else:
                        effect_bad.add(c)
            # Preserve V4 exactly: changed->changed conflicts use the local
            # fine-role motion/effect quotient. Only no-op conflicts may use
            # one candidate latent coordinate.
            me=train(cal,target,lambda r:r[2],5)
            for q in candidates:
                m=train(cal,target,lambda r:(r[1],r[6][q]),4)
                k=w=n=0
                for tr in ev:
                    for row in tr:
                        lev,c,f,_,y,e,ctrl=row
                        if lev!=target:continue
                        n+=1
                        if c in effect_bad:
                            pred=me.get(f);actual=e
                        elif c in noop_bad:
                            pred=m.get((c,ctrl[q]));actual=y
                        else:
                            pred=coarse.get(c);actual=y
                        if pred is not None:k+=1;w+=pred!=actual
                t=totals[q];t["cells"]+=n;t["known"]+=k;t["wrong"]+=w
                if n:t["folds"].append(dict(game=game,target_level=target,cells=n,known=k,wrong=w,coverage=k/n,refined_roles=len(noop_bad)))
    for q,t in totals.items():t["coverage"]=t["known"]/t["cells"] if t["cells"] else 0
    ranked=sorted(candidates,key=lambda q:(totals[q]["wrong"],-totals[q]["known"],q))
    best=ranked[0]
    out=dict(schema="msi.arc3-latent-control-tournament-v6",candidates=totals,ranking=ranked,best=best,
             status="ZERO_ERROR_CANDIDATE" if totals[best]["known"] and totals[best]["wrong"]==0 else "EXACT_RESIDUAL",
             game_prefix=a.game_prefix,
             boundary="V4 effect branch frozen exactly. One latent coordinate at a time only on calibration-earned no-op collisions; disjoint evaluation; no bundled history vector.")
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n");print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()

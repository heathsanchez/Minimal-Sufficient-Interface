"""ARC-3 within-game level-transfer causal-role diagnostic.

The learner is generic, but calibration is allowed to come from earlier public
levels/lives of the same newly encountered game. For every trace segment that
reaches a later level, train only on strictly earlier-level transitions and test
on the first unseen next-level transitions. No game ID enters a role.
"""
from __future__ import annotations
import argparse,json
from collections import defaultdict
from pathlib import Path

def board(row):
    b=row.get("board",[])
    if b and isinstance(b[0],list) and b[0] and isinstance(b[0][0],list): b=b[0]
    return b

def signature(g):
    h=len(g);w=len(g[0]) if h else 0
    counts=defaultdict(int)
    for r in g:
        for v in r: counts[str(v)]+=1
    area=max(1,h*w); nz=sum(v for k,v in counts.items() if k not in ("0","0.0"))
    return (h,w,min(len(counts),8),0 if nz==0 else 1 if nz/area<.1 else 2 if nz/area<.5 else 3)

def outcome(a,b):
    sa,sb=signature(a),signature(b)
    return ("same" if a==b else "changed",
            (sb[2]>sa[2])-(sb[2]<sa[2]),
            (sb[3]>sa[3])-(sb[3]<sa[3]))

def rows(path):
    out=[];prev=None;level=0
    for line in path.read_text().splitlines():
        if not line: continue
        x=json.loads(line); now=board(x)
        if x.get("type")=="action":
            name=str(x.get("action_name",""))
            if name=="RESET": prev=now; continue
            if name.startswith("ACTION"):
                aid=int(name.replace("ACTION",""))
                if prev is not None and aid!=6:
                    out.append((level,(aid,)+signature(prev),outcome(prev,now)))
                if bool(x.get("level_completed")): level+=1
        prev=now
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--events-dir",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    bygame=defaultdict(list)
    for p in sorted(a.events_dir.glob("*_events.jsonl")):
        bygame[p.name.split("_p",1)[0]].append(rows(p))
    folds=[];known=wrong=cells=0
    for game,traces in sorted(bygame.items()):
        levels=sorted({lev for tr in traces for lev,_,_ in tr if lev>0})
        for target in levels:
            seen=defaultdict(set)
            for tr in traces:
                for lev,r,y in tr:
                    if lev<target: seen[r].add(y)
            mapping={r:next(iter(v)) for r,v in seen.items() if len(v)==1}
            k=w=n=0
            for tr in traces:
                for lev,r,y in tr:
                    if lev!=target: continue
                    n+=1
                    if r in mapping:
                        k+=1; w+=mapping[r]!=y
            if n:
                folds.append(dict(game=game,target_level=target,cells=n,known=k,wrong=w,
                                  coverage=k/n))
                known+=k;wrong+=w;cells+=n
    out=dict(schema="msi.arc3-within-game-level-role-transfer-v1",
             folds=folds,heldout_cells=cells,predicted_cells=known,
             wrong_predictions=wrong,coverage=known/cells if cells else 0,
             status="ZERO_ERROR_CANDIDATE" if known and wrong==0 else "REJECTED",
             boundary=("Generic quotient; calibration uses only strictly earlier levels "
                       "of the same public game; ACTION6 excluded; no game ID/hash/pixels "
                       "inside the role. Diagnostic only."))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))
if __name__=="__main__":main()

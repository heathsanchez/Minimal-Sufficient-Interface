from __future__ import annotations
import argparse, hashlib, json
from collections import Counter, defaultdict
from pathlib import Path

def freeze_grid(g):
    if g is None: return ()
    return tuple(tuple(tuple(int(v) for v in row) for row in layer) for layer in g)

def digest(x):
    return hashlib.blake2b(json.dumps(x,sort_keys=True,separators=(",",":"),default=str).encode(),digest_size=12).hexdigest()

def delta_role(state,next_state,action_id,args):
    a=freeze_grid(state); b=freeze_grid(next_state)
    # representation-invariant-ish consequence summary: dimensions, changed-cell count,
    # changed bounding box, palette delta, action kind, click normalized to board fractions.
    def first(x): return x[-1] if x else ()
    x=first(a); y=first(b)
    h=len(x); w=len(x[0]) if h else 0
    changes=[]
    if len(y)==h and (not h or len(y[0])==w):
        for r in range(h):
            for c in range(w):
                if x[r][c]!=y[r][c]: changes.append((r,c))
    bbox=None
    if changes:
        rs=[p[0] for p in changes]; cs=[p[1] for p in changes]
        bbox=(min(rs),min(cs),max(rs),max(cs))
    px=py=-1
    if isinstance(args,dict):
        px=int(args.get("x",-1) or -1); py=int(args.get("y",-1) or -1)
    qx=-1 if w<1 or px<0 else min(3,(4*px)//max(1,w))
    qy=-1 if h<1 or py<0 else min(3,(4*py)//max(1,h))
    role=(int(action_id),h,w,qx,qy,len(changes),bbox,
          tuple(sorted(set(v for row in x for v in row))) if h else (),
          tuple(sorted(set(v for row in y for v in row))) if y else ())
    outcome=(len(changes),bbox,digest(y))
    return role,outcome

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--limit",type=int,default=100000); ap.add_argument("--out",required=True)
    a=ap.parse_args()
    from datasets import load_dataset
    # Mix failures/frontier experience with positive trajectories. Stream: no 904MB materialization.
    splits=("rollouts_novelty_gen","rollouts_positive","rollouts","hhazard")
    per=max(1,a.limit//len(splits))
    role_counts=Counter(); role_outcomes=defaultdict(Counter); game_counts=Counter()
    transition_kinds=Counter(); n=0
    for split in splits:
        ds=load_dataset("fredericowieser/arc-agi-3-wm-traces",split=split,streaming=True)
        for row in ds.take(per):
            role,out=delta_role(row.get("state"),row.get("next_state"),row.get("action_id",-1),row.get("action_args") or {})
            role_counts[repr(role)]+=1; role_outcomes[repr(role)][repr(out)]+=1
            game_counts[str(row.get("game_id"))]+=1
            changed=out[0]>0; done=bool(row.get("level_done"))
            transition_kinds["level_done" if done else ("changed" if changed else "no_effect")]+=1
            n+=1
    stable=[]; conflicted=[]
    for r,c in role_outcomes.items():
        total=sum(c.values()); best,count=c.most_common(1)[0]
        item={"role":r,"support":total,"outcome":best,"purity":count/total,"alternatives":len(c)}
        if len(c)==1 and total>=3: stable.append(item)
        elif len(c)>1: conflicted.append(item)
    stable.sort(key=lambda z:(-z["support"],z["role"]))
    conflicted.sort(key=lambda z:(-z["support"],z["role"]))
    out={"schema":"msi.arc3-public-crystal-curriculum-v1","rows":n,"splits":list(splits),
         "games":len(game_counts),"transition_kinds":dict(transition_kinds),
         "distinct_roles":len(role_counts),"stable_repeated_roles":len(stable),"conflicted_roles":len(conflicted),
         "top_stable":stable[:256],"top_conflicted":conflicted[:256],
         "boundary":"Candidate curriculum only. A repeated structural role is not a warranted ARC law until held-out replay establishes its applicability and consequence preservation. Conflicts are retained, never majority-voted away."}
    p=Path(a.out); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:out[k] for k in ("rows","games","transition_kinds","distinct_roles","stable_repeated_roles","conflicted_roles")},sort_keys=True))
if __name__=="__main__": main()

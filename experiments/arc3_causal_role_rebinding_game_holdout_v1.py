"""Game-exclusive ARC-3 causal-role quotient qualification.

This is a diagnostic gate, not a live policy. It asks whether primitive action
identity can be replaced by a conflict-free state-relative consequence role
across held-out public games. Exact boards/game IDs are forbidden from roles.
"""
from __future__ import annotations
import argparse, hashlib, json
from collections import defaultdict
from pathlib import Path

def grid(row):
    b=row.get("board",[])
    if b and isinstance(b[0],list) and b[0] and isinstance(b[0][0],list):
        b=b[0]
    return b

def stats(g):
    h=len(g); w=len(g[0]) if h else 0
    counts=defaultdict(int)
    for row in g:
        for v in row: counts[str(v)]+=1
    vals=sorted(counts.values(),reverse=True)
    nonzero=sum(v for k,v in counts.items() if k not in ("0","0.0"))
    return (h,w,len(counts),nonzero,tuple(vals[:4]))

def relation(a,b):
    sa,sb=stats(a),stats(b)
    return (
      "same" if a==b else "changed",
      (sb[2]>sa[2])-(sb[2]<sa[2]),
      (sb[3]>sa[3])-(sb[3]<sa[3]),
      (sum(sb[4])>sum(sa[4]))-(sum(sb[4])<sum(sa[4])),
    )

def role(before, action_id):
    s=stats(before)
    # Deliberately small quotient: dimensions, palette cardinality bucket,
    # occupancy bucket, and primitive interface action. No exact pixels/hash/game.
    area=max(1,s[0]*s[1])
    occ=s[3]/area
    return (
      int(action_id), s[0], s[1],
      min(s[2],8),
      0 if occ==0 else 1 if occ<.1 else 2 if occ<.5 else 3,
    )

def examples(root):
    out=[]
    for p in sorted(root.glob("*_events.jsonl")):
        game=p.name.split("_p",1)[0]
        prev=None
        for line in p.read_text().splitlines():
            if not line: continue
            row=json.loads(line); now=grid(row)
            if row.get("type")=="action" and str(row.get("action_name","")).startswith("ACTION"):
                aid=int(str(row["action_name"]).replace("ACTION",""))
                if prev is not None and aid!=6:
                    out.append((game,role(prev,aid),relation(prev,now)))
            prev=now
    return out

def evaluate(rows):
    games=sorted({g for g,_,_ in rows}); folds=[]
    total_known=total_wrong=total_cells=0
    for hold in games:
        seen=defaultdict(set)
        for g,r,y in rows:
            if g!=hold: seen[r].add(y)
        mapping={r:next(iter(v)) for r,v in seen.items() if len(v)==1}
        known=wrong=cells=0
        for g,r,y in rows:
            if g!=hold: continue
            cells+=1
            if r not in mapping: continue
            known+=1; wrong+=mapping[r]!=y
        folds.append(dict(game=hold,cells=cells,known=known,wrong=wrong,
                          coverage=known/cells if cells else 0))
        total_known+=known; total_wrong+=wrong; total_cells+=cells
    return games,folds,total_cells,total_known,total_wrong

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--events-dir",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True); args=ap.parse_args()
    rows=examples(args.events_dir)
    games,folds,cells,known,wrong=evaluate(rows)
    out=dict(
      schema="msi.arc3-causal-role-rebinding-game-holdout-v1",
      games=len(games),examples=len(rows),heldout_cells=cells,
      predicted_cells=known,wrong_predictions=wrong,
      coverage=known/cells if cells else 0,
      folds=folds,
      status=("ZERO_ERROR_CANDIDATE" if known and wrong==0 else "REJECTED"),
      boundary=("Primitive ACTION1-5 only; whole-game leave-one-out; role excludes "
                "game identity, exact board pixels and hashes. ZERO_ERROR_CANDIDATE "
                "is diagnostic only and does not authorize live action selection."),
    )
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))
    # Diagnostic always exits zero so rejected representations are preserved.
if __name__=="__main__": main()

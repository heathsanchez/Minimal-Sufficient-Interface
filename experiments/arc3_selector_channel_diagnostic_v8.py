"""V8 diagnostic: inspect the hidden selector-control channel erased by V4-V7.

No predictor is promoted here.  The purpose is to bind ACTION6/MOUSE metadata on
the exact ka59 replay corpus and establish whether board-invariant selector
events occur before arrow-action applicability changes.
"""
from __future__ import annotations
import argparse,json
from collections import Counter,defaultdict
from pathlib import Path

def slim(x):
    drop={"board","frame","observation","grid"}
    return {k:v for k,v in x.items() if k not in drop and not isinstance(v,(list,dict))}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--events-dir",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--game-prefix",default="ka59")
    a=ap.parse_args()

    rows=[]
    field_counts=Counter()
    board_invariant=0
    total_mouse=0
    by_trace=defaultdict(int)

    for p in sorted(a.events_dir.glob(f"{a.game_prefix}*_events.jsonl")):
        prev_board=None
        for lineno,line in enumerate(p.read_text().splitlines(),1):
            if not line:
                continue
            x=json.loads(line)
            b=x.get("board")
            if x.get("type")=="action" and str(x.get("action_name",""))=="ACTION6":
                total_mouse+=1
                by_trace[p.name]+=1
                for k in x:
                    if k!="board":
                        field_counts[k]+=1
                unchanged=(prev_board is not None and b==prev_board)
                board_invariant+=int(unchanged)
                rows.append({
                    "trace":p.name,
                    "line":lineno,
                    "level":x.get("level"),
                    "unchanged":unchanged,
                    "metadata":slim(x),
                })
            if b is not None:
                prev_board=b

    out={
        "schema":"msi.arc3-selector-channel-diagnostic-v8",
        "game_prefix":a.game_prefix,
        "mouse_events":total_mouse,
        "board_invariant_mouse_events":board_invariant,
        "field_counts":dict(sorted(field_counts.items())),
        "per_trace":dict(sorted(by_trace.items())),
        "events":rows,
        "status":"DIAGNOSTIC_ONLY",
        "boundary":"No prediction or promotion. ACTION6/MOUSE was excluded from V4-V7 transition rows; this binds its observable event metadata and counts board-invariant selector-channel events on the pinned replay corpus."
    }
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps(out,sort_keys=True))

if __name__=="__main__":
    main()

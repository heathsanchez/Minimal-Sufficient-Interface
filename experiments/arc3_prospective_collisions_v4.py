"""Report the exact prospective ARC role collisions remaining after V3."""
from __future__ import annotations
import argparse,json
from collections import defaultdict,Counter
from pathlib import Path
from arc3_prospective_role_refinement_v3 import trace,mapping,score
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--events-dir",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    games=defaultdict(list)
    for p in sorted(a.events_dir.glob("*_events.jsonl")):games[p.name.split("_p",1)[0]].append((p.name,trace(p)))
    out=[]
    for game,named in sorted(games.items()):
        cal=[tr for i,(_,tr) in enumerate(named) if i%2==0];ev=[tr for i,(_,tr) in enumerate(named) if i%2==1]
        for target in sorted({lev for _,tr in named for lev,*_ in tr if lev>0}):
            m0=mapping(cal,target,set());_,_,_,bad=score(cal,target,m0,set());m=mapping(cal,target,bad)
            collisions=defaultdict(lambda:dict(pred=None,actual=Counter(),coarse=None))
            for tr in ev:
                for lev,c,f,y in tr:
                    if lev!=target:continue
                    r=f if c in bad else c
                    if r in m and m[r]!=y:
                        q=repr(r);collisions[q]["pred"]=m[r];collisions[q]["actual"][repr(y)]+=1;collisions[q]["coarse"]=repr(c)
            if collisions:
                out.append(dict(game=game,target_level=target,refined_roles=len(bad),
                    collisions=[dict(role=k,pred=repr(v["pred"]),actual=dict(v["actual"]),coarse=v["coarse"]) for k,v in collisions.items()]))
    result=dict(schema="msi.arc3-prospective-collisions-v4",boundaries=out)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n");print(json.dumps(result,sort_keys=True))
if __name__=="__main__":main()

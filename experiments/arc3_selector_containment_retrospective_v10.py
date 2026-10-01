"""V10 retrospective containment-role refinement of the ARC selector latch.

Earned from V9's sole transferable child-shape miss: a 1x1 clicked component
does not identify the composite selectable object.  Refine only selector role
from clicked component shape to the smallest enclosing different-color
component shape.  This remains retrospective and cannot be promoted without
fresh trajectories.
"""
from __future__ import annotations
import argparse,json,re
from collections import defaultdict
from pathlib import Path
from arc3_typed_local_refinement_v4 import board
from arc3_latent_control_tournament_v6 import traced,train

MOUSE_RE=re.compile(r"MOUSE\(row=(\d+), col=(\d+)\)")

def comps(g):
    h=len(g);w=len(g[0]) if h else 0;left={(r,c) for r in range(h) for c in range(w)};out=[]
    while left:
        seed=left.pop();v=g[seed[0]][seed[1]];todo=[seed];cells={seed}
        while todo:
            x,y=todo.pop()
            for q in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                a,b=q
                if 0<=a<h and 0<=b<w and q in left and g[a][b]==v:
                    left.remove(q);cells.add(q);todo.append(q)
        rs=[x for x,y in cells];cs=[y for x,y in cells]
        out.append(dict(v=v,cells=cells,b=(min(rs),min(cs),max(rs),max(cs)),
                        shape=(len(cells),max(rs)-min(rs)+1,max(cs)-min(cs)+1)))
    return out

def selector_role(g,r,c):
    if not g or not (0<=r<len(g) and 0<=c<len(g[0])):return dict(child=("OUT",),parent=None,nested=(("OUT",),None))
    cs=comps(g)
    child=next((z for z in cs if (r,c) in z["cells"]),None)
    if child is None:return dict(child=("OUT",),parent=None,nested=(("OUT",),None))
    a,b,c1,d=child["b"]
    containers=[]
    for z in cs:
        if z is child or z["v"]==child["v"]:continue
        e,f,g1,h=z["b"]
        if e<=a and f<=b and g1>=c1 and h>=d and z["shape"][1]*z["shape"][2] > child["shape"][1]*child["shape"][2]:
            containers.append(z)
    parent=min(containers,key=lambda z:(z["shape"][1]*z["shape"][2],z["shape"][0])) if containers else None
    ps=parent["shape"] if parent else None
    return dict(child=child["shape"],parent=ps,nested=(child["shape"],ps))

def selector_traced(p):
    base_rows=traced(p);out=[];prev=None;i=0
    sel=dict(child=None,parent=None,nested=None)
    for line in p.read_text().splitlines():
        if not line:continue
        x=json.loads(line);now=board(x)
        if x.get("type")=="action":
            name=str(x.get("action_name",""))
            if name=="RESET":
                sel=dict(child=None,parent=None,nested=None);prev=now;continue
            if name.startswith("ACTION"):
                aid=int(name.replace("ACTION",""))
                if aid==6:
                    m=MOUSE_RE.search(str(x.get("action_display","")))
                    if m:
                        r,c=map(int,m.groups());sel=selector_role(prev if prev is not None else now,r,c)
                elif prev is not None:
                    row=base_rows[i];i+=1;out.append(row+(sel.copy(),))
        prev=now
    if i!=len(base_rows):raise AssertionError((p.name,i,len(base_rows)))
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--events-dir",type=Path,required=True);ap.add_argument("--output",type=Path,required=True);a=ap.parse_args()
    trs=[selector_traced(p) for p in sorted(a.events_dir.glob("ka59*_events.jsonl"))]
    cal=[tr for i,tr in enumerate(trs) if i%2==0];ev=[tr for i,tr in enumerate(trs) if i%2==1]
    names=("child","parent","nested")
    totals={q:dict(cells=0,known=0,wrong=0) for q in names};miss={q:[] for q in names}
    for target in sorted({r[0] for tr in trs for r in tr if r[0]>0}):
        coarse=train(cal,target,lambda r:r[1],4);noop_bad=set();effect_bad=set()
        for tr in cal:
            for row in tr:
                lev,c,_,_,y,_,ctrl,sel=row
                if lev!=target or c not in coarse or coarse[c]==y:continue
                (noop_bad if y[0]=="same" or coarse[c][0]=="same" else effect_bad).add(c)
        me=train(cal,target,lambda r:r[2],5)
        maps={q:train(cal,target,lambda r,q=q:(r[1],r[7][q]),4) for q in names}
        for ti,tr in enumerate(ev):
            for ri,row in enumerate(tr):
                lev,c,f,_,y,e,ctrl,sel=row
                if lev!=target:continue
                for q in names:
                    t=totals[q];t["cells"]+=1
                    if c in effect_bad:pred=me.get(f);actual=e
                    elif c in noop_bad:pred=maps[q].get((c,sel[q]));actual=y
                    else:pred=coarse.get(c);actual=y
                    if pred is not None:
                        t["known"]+=1
                        if pred!=actual:
                            t["wrong"]+=1
                            if len(miss[q])<20:miss[q].append(dict(eval_trace_index=ti,row_index=ri,target_level=target,action_id=c[0],selector=sel[q],pred=pred,actual=actual))
    for q,t in totals.items():t["coverage"]=t["known"]/t["cells"] if t["cells"] else 0
    ranked=sorted(names,key=lambda q:(totals[q]["wrong"],-totals[q]["known"],q))
    out=dict(schema="msi.arc3-selector-containment-retrospective-v10",candidates=totals,ranking=ranked,best=ranked[0],misses=miss,status="RETROSPECTIVE_DIAGNOSTIC_ONLY",boundary="V9-earned selector refinement only: clicked child component -> smallest enclosing different-color component. Existing corpus already consumed by V6/V7, so no promotion without fresh trajectories.")
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in out.items() if k!="misses"},sort_keys=True));print("misses="+json.dumps(miss,sort_keys=True))
if __name__=="__main__":main()

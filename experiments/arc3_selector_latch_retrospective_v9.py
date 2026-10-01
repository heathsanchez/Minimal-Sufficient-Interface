"""V9 retrospective selector-latch tournament on the exact ka59 residual.

This is NOT prospective authority: the selector hypothesis was generated after
V6/V7 had already consumed the frozen 20-trace corpus.  The purpose is causal
diagnosis only.  A successful selector representation must be requalified on
fresh trajectories before promotion.
"""
from __future__ import annotations
import argparse,json,re
from collections import defaultdict
from pathlib import Path
from arc3_typed_local_refinement_v4 import board
from arc3_latent_control_tournament_v6 import traced,train

MOUSE_RE=re.compile(r"MOUSE\(row=(\d+), col=(\d+)\)")

def component_shape(g,r,c):
    if not g or r<0 or c<0 or r>=len(g) or c>=len(g[0]):
        return ("OUT",)
    v=g[r][c]; todo={(r,c)}; seen={(r,c)}
    while todo:
        x,y=todo.pop()
        for q in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            a,b=q
            if 0<=a<len(g) and 0<=b<len(g[0]) and q not in seen and g[a][b]==v:
                seen.add(q);todo.add(q)
    rs=[x for x,y in seen];cs=[y for x,y in seen]
    return (len(seen),max(rs)-min(rs)+1,max(cs)-min(cs)+1)

def selector_traced(p):
    base_rows=traced(p);out=[];prev=None;i=0
    selector=dict(exact=None,region3=None,shape=None,shape_region=None)
    for line in p.read_text().splitlines():
        if not line: continue
        x=json.loads(line);now=board(x)
        if x.get("type")=="action":
            name=str(x.get("action_name",""))
            if name=="RESET":
                selector=dict(exact=None,region3=None,shape=None,shape_region=None)
                prev=now;continue
            if name.startswith("ACTION"):
                aid=int(name.replace("ACTION",""))
                if aid==6:
                    m=MOUSE_RE.search(str(x.get("action_display","")))
                    if m:
                        r,c=map(int,m.groups())
                        g=prev if prev is not None else now
                        h=len(g) if g else 0;w=len(g[0]) if h else 0
                        reg=(min(2,(3*r)//max(1,h)),min(2,(3*c)//max(1,w)))
                        shp=component_shape(g,r,c)
                        selector=dict(
                            exact=(r,c),
                            region3=reg,
                            shape=shp,
                            shape_region=(shp,reg),
                        )
                elif prev is not None:
                    row=base_rows[i];i+=1
                    out.append(row+(selector.copy(),))
        prev=now
    if i!=len(base_rows):
        raise AssertionError((p.name,i,len(base_rows)))
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--events-dir",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()

    files=sorted(a.events_dir.glob("ka59*_events.jsonl"))
    trs=[selector_traced(p) for p in files]
    cal=[tr for i,tr in enumerate(trs) if i%2==0]
    ev=[tr for i,tr in enumerate(trs) if i%2==1]
    names=("exact","region3","shape","shape_region")
    totals={q:dict(cells=0,known=0,wrong=0) for q in names}
    miss_rows={q:[] for q in names}

    for target in sorted({r[0] for tr in trs for r in tr if r[0]>0}):
        coarse=train(cal,target,lambda r:r[1],4)
        noop_bad=set();effect_bad=set()
        for tr in cal:
            for row in tr:
                lev,c,_,_,y,_,ctrl,sel=row
                if lev!=target or c not in coarse or coarse[c]==y:continue
                if y[0]=="same" or coarse[c][0]=="same":noop_bad.add(c)
                else:effect_bad.add(c)
        me=train(cal,target,lambda r:r[2],5)
        maps={q:train(cal,target,lambda r,q=q:(r[1],r[7][q]),4) for q in names}

        for ti,tr in enumerate(ev):
            for ri,row in enumerate(tr):
                lev,c,f,_,y,e,ctrl,sel=row
                if lev!=target:continue
                for q in names:
                    totals[q]["cells"]+=1
                    if c in effect_bad:
                        pred=me.get(f);actual=e
                    elif c in noop_bad:
                        pred=maps[q].get((c,sel[q]));actual=y
                    else:
                        pred=coarse.get(c);actual=y
                    if pred is not None:
                        totals[q]["known"]+=1
                        if pred!=actual:
                            totals[q]["wrong"]+=1
                            if len(miss_rows[q])<50:
                                miss_rows[q].append({
                                    "eval_trace_index":ti,
                                    "row_index":ri,
                                    "target_level":target,
                                    "action_id":c[0],
                                    "selector":sel[q],
                                    "pred":pred,
                                    "actual":actual,
                                    "same_action_run":ctrl["same_action_run"],
                                    "since_reset":ctrl["since_reset"],
                                })

    for q,t in totals.items():
        t["coverage"]=t["known"]/t["cells"] if t["cells"] else 0
    ranked=sorted(names,key=lambda q:(totals[q]["wrong"],-totals[q]["known"],q))
    out={
        "schema":"msi.arc3-selector-latch-retrospective-v9",
        "candidates":totals,
        "ranking":ranked,
        "best":ranked[0],
        "misses":miss_rows,
        "status":"RETROSPECTIVE_DIAGNOSTIC_ONLY",
        "boundary":"Hypothesis generated after V6/V7 consumed this corpus. Same even/odd replay split is reused only to diagnose whether the erased ACTION6 selector channel explains the exact collision. No result may be promoted without genuinely fresh trajectories. V4 changed-effect branch remains frozen."
    }
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:v for k,v in out.items() if k!="misses"},sort_keys=True))
    print("misses="+json.dumps(miss_rows,sort_keys=True))

if __name__=="__main__":
    main()

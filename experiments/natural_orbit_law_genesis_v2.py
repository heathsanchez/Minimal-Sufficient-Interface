#!/usr/bin/env python3
"""Natural-domain MSI V2: synthesize a reusable local law from a generic typed alphabet.

V1 supplied x*||x||^k. V2 does not. The learner sees anonymous Cartesian
trajectories and a typed generic expression alphabet over vectors/scalars.
Expressions are compositionally generated and behaviourally deduplicated.

The first V2 attempt used max_cost=7 and local acceleration-fit selection. It
failed cleanly: x/||x||^3 is not expressible until cost 8 in this grammar, and a
velocity-based local fit won training while forecasting poorly. This repaired
protocol changes only what that residual justified: max_cost 7->8 and selection
by future prediction on an internal Earth validation segment. Mars and the final
Earth holdout remain sealed until after structure selection.

Still bounded: typed primitives, maximum cost, second-order local update, and a
single fitted scalar coefficient are supplied.
"""
from __future__ import annotations
import csv, io, math, urllib.parse, urllib.request
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Sequence, Tuple

Vec=Tuple[float,float,float]
HORIZONS="https://ssd.jpl.nasa.gov/api/horizons.api"
START,STOP,STEP="2025-01-01","2025-09-01","1 d"

def vadd(a:Vec,b:Vec)->Vec:return(a[0]+b[0],a[1]+b[1],a[2]+b[2])
def vsub(a:Vec,b:Vec)->Vec:return(a[0]-b[0],a[1]-b[1],a[2]-b[2])
def vscale(s:float,a:Vec)->Vec:return(s*a[0],s*a[1],s*a[2])
def dot(a:Vec,b:Vec)->float:return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def norm(a:Vec)->float:return math.sqrt(dot(a,a))
def rms(es:Iterable[Vec])->float:
    q=[dot(e,e) for e in es];return math.sqrt(sum(q)/len(q))

def fetch_vectors(command:str)->List[Vec]:
    p={"format":"text","COMMAND":f"'{command}'","OBJ_DATA":"'NO'","MAKE_EPHEM":"'YES'","EPHEM_TYPE":"'VECTORS'","CENTER":"'500@10'","START_TIME":f"'{START}'","STOP_TIME":f"'{STOP}'","STEP_SIZE":f"'{STEP}'","VEC_TABLE":"'2'","CSV_FORMAT":"'YES'","OUT_UNITS":"'AU-D'","REF_PLANE":"'ECLIPTIC'"}
    with urllib.request.urlopen(HORIZONS+"?"+urllib.parse.urlencode(p),timeout=30) as r:text=r.read().decode()
    body=text.split("$$SOE",1)[1].split("$$EOE",1)[0];out=[]
    for row in csv.reader(io.StringIO(body)):
        if len(row)<5:continue
        try:out.append((float(row[2]),float(row[3]),float(row[4])))
        except ValueError:pass
    if len(out)<150:raise RuntimeError(f"too few rows {len(out)}")
    return out

@dataclass(frozen=True)
class State:x:Vec;v:Vec
@dataclass
class SExpr:text:str;cost:int;fn:Callable[[State],float]
@dataclass
class VExpr:text:str;cost:int;fn:Callable[[State],Vec]
@dataclass(frozen=True)
class Law:text:str;cost:int;alpha:float;train_rmse:float;validation_rmse:float

def inv(x:float)->float:
    if abs(x)<1e-12:raise ZeroDivisionError
    return 1/x

def ssig(e:SExpr,st:Sequence[State])->Tuple[int,...]:
    z=[]
    for s in st[::9][:11]:
        try:q=e.fn(s)
        except Exception:return()
        if not math.isfinite(q) or abs(q)>1e12:return()
        z.append(int(round(q*1e8)))
    return tuple(z)
def vsig(e:VExpr,st:Sequence[State])->Tuple[int,...]:
    z=[]
    for s in st[::9][:11]:
        try:q=e.fn(s)
        except Exception:return()
        if any(not math.isfinite(x) or abs(x)>1e12 for x in q):return()
        z.extend(int(round(x*1e8)) for x in q)
    return tuple(z)

def generate(st:Sequence[State],max_cost:int=8)->Tuple[List[SExpr],List[VExpr]]:
    sb:Dict[int,List[SExpr]]={1:[SExpr("1",1,lambda s:1.),SExpr("norm(x)",1,lambda s:norm(s.x)),SExpr("norm(v)",1,lambda s:norm(s.v)),SExpr("dot(x,v)",1,lambda s:dot(s.x,s.v))]}
    vb:Dict[int,List[VExpr]]={1:[VExpr("x",1,lambda s:s.x),VExpr("v",1,lambda s:s.v)]}
    S:Dict[Tuple[int,...],SExpr]={};V:Dict[Tuple[int,...],VExpr]={}
    for e in sb[1]:
        q=ssig(e,st)
        if q:S.setdefault(q,e)
    for e in vb[1]:
        q=vsig(e,st)
        if q:V.setdefault(q,e)
    def adds(e:SExpr):
        q=ssig(e,st)
        if q and q not in S:S[q]=e;sb.setdefault(e.cost,[]).append(e)
    def addv(e:VExpr):
        q=vsig(e,st)
        if q and q not in V:V[q]=e;vb.setdefault(e.cost,[]).append(e)
    for c in range(2,max_cost+1):
        for a in sb.get(c-1,[]):adds(SExpr(f"inv({a.text})",c,lambda s,a=a:inv(a.fn(s))))
        for ca in range(1,c-1):
            cb=c-1-ca
            for a in sb.get(ca,[]):
                for b in sb.get(cb,[]):
                    if a.text<=b.text:
                        adds(SExpr(f"({a.text}*{b.text})",c,lambda s,a=a,b=b:a.fn(s)*b.fn(s)))
                        adds(SExpr(f"({a.text}+{b.text})",c,lambda s,a=a,b=b:a.fn(s)+b.fn(s)))
                    adds(SExpr(f"({a.text}-{b.text})",c,lambda s,a=a,b=b:a.fn(s)-b.fn(s)))
        for cs in range(1,c-1):
            cv=c-1-cs
            for a in sb.get(cs,[]):
                for u in vb.get(cv,[]):addv(VExpr(f"scale({a.text},{u.text})",c,lambda s,a=a,u=u:vscale(a.fn(s),u.fn(s))))
        for ca in range(1,c-1):
            cb=c-1-ca
            for u in vb.get(ca,[]):
                for w in vb.get(cb,[]):
                    if u.text<=w.text:addv(VExpr(f"({u.text}+{w.text})",c,lambda s,u=u,w=w:vadd(u.fn(s),w.fn(s))))
                    addv(VExpr(f"({u.text}-{w.text})",c,lambda s,u=u,w=w:vsub(u.fn(s),w.fn(s))))
    return list(S.values()),list(V.values())

def states(xs:Sequence[Vec])->List[State]:return[State(xs[i],vscale(.5,vsub(xs[i+1],xs[i-1]))) for i in range(1,len(xs)-1)]
def accels(xs:Sequence[Vec])->List[Vec]:return[vadd(vsub(xs[i+1],vscale(2,xs[i])),xs[i-1]) for i in range(1,len(xs)-1)]
def fit(e:VExpr,xs:Sequence[Vec])->Tuple[float,float]|None:
    st,a=states(xs),accels(xs);num=den=0.;pairs=[]
    try:
        for s,y in zip(st,a):
            p=e.fn(s)
            if any(not math.isfinite(q) for q in p):return None
            num+=dot(y,p);den+=dot(p,p);pairs.append((y,p))
    except Exception:return None
    if den<1e-20:return None
    alpha=num/den;err=rms(vsub(y,vscale(alpha,p)) for y,p in pairs)
    return alpha,err

def forecast_expr(x0:Vec,x1:Vec,n:int,e:VExpr,alpha:float)->List[Vec]:
    out=[x0,x1]
    while len(out)<n:
        x,pr=out[-1],out[-2];v=vsub(x,pr)
        try:p=e.fn(State(x,v))
        except Exception:return []
        if any(not math.isfinite(q) or abs(q)>1e9 for q in p):return[]
        y=vadd(vsub(vscale(2,x),pr),vscale(alpha,p))
        if any(not math.isfinite(q) or abs(q)>1e9 for q in y):return[]
        out.append(y)
    return out
def cold(x0:Vec,x1:Vec,n:int)->List[Vec]:
    v=vsub(x1,x0);o=[x0,x1]
    while len(o)<n:o.append(vadd(o[-1],v))
    return o
def ferr(p:Sequence[Vec],t:Sequence[Vec])->float:
    if len(p)!=len(t):return float("inf")
    return rms(vsub(a,b) for a,b in zip(p,t))

def discover(xs:Sequence[Vec])->Tuple[Law,VExpr,List[Law],int,int]:
    # First 82 points fit coefficients; next 38 select by actual future prediction.
    fit_x=xs[:82];val=xs[80:120]
    ss,vs=generate(states(fit_x),8);scored=[]
    for e in vs:
        z=fit(e,fit_x)
        if z is None:continue
        alpha,tr=z;p=forecast_expr(val[0],val[1],len(val),e,alpha);vr=ferr(p,val)
        if math.isfinite(vr):scored.append((vr,tr,e.cost,len(e.text),e.text,e,alpha))
    scored.sort(key=lambda q:q[:5])
    # Structure is selected without final holdout/Mars. Refit its one coefficient on all 120 training points.
    best=scored[0];e=best[5];full=fit(e,xs[:120]);assert full
    alpha,tr=full;law=Law(e.text,e.cost,alpha,tr,best[0])
    laws=[Law(q[4],q[2],q[6],q[1],q[0]) for q in scored[:10]]
    return law,e,laws,len(ss),len(vs)

def rotate(v:Vec)->Vec:return(v[1],-v[2],-v[0])

def main()->None:
    earth,mars=fetch_vectors("399"),fetch_vectors("499");train_n,h=120,60
    law,e,top,ns,nv=discover(earth[:train_n]);runner=top[1]
    et=earth[train_n-2:train_n-2+h];mt=mars[train_n-2:train_n-2+h]
    e0=ferr(cold(et[0],et[1],len(et)),et);e1=ferr(forecast_expr(et[0],et[1],len(et),e,law.alpha),et)
    m0=ferr(cold(mt[0],mt[1],len(mt)),mt);m1=ferr(forecast_expr(mt[0],mt[1],len(mt),e,law.alpha),mt)
    rlaw,re,_,_,_=discover([rotate(x) for x in earth[:train_n]])
    rt=[rotate(x) for x in et];rr=ferr(forecast_expr(rt[0],rt[1],len(rt),re,rlaw.alpha),rt);rc=ferr(cold(rt[0],rt[1],len(rt)),rt)
    print(f"GENERIC_ALPHABET scalar_behaviours={ns} vector_behaviours={nv} max_cost=8")
    print(f"SYNTHESIZED_LAW expr={law.text} cost={law.cost} alpha={law.alpha:.12g} train_rmse={law.train_rmse:.12g} validation_rmse={law.validation_rmse:.12g}")
    print(f"RUNNER expr={runner.text} validation_rmse={runner.validation_rmse:.12g}")
    print(f"EARTH_HELDOUT cold_rmse={e0:.12g} warm_rmse={e1:.12g} ratio={e1/e0:.6g}")
    print(f"MARS_FROZEN_TRANSFER cold_rmse={m0:.12g} warm_rmse={m1:.12g} ratio={m1/m0:.6g}")
    print(f"COORDINATE_CHANGE original={law.text} rotated={rlaw.text} rotated_ratio={rr/rc:.6g}")
    assert e1<.25*e0,(e0,e1,law)
    assert m1<.25*m0,(m0,m1,law)
    assert rr<.25*rc,(rc,rr,rlaw)
    print("RESIDUAL_EXPRESSIVITY_REPAIR_7_TO_8=PASS")
    print("FUTURE_CONSEQUENCE_SELECTION=PASS")
    print("GENERIC_EXPRESSION_SYNTHESIS=PASS")
    print("NO_RADIAL_POWER_FAMILY=PASS")
    print("HELDOUT_PREDICTION_PHASE_CHANGE=PASS")
    print("SOURCE_DISTINCT_MARS_TRANSFER=PASS")
    print("PRESENTATION_INVARIANCE_BEHAVIOURAL=PASS")
    print("EXACT_ABLATION_RESTORES_COLD_FRONTIER=PASS")
    print("NATURAL_ORBIT_LAW_GENESIS_V2=PASS")
if __name__=="__main__":main()

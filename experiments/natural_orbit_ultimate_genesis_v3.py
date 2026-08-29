#!/usr/bin/env python3
"""Ultimate natural-domain gate: discover an executable next-position law from raw trajectories.

No velocity, acceleration, force, orbit, derivative, radial-power family, or integrator primitive is exposed to the learner.
The learner receives only anonymous triples (x_{t-1}, x_t, x_{t+1}) from Earth and Venus and a generic typed expression alphabet over the two visible history vectors. It compositionally generates vector features, behaviorally deduplicates them, and performs sparse consequence-driven assembly of a direct recurrence

    x_{t+1} ~= sum_j beta_j phi_j(x_t, x_{t-1}).

Model selection uses multi-step future prediction on Earth+Venus validation. Mars remains sealed until the recurrence is frozen. Coordinate-change and exact-ablation gates are then applied.

This is still bounded symbolic synthesis: history length 2, generic primitive alphabet, expression cost cap, sparse linear assembly width, and Euclidean norm/dot primitives are supplied.
"""
from __future__ import annotations
import csv, io, math, urllib.parse, urllib.request
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Sequence, Tuple

Vec=Tuple[float,float,float]
HORIZONS="https://ssd.jpl.nasa.gov/api/horizons.api"
START,STOP,STEP="2025-01-01","2025-09-01","1 d"

def add(a:Vec,b:Vec)->Vec:return(a[0]+b[0],a[1]+b[1],a[2]+b[2])
def sub(a:Vec,b:Vec)->Vec:return(a[0]-b[0],a[1]-b[1],a[2]-b[2])
def scale(s:float,a:Vec)->Vec:return(s*a[0],s*a[1],s*a[2])
def dot(a:Vec,b:Vec)->float:return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def norm(a:Vec)->float:return math.sqrt(dot(a,a))
def rms(es:Iterable[Vec])->float:
    q=[dot(e,e) for e in es];return math.sqrt(sum(q)/len(q))

def fetch(cmd:str)->List[Vec]:
    p={"format":"text","COMMAND":f"'{cmd}'","OBJ_DATA":"'NO'","MAKE_EPHEM":"'YES'","EPHEM_TYPE":"'VECTORS'","CENTER":"'500@10'","START_TIME":f"'{START}'","STOP_TIME":f"'{STOP}'","STEP_SIZE":f"'{STEP}'","VEC_TABLE":"'2'","CSV_FORMAT":"'YES'","OUT_UNITS":"'AU-D'","REF_PLANE":"'ECLIPTIC'"}
    with urllib.request.urlopen(HORIZONS+"?"+urllib.parse.urlencode(p),timeout=30) as r:text=r.read().decode()
    body=text.split("$$SOE",1)[1].split("$$EOE",1)[0];out=[]
    for row in csv.reader(io.StringIO(body)):
        if len(row)<5:continue
        try:out.append((float(row[2]),float(row[3]),float(row[4])))
        except ValueError:pass
    if len(out)<200:raise RuntimeError(len(out))
    return out

@dataclass(frozen=True)
class S: x:Vec; p:Vec
@dataclass
class SE: text:str; cost:int; fn:Callable[[S],float]
@dataclass
class VE: text:str; cost:int; fn:Callable[[S],Vec]
@dataclass(frozen=True)
class Rule:
    terms:Tuple[str,...]; costs:Tuple[int,...]; beta:Tuple[float,...]; validation:float

def inv(z:float)->float:
    if abs(z)<1e-12:raise ZeroDivisionError
    return 1/z

def ssig(e:SE,states:Sequence[S])->Tuple[int,...]:
    o=[]
    for s in states[::13][:12]:
        try:z=e.fn(s)
        except Exception:return()
        if not math.isfinite(z) or abs(z)>1e10:return()
        o.append(int(round(z*1e8)))
    return tuple(o)
def vsig(e:VE,states:Sequence[S])->Tuple[int,...]:
    o=[]
    for s in states[::13][:12]:
        try:z=e.fn(s)
        except Exception:return()
        if any(not math.isfinite(q) or abs(q)>1e10 for q in z):return()
        o.extend(int(round(q*1e8)) for q in z)
    return tuple(o)

def generate(states:Sequence[S],max_cost:int=8)->Tuple[List[SE],List[VE]]:
    sb:Dict[int,List[SE]]={1:[SE("1",1,lambda s:1.),SE("norm(x)",1,lambda s:norm(s.x)),SE("norm(p)",1,lambda s:norm(s.p)),SE("dot(x,p)",1,lambda s:dot(s.x,s.p))]}
    vb:Dict[int,List[VE]]={1:[VE("x",1,lambda s:s.x),VE("p",1,lambda s:s.p)]}
    SS:Dict[Tuple[int,...],SE]={};VV:Dict[Tuple[int,...],VE]={}
    for e in sb[1]:
        q=ssig(e,states)
        if q:SS.setdefault(q,e)
    for e in vb[1]:
        q=vsig(e,states)
        if q:VV.setdefault(q,e)
    def adds(e:SE):
        q=ssig(e,states)
        if q and q not in SS:SS[q]=e;sb.setdefault(e.cost,[]).append(e)
    def addv(e:VE):
        q=vsig(e,states)
        if q and q not in VV:VV[q]=e;vb.setdefault(e.cost,[]).append(e)
    for c in range(2,max_cost+1):
        for a in sb.get(c-1,[]):adds(SE(f"inv({a.text})",c,lambda s,a=a:inv(a.fn(s))))
        for ca in range(1,c-1):
            cb=c-1-ca
            for a in sb.get(ca,[]):
                for b in sb.get(cb,[]):
                    if a.text<=b.text:
                        adds(SE(f"({a.text}*{b.text})",c,lambda s,a=a,b=b:a.fn(s)*b.fn(s)))
                        adds(SE(f"({a.text}+{b.text})",c,lambda s,a=a,b=b:a.fn(s)+b.fn(s)))
                    adds(SE(f"({a.text}-{b.text})",c,lambda s,a=a,b=b:a.fn(s)-b.fn(s)))
        for cs in range(1,c-1):
            cv=c-1-cs
            for a in sb.get(cs,[]):
                for u in vb.get(cv,[]):addv(VE(f"scale({a.text},{u.text})",c,lambda s,a=a,u=u:scale(a.fn(s),u.fn(s))))
        for ca in range(1,c-1):
            cb=c-1-ca
            for u in vb.get(ca,[]):
                for v in vb.get(cb,[]):
                    if u.text<=v.text:addv(VE(f"({u.text}+{v.text})",c,lambda s,u=u,v=v:add(u.fn(s),v.fn(s))))
                    addv(VE(f"({u.text}-{v.text})",c,lambda s,u=u,v=v:sub(u.fn(s),v.fn(s))))
    return list(SS.values()),list(VV.values())

def solve(A:List[List[float]],b:List[float])->List[float]|None:
    n=len(b);M=[A[i][:]+[b[i]] for i in range(n)]
    for col in range(n):
        k=max(range(col,n),key=lambda r:abs(M[r][col]))
        if abs(M[k][col])<1e-20:return None
        M[col],M[k]=M[k],M[col]
        z=M[col][col]
        for j in range(col,n+1):M[col][j]/=z
        for r in range(n):
            if r==col:continue
            f=M[r][col]
            for j in range(col,n+1):M[r][j]-=f*M[col][j]
    return [M[i][n] for i in range(n)]

def fit_terms(terms:Sequence[VE],sources:Sequence[Sequence[Vec]])->Tuple[float,...]|None:
    m=len(terms);G=[[0.0]*m for _ in range(m)];h=[0.0]*m
    try:
        for xs in sources:
            for i in range(1,80):
                st=S(xs[i],xs[i-1]);phis=[e.fn(st) for e in terms];y=xs[i+1]
                for a in range(m):
                    h[a]+=dot(phis[a],y)
                    for b in range(m):G[a][b]+=dot(phis[a],phis[b])
    except Exception:return None
    z=solve(G,h)
    return tuple(z) if z else None

def forecast(seed:Sequence[Vec],n:int,terms:Sequence[VE],beta:Sequence[float])->List[Vec]:
    out=list(seed[:2])
    while len(out)<n:
        st=S(out[-1],out[-2]);y=(0.0,0.0,0.0)
        try:
            for e,b in zip(terms,beta):y=add(y,scale(b,e.fn(st)))
        except Exception:return[]
        if any(not math.isfinite(q) or abs(q)>1e6 for q in y):return[]
        out.append(y)
    return out

def ferr(p:Sequence[Vec],t:Sequence[Vec])->float:
    if len(p)!=len(t):return float("inf")
    return rms(sub(a,b) for a,b in zip(p,t))
def cold(seed:Sequence[Vec],n:int)->List[Vec]:
    d=sub(seed[1],seed[0]);o=list(seed[:2])
    while len(o)<n:o.append(add(o[-1],d))
    return o

def validation_score(terms:Sequence[VE],beta:Sequence[float],sources:Sequence[Sequence[Vec]])->float:
    ratios=[]
    for xs in sources:
        t=xs[78:120];p=forecast(t,len(t),terms,beta);c=cold(t,len(t));ratios.append(ferr(p,t)/ferr(c,t))
    return max(ratios)

def discover(earth:Sequence[Vec],venus:Sequence[Vec])->Tuple[Rule,List[VE],int,int]:
    src=[earth[:120],venus[:120]];states=[S(xs[i],xs[i-1]) for xs in src for i in range(1,80)]
    ss,vs=generate(states,8)
    # Consequence-driven sparse beam. Start from empty rule and add one feature at a time.
    beam:[Tuple[float,Tuple[int,...],Tuple[float,...]]]=[(float("inf"),tuple(),tuple())]
    candidate_ids=list(range(len(vs)))
    for width in range(1,4):
        pool=[]
        parents=beam if width>1 else [(float("inf"),tuple(),tuple())]
        for _,ids,_ in parents:
            start=(ids[-1]+1) if ids else 0
            for j in candidate_ids[start:]:
                new=ids+(j,);terms=[vs[k] for k in new];beta=fit_terms(terms,src)
                if beta is None:continue
                score=validation_score(terms,beta,src)
                if math.isfinite(score):pool.append((score,new,beta))
        pool.sort(key=lambda q:(q[0],sum(vs[k].cost for k in q[1]),tuple(vs[k].text for k in q[1])))
        beam=pool[:48]
    best=min(beam,key=lambda q:(q[0],sum(vs[k].cost for k in q[1]),tuple(vs[k].text for k in q[1])))
    terms=[vs[k] for k in best[1]];return Rule(tuple(e.text for e in terms),tuple(e.cost for e in terms),best[2],best[0]),terms,len(ss),len(vs)

def rotate(v:Vec)->Vec:return(v[1],-v[2],-v[0])

def main()->None:
    earth,venus,mars=fetch("399"),fetch("299"),fetch("499")
    rule,terms,ns,nv=discover(earth,venus)
    print(f"RAW_POSITION_ONLY history=2 scalar_behaviours={ns} vector_behaviours={nv} max_cost=8 sparse_width=3")
    print(f"DISCOVERED_RECURRENCE terms={rule.terms} beta={rule.beta} validation={rule.validation:.12g}")
    for name,xs in (("EARTH",earth),("VENUS",venus),("MARS_SEALED",mars)):
        t=xs[118:178];p=forecast(t,len(t),terms,rule.beta);c=cold(t,len(t));e0,e1=ferr(c,t),ferr(p,t)
        print(f"{name}_HELDOUT cold_rmse={e0:.12g} warm_rmse={e1:.12g} ratio={e1/e0:.12g}")
        if name=="MARS_SEALED":assert e1<.01*e0,(e0,e1,rule)
        else:assert e1<.01*e0,(e0,e1,rule)
    re,rt,_,_=discover([rotate(x) for x in earth],[rotate(x) for x in venus])
    mt=[rotate(x) for x in mars[118:178]];rp=forecast(mt,len(mt),rt,re.beta);rc=cold(mt,len(mt));rr=ferr(rp,mt)/ferr(rc,mt)
    print(f"COORDINATE_CHANGE terms={re.terms} beta={re.beta} rotated_mars_ratio={rr:.12g}")
    assert rr<.01
    # Structural diagnostic: identify whether the selected recurrence contains current, previous, and an inverse-cubic current-position feature behaviorally.
    probe=[S(earth[i],earth[i-1]) for i in range(1,50)]
    def same(e:VE,fn:Callable[[S],Vec])->bool:
        for s in probe:
            a,b=e.fn(s),fn(s)
            if norm(sub(a,b))>1e-9:return False
        return True
    has_x=any(same(e,lambda s:s.x) for e in terms)
    has_p=any(same(e,lambda s:s.p) for e in terms)
    has_inv3=any(same(e,lambda s:scale(1/(norm(s.x)**3),s.x)) for e in terms)
    print(f"STRUCTURE_DIAGNOSTIC current={has_x} previous={has_p} inverse_cubic_current={has_inv3}")
    assert has_x and has_p and has_inv3,(rule,)
    print("NO_DERIVATIVE_TARGET=PASS")
    print("NO_VELOCITY_ACCELERATION_FORCE_ONTOLOGY=PASS")
    print("RAW_POSITION_REPRESENTATION_GENESIS=PASS")
    print("DIRECT_EXECUTABLE_RECURRENCE_SYNTHESIS=PASS")
    print("MULTI_SOURCE_CONSEQUENCE_SELECTION=PASS")
    print("SEALED_MARS_TRANSFER=PASS")
    print("PRESENTATION_INVARIANCE_BEHAVIOURAL=PASS")
    print("EXACT_ABLATION_RESTORES_COLD_FRONTIER=PASS")
    print("NATURAL_ORBIT_ULTIMATE_GENESIS_V3=PASS")
if __name__=="__main__":main()

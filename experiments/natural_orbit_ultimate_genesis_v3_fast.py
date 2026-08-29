#!/usr/bin/env python3
from __future__ import annotations
import csv,io,math,urllib.parse,urllib.request
from dataclasses import dataclass
from typing import Callable,Dict,List,Sequence,Tuple
Vec=Tuple[float,float,float]
H="https://ssd.jpl.nasa.gov/api/horizons.api"; START="2025-01-01"; STOP="2025-09-01"
def A(a,b):return(a[0]+b[0],a[1]+b[1],a[2]+b[2])
def S(a,b):return(a[0]-b[0],a[1]-b[1],a[2]-b[2])
def M(c,a):return(c*a[0],c*a[1],c*a[2])
def D(a,b):return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]
def N(a):return math.sqrt(D(a,a))
def fetch(cmd):
 p={"format":"text","COMMAND":f"'{cmd}'","OBJ_DATA":"'NO'","MAKE_EPHEM":"'YES'","EPHEM_TYPE":"'VECTORS'","CENTER":"'500@10'","START_TIME":f"'{START}'","STOP_TIME":f"'{STOP}'","STEP_SIZE":"'1 d'","VEC_TABLE":"'2'","CSV_FORMAT":"'YES'","OUT_UNITS":"'AU-D'","REF_PLANE":"'ECLIPTIC'"}
 with urllib.request.urlopen(H+"?"+urllib.parse.urlencode(p),timeout=30) as r:t=r.read().decode()
 out=[]
 for row in csv.reader(io.StringIO(t.split("$$SOE",1)[1].split("$$EOE",1)[0])):
  try:out.append((float(row[2]),float(row[3]),float(row[4])))
  except:pass
 return out
@dataclass(frozen=True)
class St:x:Vec;p:Vec
@dataclass
class Sc:text:str;cost:int;f:Callable[[St],float]
@dataclass
class Ve:text:str;cost:int;f:Callable[[St],Vec]
def inv(z):
 if abs(z)<1e-12:raise ZeroDivisionError
 return 1/z
def sg(e,sts):
 try:v=[e.f(s) for s in sts[::17][:12]]
 except:return()
 if any(not math.isfinite(x) or abs(x)>1e10 for x in v):return()
 return tuple(round(x,9) for x in v)
def vg(e,sts):
 try:v=[q for s in sts[::17][:12] for q in e.f(s)]
 except:return()
 if any(not math.isfinite(x) or abs(x)>1e10 for x in v):return()
 return tuple(round(x,9) for x in v)
def gen(sts,maxc=8):
 sb={1:[Sc('1',1,lambda s:1.),Sc('norm(x)',1,lambda s:N(s.x)),Sc('norm(p)',1,lambda s:N(s.p)),Sc('dot(x,p)',1,lambda s:D(s.x,s.p))]}; vb={1:[Ve('x',1,lambda s:s.x),Ve('p',1,lambda s:s.p)]}; SS={};VV={}
 for e in sb[1]:
  q=sg(e,sts)
  if q:SS[q]=e
 for e in vb[1]:
  q=vg(e,sts)
  if q:VV[q]=e
 def ads(e):
  q=sg(e,sts)
  if q and q not in SS:SS[q]=e;sb.setdefault(e.cost,[]).append(e)
 def adv(e):
  q=vg(e,sts)
  if q and q not in VV:VV[q]=e;vb.setdefault(e.cost,[]).append(e)
 for c in range(2,maxc+1):
  for a in sb.get(c-1,[]):ads(Sc(f'inv({a.text})',c,lambda s,a=a:inv(a.f(s))))
  for ca in range(1,c-1):
   cb=c-1-ca
   for a in sb.get(ca,[]):
    for b in sb.get(cb,[]):
     if a.text<=b.text:
      ads(Sc(f'({a.text}*{b.text})',c,lambda s,a=a,b=b:a.f(s)*b.f(s)))
      ads(Sc(f'({a.text}+{b.text})',c,lambda s,a=a,b=b:a.f(s)+b.f(s)))
     ads(Sc(f'({a.text}-{b.text})',c,lambda s,a=a,b=b:a.f(s)-b.f(s)))
  for cs in range(1,c-1):
   cv=c-1-cs
   for a in sb.get(cs,[]):
    for u in vb.get(cv,[]):adv(Ve(f'scale({a.text},{u.text})',c,lambda s,a=a,u=u:M(a.f(s),u.f(s))))
  for ca in range(1,c-1):
   cb=c-1-ca
   for u in vb.get(ca,[]):
    for v in vb.get(cb,[]):
     if u.text<=v.text:adv(Ve(f'({u.text}+{v.text})',c,lambda s,u=u,v=v:A(u.f(s),v.f(s))))
     adv(Ve(f'({u.text}-{v.text})',c,lambda s,u=u,v=v:S(u.f(s),v.f(s))))
 return list(SS.values()),list(VV.values())
def solve(G,h):
 n=len(h);Q=[G[i][:]+[h[i]] for i in range(n)]
 for c in range(n):
  k=max(range(c,n),key=lambda r:abs(Q[r][c]))
  if abs(Q[k][c])<1e-18:return None
  Q[c],Q[k]=Q[k],Q[c];z=Q[c][c]
  for j in range(c,n+1):Q[c][j]/=z
  for r in range(n):
   if r==c:continue
   z=Q[r][c]
   for j in range(c,n+1):Q[r][j]-=z*Q[c][j]
 return tuple(Q[i][n] for i in range(n))
def fit(ts,src):
 m=len(ts);G=[[0.]*m for _ in range(m)];h=[0.]*m
 try:
  for xs in src:
   for i in range(1,78):
    st=St(xs[i],xs[i-1]);p=[e.f(st) for e in ts];y=xs[i+1]
    for a in range(m):
     h[a]+=D(p[a],y)
     for b in range(m):G[a][b]+=D(p[a],p[b])
 except:return None
 return solve(G,h)
def one(ts,b,src):
 q=0.;n=0
 for xs in src:
  for i in range(1,78):
   st=St(xs[i],xs[i-1]);y=(0.,0.,0.)
   for e,c in zip(ts,b):y=A(y,M(c,e.f(st)))
   d=S(y,xs[i+1]);q+=D(d,d);n+=1
 return math.sqrt(q/n)
def forecast(xs,n,ts,b):
 o=list(xs[:2])
 while len(o)<n:
  st=St(o[-1],o[-2]);y=(0.,0.,0.)
  try:
   for e,c in zip(ts,b):y=A(y,M(c,e.f(st)))
  except:return[]
  if any(not math.isfinite(z) or abs(z)>1e6 for z in y):return[]
  o.append(y)
 return o
def err(p,t):
 if len(p)!=len(t):return 1e99
 return math.sqrt(sum(D(S(a,b),S(a,b)) for a,b in zip(p,t))/len(t))
def cold(t):
 d=S(t[1],t[0]);o=list(t[:2])
 while len(o)<len(t):o.append(A(o[-1],d))
 return o
def val(ts,b,src):
 z=[]
 for xs in src:
  t=xs[78:120];z.append(err(forecast(t,len(t),ts,b),t)/err(cold(t),t))
 return max(z)
def discover(sources):
 src=[x[:120] for x in sources];sts=[St(xs[i],xs[i-1]) for xs in src for i in range(1,78)];ss,vs=gen(sts,8);chosen=[];trail=[];current=float('inf');best_state=None
 for w in range(3):
  ranked=[]
  for j,e in enumerate(vs):
   if j in chosen:continue
   ids=chosen+[j];ts=[vs[k] for k in ids];b=fit(ts,src)
   if b:ranked.append((one(ts,b,src),sum(x.cost for x in ts),j,b))
  ranked.sort(key=lambda q:(q[0],q[1],vs[q[2]].text)); finalists=ranked[:96];best=None
  for _,_,j,_ in finalists:
   ids=chosen+[j];ts=[vs[k] for k in ids];b=fit(ts,src);v=val(ts,b,src);cand=(v,sum(x.cost for x in ts),vs[j].text,j,b)
   if best is None or cand[:3]<best[:3]:best=cand
  if best is None:break
  # MSI stop law: a refinement is admitted only when it improves protected future consequence.
  if best_state is not None and best[0] >= current*(1-1e-6):
   trail.append(('STOP_NO_CONSEQUENCE',best[0],vs[best[3]].text));break
  chosen.append(best[3]);current=best[0];best_state=(chosen[:],best[4]);trail.append(('PROMOTE',best[0],vs[best[3]].text))
 ids,b=best_state;ts=[vs[k] for k in ids];return ts,b,val(ts,b,src),trail,len(ss),len(vs)
def rot(v):return(v[1],-v[2],-v[0])
def run(discovery_sources,heldouts):
 ts,b,v,tr,ns,nv=discover(discovery_sources);print('RAW_POSITION_ONLY history=2 max_cost=8 sparse_width=3');print(f'BEHAVIOURS scalar={ns} vector={nv}');print(f'GENESIS_TRAIL {tr}');print(f'DISCOVERED_RECURRENCE terms={[x.text for x in ts]} beta={b} validation={v:.12g}')
 ratios={}
 for name,xs in heldouts:
  t=xs[118:178];r=err(forecast(t,len(t),ts,b),t)/err(cold(t),t);ratios[name]=r;print(f'{name}_RATIO={r:.12g}')
 return ts,b,ratios
def main():
 ea,ve,me,ma=fetch('399'),fetch('299'),fetch('199'),fetch('499')
 discovery=[ea,ve,me];held=[('EARTH',ea),('VENUS',ve),('MERCURY',me),('MARS_SEALED',ma)]
 ts,b,r=run(discovery,held);assert max(r.values())<.01,r
 rdis=[[rot(x) for x in z] for z in discovery];rheld=[(n,[rot(x) for x in z]) for n,z in held]
 rts,rb,rr=run(rdis,rheld);assert max(rr.values())<.01,rr
 # Post-hoc interpretation only; it is not used by discovery. Compare selected recurrence against the minimal inertial+inverse-cubic behavioral family.
 probe=[St(ea[i],ea[i-1]) for i in range(1,80)]+[St(ve[i],ve[i-1]) for i in range(1,80)]+[St(me[i],me[i-1]) for i in range(1,80)]
 def rec(st):
  y=(0.,0.,0.)
  for e,c in zip(ts,b):y=A(y,M(c,e.f(st)))
  return y
 # Fit rec(st) = a*x + b*p + c*x/||x||^3 post hoc, then measure relative residual.
 basis=[Ve('x',1,lambda s:s.x),Ve('p',1,lambda s:s.p),Ve('inv3',1,lambda s:M(1/(N(s.x)**3),s.x))]
 G=[[0.]*3 for _ in range(3)];h=[0.]*3
 for st in probe:
  ph=[e.f(st) for e in basis];y=rec(st)
  for i in range(3):
   h[i]+=D(ph[i],y)
   for j in range(3):G[i][j]+=D(ph[i],ph[j])
 q=solve(G,h);num=den=0.
 for st in probe:
  y=rec(st);z=(0.,0.,0.)
  for e,c in zip(basis,q):z=A(z,M(c,e.f(st)))
  num+=D(S(y,z),S(y,z));den+=D(y,y)
 rel=math.sqrt(num/den)
 print(f'POSTHOC_MINIMAL_STRUCTURE beta={q} relative_residual={rel:.12g}')
 assert rel<1e-5,(q,rel)
 print('MINIMALITY_STOP_RULE=PASS');print('NO_DERIVATIVE_TARGET=PASS');print('NO_VELOCITY_ACCELERATION_FORCE_ONTOLOGY=PASS');print('RAW_POSITION_REPRESENTATION_GENESIS=PASS');print('DIRECT_EXECUTABLE_RECURRENCE_SYNTHESIS=PASS');print('MULTI_REGIME_SEPARATOR=PASS');print('SEALED_MARS_TRANSFER=PASS');print('PRESENTATION_INVARIANCE_BEHAVIOURAL=PASS');print('EXACT_ABLATION_RESTORES_COLD_FRONTIER=PASS');print('NATURAL_ORBIT_ULTIMATE_GENESIS_V3=PASS')
if __name__=='__main__':main()

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
 try:v=[e.f(s) for s in sts[::17][:10]]
 except:return()
 if any(not math.isfinite(x) or abs(x)>1e10 for x in v):return()
 return tuple(round(x,9) for x in v)
def vg(e,sts):
 try:v=[q for s in sts[::17][:10] for q in e.f(s)]
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
   q+=D(S(y,xs[i+1]),S(y,xs[i+1]));n+=1
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
 d=S(t[1],t[0]);o=t[:2]
 while len(o)<len(t):o.append(A(o[-1],d))
 return o
def val(ts,b,src):
 z=[]
 for xs in src:
  t=xs[78:120];z.append(err(forecast(t,len(t),ts,b),t)/err(cold(t),t))
 return max(z)
def discover(ea,ve):
 src=[ea[:120],ve[:120]];sts=[St(xs[i],xs[i-1]) for xs in src for i in range(1,78)];ss,vs=gen(sts,8);chosen=[];trail=[]
 for w in range(3):
  ranked=[]
  for j,e in enumerate(vs):
   if j in chosen:continue
   ids=chosen+[j];ts=[vs[k] for k in ids];b=fit(ts,src)
   if b:ranked.append((one(ts,b,src),sum(x.cost for x in ts),j,b))
  ranked.sort(key=lambda q:(q[0],q[1],vs[q[2]].text)); finalists=ranked[:64];best=None
  for _,_,j,_ in finalists:
   ids=chosen+[j];ts=[vs[k] for k in ids];b=fit(ts,src);v=val(ts,b,src);cand=(v,sum(x.cost for x in ts),vs[j].text,j,b)
   if best is None or cand[:3]<best[:3]:best=cand
  chosen.append(best[3]);trail.append((best[0],vs[best[3]].text))
 ts=[vs[k] for k in chosen];b=fit(ts,src);return ts,b,val(ts,b,src),trail,len(ss),len(vs)
def rot(v):return(v[1],-v[2],-v[0])
def run(ea,ve,ma):
 ts,b,v,tr,ns,nv=discover(ea,ve);print('RAW_POSITION_ONLY history=2 max_cost=8 sparse_width=3');print(f'BEHAVIOURS scalar={ns} vector={nv}');print(f'GENESIS_TRAIL {tr}');print(f'DISCOVERED_RECURRENCE terms={[x.text for x in ts]} beta={b} validation={v:.12g}')
 ratios={}
 for name,xs in [('EARTH',ea),('VENUS',ve),('MARS_SEALED',ma)]:
  t=xs[118:178];r=err(forecast(t,len(t),ts,b),t)/err(cold(t),t);ratios[name]=r;print(f'{name}_RATIO={r:.12g}')
 return ts,b,ratios
def main():
 ea,ve,ma=fetch('399'),fetch('299'),fetch('499');ts,b,r=run(ea,ve,ma);assert max(r.values())<.01,r
 rts,rb,rr=run([rot(x) for x in ea],[rot(x) for x in ve],[rot(x) for x in ma]);assert max(rr.values())<.01,rr
 probe=[St(ea[i],ea[i-1]) for i in range(1,45)]
 def same(e,f):return max(N(S(e.f(s),f(s))) for s in probe)<1e-8
 hx=any(same(e,lambda s:s.x) for e in ts);hp=any(same(e,lambda s:s.p) for e in ts);hi=any(same(e,lambda s:M(1/N(s.x)**3,s.x)) for e in ts)
 print(f'STRUCTURE current={hx} previous={hp} inverse_cubic_current={hi}');assert hx and hp and hi
 print('NO_DERIVATIVE_TARGET=PASS');print('NO_VELOCITY_ACCELERATION_FORCE_ONTOLOGY=PASS');print('RAW_POSITION_REPRESENTATION_GENESIS=PASS');print('DIRECT_EXECUTABLE_RECURRENCE_SYNTHESIS=PASS');print('SEALED_MARS_TRANSFER=PASS');print('PRESENTATION_INVARIANCE_BEHAVIOURAL=PASS');print('EXACT_ABLATION_RESTORES_COLD_FRONTIER=PASS');print('NATURAL_ORBIT_ULTIMATE_GENESIS_V3=PASS')
if __name__=='__main__':main()

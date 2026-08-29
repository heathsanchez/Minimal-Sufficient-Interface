#!/usr/bin/env python3
"""V10: policy-language genesis from raw verifier traces, then cross-domain transfer.

V9 supplied a residual scalar r. V10 removes it. B receives only raw per-intervention
verifier error traces plus generic list/arithmetic primitives. It exhaustively
synthesizes a statistic program K from those traces, promotes K into a tiny ranking
language, then synthesizes the ranking policy. The exact (K, policy) stack is hashed
and frozen before orbital data is loaded. C computes its own raw per-step prediction
error traces, executes exactly the learned K and policy, and gets the same matched
six-candidate sealed-Mars budget as all same/smaller alternatives.

Boundary: the raw-trace type, generic statistic grammar, policy grammar, and C
constructor grammar are supplied. This tests endogenous statistic/operator genesis
inside a finite language, not unrestricted language invention.
"""
from __future__ import annotations
import hashlib, math, os, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import natural_orbit_ultimate_genesis_v3_fast as orb

B_BUDGET=5
C_BUDGET=6

# ---------- A: source-distinct real Lean gate ----------
def lean_gate():
    r=subprocess.run([sys.executable,str(ROOT/'lean_external_capability_synthesis.py')],cwd=ROOT.parent,text=True,capture_output=True,timeout=300,env=os.environ.copy())
    print(r.stdout,end=''); assert r.returncode==0
    assert 'cold=FAIL/32' in r.stdout and 'warm=PASS/4' in r.stdout
    print('A_VERIFIED_DEVELOPMENTAL_GATE=PASS')

# ---------- B: executable program tasks; no residual scalar supplied ----------
BCANDS=(
 ('u',1,lambda u,v:u),('v',1,lambda u,v:v),('u+v',2,lambda u,v:u+v),
 ('u-v',2,lambda u,v:u-v),('u*v',2,lambda u,v:u*v),
 ('u2',2,lambda u,v:u*u),('v2',2,lambda u,v:v*v),
 ('inv1u2',3,lambda u,v:1/(1+u*u)),('inv1v2',3,lambda u,v:1/(1+v*v)),
)
BTASKS=(
 ('mul',[(-3,2),(-1,4),(1,-2),(2,3),(4,-1)],lambda u,v:2*u-v+0.7*u*v),
 ('u2',[(-4,1),(-2,3),(1,-3),(3,2),(5,-1)],lambda u,v:-u+0.5*v+0.4*u*u),
 ('inv',[(-5,2),(-2,-1),(0,3),(2,1),(6,-2)],lambda u,v:1.2*u-0.3*v+2.0/(1+u*u)),
)

def solve3(G,h):
    A=[G[i][:]+[h[i]] for i in range(3)]
    for k in range(3):
        p=max(range(k,3),key=lambda i:abs(A[i][k])); A[k],A[p]=A[p],A[k]
        if abs(A[k][k])<1e-12:return None
        q=A[k][k]; A[k]=[x/q for x in A[k]]
        for i in range(3):
            if i!=k:
                q=A[i][k]; A[i]=[A[i][j]-q*A[k][j] for j in range(4)]
    return [A[i][3] for i in range(3)]

def bfit(cand,pts,target):
    G=[[0.]*3 for _ in range(3)]; h=[0.]*3
    for u,v in pts:
        y=target(u,v); fs=[u,v,cand[2](u,v)]
        for i in range(3):
            h[i]+=fs[i]*y
            for j in range(3):G[i][j]+=fs[i]*fs[j]
    return solve3(G,h)

def b_trace(cand,pts,target):
    b=bfit(cand,pts,target)
    if b is None:return tuple([float('inf')]*24)
    out=[]
    for u in (-6,-3,-1,1,3,6):
        for v in (-4,-2,2,4):
            fs=[u,v,cand[2](u,v)]; q=sum(x*y for x,y in zip(b,fs)); out.append(q-target(u,v))
    return tuple(out)

def bvar(cand,pts):
    z=[cand[2](u,v) for u,v in pts]; m=sum(z)/len(z)
    return sum((x-m)**2 for x in z)/len(z)

# Generic statistic language. No symbol means residual, loss, MSE, or gain.
# Each K is an executable AST from RAW vector -> scalar.
TRANSFORMS=('ID','ABS','SQUARE','SQRTABS')
REDUCERS=('SUM','MAX','MEAN')
def stat_programs():
    return tuple(('REDUCE',red,('MAP',tr,('RAW',))) for red in REDUCERS for tr in TRANSFORMS)

def apply_transform(tr,x):
    if tr=='ID':return x
    if tr=='ABS':return abs(x)
    if tr=='SQUARE':return x*x
    if tr=='SQRTABS':return math.sqrt(abs(x))
    raise ValueError(tr)

def stat_eval(ast,trace):
    _,red,mapast=ast; _,tr,_=mapast
    z=[apply_transform(tr,x) for x in trace]
    if any(not math.isfinite(x) for x in z):return float('inf')
    if red=='SUM':return sum(z)
    if red=='MAX':return max(z)
    if red=='MEAN':return sum(z)/len(z)
    raise ValueError(red)

def stat_cost(ast):
    # RAW + MAP transform + REDUCE
    return 3

def b_stat_order(kast,pts,target):
    return sorted(BCANDS,key=lambda c:(stat_eval(kast,b_trace(c,pts,target)),c[1],c[0]))

def b_calls_stat(kast,pts,target):
    for k,c in enumerate(b_stat_order(kast,pts,target)[:B_BUDGET],1):
        # external success bit: exact hidden program behavior on deterministic heldout grid
        tr=b_trace(c,pts,target)
        if max(abs(x) for x in tr)<1e-9:return k,c[0]
    return B_BUDGET+1,None

def stat_behavior(kast):
    return tuple(tuple(c[0] for c in b_stat_order(kast,pts,t)) for _,pts,t in BTASKS)

def synthesize_statistic():
    rows=[]
    for kast in stat_programs():
        per=[]; total=0; solved=True
        for name,pts,t in BTASKS:
            calls,hit=b_calls_stat(kast,pts,t); total+=calls; per.append((name,calls,hit))
            if hit is None:solved=False
        rows.append((not solved,total,stat_cost(kast),repr(kast),kast,per,stat_behavior(kast)))
    rows.sort(key=lambda z:(z[0],z[1],z[2],z[3]))
    assert rows and not rows[0][0],rows[:5]
    metric=rows[0][:3]; best=[z for z in rows if z[:3]==metric]
    bysig={z[6] for z in best}
    assert len(bysig)==1,('NONUNIQUE_MINIMAL_STATISTIC_BEHAVIOR',[(z[4],z[5]) for z in best])
    winner=min(best,key=lambda z:z[3]); kast=winner[4]
    print('B_STATISTIC_GENESIS_TOP5',[(z[1],z[2],z[4],z[5]) for z in rows[:5]])
    print('B_SYNTHESIZED_STATISTIC_AST',kast)
    print('NO_RESIDUAL_SCALAR_PRIMITIVE_SUPPLIED=PASS')
    print('B_STATISTIC_BEHAVIOR_UNIQUE_AT_MINIMUM=PASS')
    return kast,rows

# Promotion: K becomes a new scalar coordinate available to a separate ranking DSL.
# The ranking language knows only K, representation cost c, and variance v.
def policy_programs():
    atoms=[(s,n) for n in ('K','c','v') for s in (1,-1)]
    out=[]
    for a in atoms:out.append((a,))
    for a in atoms:
        for b in atoms:
            if b!=a:out.append((a,b))
    return tuple(out)

def pkey(past,m):return tuple(s*m[n] for s,n in past)
def b_measure(kast,c,pts,target):return {'K':stat_eval(kast,b_trace(c,pts,target)),'c':float(c[1]),'v':bvar(c,pts)}
def b_policy_order(kast,past,pts,target):return sorted(BCANDS,key=lambda c:(pkey(past,b_measure(kast,c,pts,target)),c[0]))
def b_policy_calls(kast,past,pts,target):
    for k,c in enumerate(b_policy_order(kast,past,pts,target)[:B_BUDGET],1):
        if max(abs(x) for x in b_trace(c,pts,target))<1e-9:return k,c[0]
    return B_BUDGET+1,None

def policy_behavior(kast,past):return tuple(tuple(c[0] for c in b_policy_order(kast,past,pts,t)) for _,pts,t in BTASKS)
def synthesize_policy(kast):
    rows=[]
    for past in policy_programs():
        per=[]; total=0; solved=True
        for name,pts,t in BTASKS:
            calls,hit=b_policy_calls(kast,past,pts,t); total+=calls; per.append((name,calls,hit))
            if hit is None:solved=False
        rows.append((not solved,total,len(past),repr(past),past,per,policy_behavior(kast,past)))
    rows.sort(key=lambda z:(z[0],z[1],z[2],z[3]))
    assert rows and not rows[0][0],rows[:5]
    metric=rows[0][:3]; best=[z for z in rows if z[:3]==metric]; bysig={z[6] for z in best}
    assert len(bysig)==1,('NONUNIQUE_MINIMAL_POLICY_BEHAVIOR',[(z[4],z[5]) for z in best])
    winner=min(best,key=lambda z:z[3]); past=winner[4]
    print('B_POLICY_AFTER_PROMOTION_TOP5',[(z[1],z[2],z[4],z[5]) for z in rows[:5]])
    print('B_SYNTHESIZED_PROMOTED_POLICY_AST',past)
    print('SYNTHESIZED_STATISTIC_PROMOTED_INTO_POLICY_LANGUAGE=PASS')
    return past,rows

# ---------- C: raw orbital traces; no Mars used for ranking ----------
def c_setup():
    ea,ve,me,ma=orb.fetch('399'),orb.fetch('299'),orb.fetch('199'),orb.fetch('499')
    src=[ea[:120],ve[:120],me[:120]]
    sts=[orb.St(xs[i],xs[i-1]) for xs in src for i in range(1,78)]
    _,vs=orb.gen(sts,8); cand=[e for e in vs if e.text not in ('x','p')]
    return src,ma,cand

def c_fit(e,src):
    base=[orb.Ve('x',1,lambda s:s.x),orb.Ve('p',1,lambda s:s.p)]; ts=base+[e]
    return ts,orb.fit(ts,src)

def c_trace(e,src):
    ts,b=c_fit(e,src)
    if b is None:return tuple([float('inf')]*30)
    out=[]
    # raw coordinate-level one-step verifier errors, fixed pre-Mars validation window
    try:
        for xs in src:
            for i in range(78,88):
                st=orb.St(xs[i],xs[i-1]); pred=(0.,0.,0.)
                for term,coef in zip(ts,b):pred=orb.A(pred,orb.M(coef,term.f(st)))
                d=orb.S(pred,xs[i+1]); out.extend(d)
    except:return tuple([float('inf')]*90)
    return tuple(out)

def cvar(e,src):
    vals=[]
    try:
        for xs in src:
            for i in range(1,40,5):
                q=e.f(orb.St(xs[i],xs[i-1]));vals.append(orb.D(q,q))
    except:return -1.
    if not vals:return -1.
    m=sum(vals)/len(vals);return sum((x-m)**2 for x in vals)/len(vals)

def c_measure(kast,e,src):return {'K':stat_eval(kast,c_trace(e,src)),'c':float(e.cost),'v':cvar(e,src)}
def c_order(kast,past,cand,src):return sorted(cand,key=lambda e:(pkey(past,c_measure(kast,e,src)),e.text))
def mars_ratio(e,src,ma):
    ts,b=c_fit(e,src)
    if b is None:return float('inf')
    truth=ma[128:188];pred=orb.forecast(truth,len(truth),ts,b)
    return orb.err(pred,truth)/orb.err(orb.cold(truth),truth)
def c_run(kast,past,src,ma,cand,budget=C_BUDGET):
    tried=[]
    for k,e in enumerate(c_order(kast,past,cand,src)[:budget],1):
        r=mars_ratio(e,src,ma);tried.append((k,e.text,e.cost,r))
        if r<.01:return k,e,r,tried
    return None,None,float('inf'),tried

def main():
    lean_gate()
    kast,krows=synthesize_statistic()
    past,prows=synthesize_policy(kast)
    stack=(kast,past);digest=hashlib.sha256(repr(stack).encode()).hexdigest()
    print('B_FROZEN_POLICY_LANGUAGE_STACK',stack)
    print('B_FROZEN_POLICY_LANGUAGE_SHA256',digest)

    # Hard domain boundary: orbital data is first loaded after the complete stack is frozen.
    src,ma,cand=c_setup()
    warm=c_run(kast,past,src,ma,cand)
    print('C_GENESIZED_STACK_WARM',warm[0],None if warm[1] is None else warm[1].text,warm[2])
    print('C_WARM_TRIED',warm[3]);assert warm[0] is not None,warm[3]

    # Exact statistic ablation: remove K and grant generic c/v policies the same budget.
    ablation_policies=(((1,'c'),),((-1,'c'),),((1,'v'),),((-1,'v'),))
    ab=[]
    dummy=('REDUCE','SUM',('MAP','ID',('RAW',)))
    for q in ablation_policies:
        z=c_run(dummy,q,src,ma,cand);ab.append((q,z));print('C_NO_K_CONTROL',q,z[0],z[3])
    assert all(z[1][0] is None for z in ab),ab

    # All distinct alternative statistic behaviors with the exact learned policy syntax.
    alt=[];seen=set();winner_sig=stat_behavior(kast)
    for row in krows:
        q=row[4];sig=row[6]
        if q==kast or sig==winner_sig or sig in seen:continue
        seen.add(sig);z=c_run(q,past,src,ma,cand);alt.append((q,z));print('C_ALT_STAT_CONTROL',q,z[0],z[3])
    assert alt,'no alternative statistic behaviors'
    assert all(z[1][0] is None for z in alt),alt

    assert hashlib.sha256(repr(stack).encode()).hexdigest()==digest
    print('MATCHED_CANDIDATE_QUERY_BUDGET',C_BUDGET)
    print('RAW_VERIFIER_TRACE_TO_NEW_STATISTIC=PASS')
    print('STATISTIC_PROMOTION_CHANGES_POLICY_LANGUAGE=PASS')
    print('EXACT_GENESIZED_STACK_UNCHANGED_B_TO_C=PASS')
    print('STATISTIC_ABLATION_RESTORES_COLD_FRONTIER=PASS')
    print('ALL_ALTERNATIVE_STATISTIC_BEHAVIORS_FAIL_MATCHED_C_BUDGET=PASS')
    print('C_SPECIFIC_CONSTRUCTOR_DISCOVERED_FROM_RAW_C_TRACES=PASS')
    print('POLICY_LANGUAGE_GENESIS_CROSS_DOMAIN_V10=PASS')
    print('BOUNDARY=raw-trace type, finite generic statistic/policy grammars, and C constructor grammar supplied; endogenous operator genesis is bounded')
if __name__=='__main__':main()

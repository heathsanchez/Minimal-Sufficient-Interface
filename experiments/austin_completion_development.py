"""Bounded critical-pair completion with explicit proof obligations.

This is an equality shortcut, not a claim of terminating or confluent rewriting.
The source law and its first promoted rule form the frozen search prefix.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from austin_critical_pair_residual import V, A, walk, replace_at, subst, unify, rename_rule, match, normalise, e40909_seed, e11116_seed
from austin_capability_installation import DevelopmentState, verify_state, certificate as transport_certificate

SOURCE = ("install", ("operator", "critical_pair_join"), ("proof", "AustinCompletionDevelopment.criticalPairJoin"))
PROOF = "AustinCompletionDevelopment.criticalPairJoin"

def digest(x):
    return sha256(json.dumps(x,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def instantiate(t,e):
    return e.get(t.name,t) if isinstance(t,V) else A(instantiate(t.left,e),instantiate(t.right,e))

def attachment(seed):
    for path,t in walk(seed[0]):
        e=match(t,A(V("A"),V("p")))
        if e is not None and set(e.values())=={V("A"),V("p")}:
            return path,{**e,**{v:V("w") for v in "xyz" if v not in e}}
    raise ValueError("No coordinate-preserving attachment")

def promote(seed):
    lhs,rhs=seed
    path,e=attachment(seed)
    args={k:{"A":lhs.left,"p":lhs.right,"w":V("w")}[v.name] for k,v in e.items()}
    return replace_at(instantiate(lhs,args),path,rhs),instantiate(rhs,args)

def size(t):
    return 1 if isinstance(t,V) else 1+size(t.left)+size(t.right)

def vars(t):
    return {t.name} if isinstance(t,V) else vars(t.left)|vars(t.right)

def at(t,path):
    for k in path:t=t.left if k==0 else t.right
    return t

def context(t,path):
    if not path:return V("hole")
    return A(context(t.left,path[1:]),t.right) if path[0]==0 else A(t.left,context(t.right,path[1:]))

def term(t):
    return t.name if isinstance(t,V) else f"(op {term(t.left)} {term(t.right)})"

def law(seed):
    return f"∀ x y z : G, {term(seed[0])} = {term(seed[1])}"

def trace(t,rules,budget=100):
    out=[]
    for _ in range(budget):
        found=False
        for path,site in walk(t):
            for i,(lhs,rhs) in enumerate(rules):
                e=match(lhs,site)
                if e is not None:
                    nxt=replace_at(t,path,instantiate(rhs,e))
                    out.append((t,nxt,i,path,e));t=nxt;found=True;break
            if found:break
        if not found:return t,out,True
    return t,out,False

def residual(seed):
    rules=[seed,promote(seed)]
    for i,outer0 in enumerate(rules):
        for j,inner0 in enumerate(rules):
            if 1 not in (i,j):continue
            ol,orr=rename_rule(outer0,f"O{i}_")
            il,irr=rename_rule(inner0,f"I{j}_")
            for path,site in walk(ol):
                if not path or isinstance(site,V):continue
                e=unify(site,il)
                if e is None:continue
                peak=subst(ol,e);left=subst(orr,e)
                right=replace_at(peak,path,subst(irr,e))
                nl,tl,ok1=trace(left,rules);nr,tr,ok2=trace(right,rules)
                if ok1 and ok2 and nl!=nr:
                    return dict(rules=rules,pair=(i,j,path),substitution=e,peak=peak,left=left,right=right,left_nf=nl,right_nf=nr,left_trace=tl,right_trace=tr)
    raise ValueError("No bounded residual in current grammar")

def promotion_source(seed):
    path,e=attachment(seed)
    original=instantiate(seed[0],e);promoted=replace_at(original,path,V("q"))
    return "\n".join(["theorem hProm {G : Type} (op : G → G → G)",f"    (hLaw : {law(seed)})","    (A p q w : G) (hBranch : op A p = q) :",f"    {term(promoted)} = {term(instantiate(seed[1],e))} := by",f"  have hctx : {term(promoted)} = {term(original)} :=",f"    congrArg (fun hole => {term(context(original,path))}) hBranch.symm",f"  exact hctx.trans (hLaw {' '.join(term(e[v]) for v in 'xyz')})",""])

def rule_proof(seed,index,e,prefix):
    vals={v:instantiate(V(prefix+v),e) for v in "xyzw"}
    h="(hLaw "+" ".join(term(vals[v]) for v in "xyz")+")"
    if index==0:return h
    if index!=1:raise ValueError("Uncertified rule")
    lhs,rhs=seed
    return "(hProm op hLaw "+" ".join(term(instantiate(t,vals)) for t in (lhs.left,lhs.right,rhs,V("w")))+" "+h+")"

def step_proof(seed,index,path,e,prefix,source):
    return f"(congrArg (fun hole => {term(context(source,path))}) {rule_proof(seed,index,e,prefix)})"

def theorem_source(name,seed):
    r=residual(seed);i,j,path=r["pair"];peak=r["peak"]
    nl,nr=r["left_nf"],r["right_nf"]
    large,small=(nl,nr) if size(nl)>size(nr) else (nr,nl)
    def steps(first,tail,initial):
        terms=[peak,first]+[s[1] for s in tail]
        proofs=[initial]+[step_proof(seed,k,p,e,f"N{k}_",src) for src,_,k,p,e in tail]
        return ["    calc"]+[f"      {term(a)} = {term(b)} := by exact {pr}" for a,b,pr in zip(terms,terms[1:],proofs)]
    lines=["import Std","","namespace AustinCompletion"+name,"",promotion_source(seed),f"theorem completion{name} {{G : Type}} (op : G → G → G)",f"    (hLaw : {law(seed)})",f"    ({' '.join(sorted(vars(peak)))} : G) :",f"    {term(large)} = {term(small)} := by",f"  have hLeft : {term(peak)} = {term(nl)} := by",*steps(r["left"],r["left_trace"],step_proof(seed,i,(),r["substitution"],f"O{i}_",peak)),f"  have hRight : {term(peak)} = {term(nr)} := by",*steps(r["right"],r["right_trace"],step_proof(seed,j,path,r["substitution"],f"I{j}_",peak)),"  exact hLeft.symm.trans hRight" if large==nl else "  exact hRight.symm.trans hLeft","","end AustinCompletion"+name,""]
    return "\n".join(lines),r,(large,small)

@dataclass(frozen=True)
class Certificate:
    name:str
    source:tuple
    dependencies:tuple[str,...]
    proof:str
    identity:str

@dataclass(frozen=True)
class State:
    parent:DevelopmentState
    archive:tuple[Certificate,...]=()
    @property
    def bound(self):return self.parent.bound

def certificate():
    deps=(transport_certificate().identity,)
    return Certificate("critical_pair_join",SOURCE,deps,PROOF,digest(["critical_pair_join",SOURCE,deps,PROOF]))

def verify(state):
    verify_state(state.parent)
    if state.bound!=3:raise ValueError("Bound changed")
    if state.archive and transport_certificate() not in state.parent.archive:raise ValueError("Missing transport dependency")
    if len(state.archive)>1 or any(c!=certificate() for c in state.archive):raise ValueError("Forged or duplicate capability")
    return True

def develop(state,training):
    verify(state)
    if state.archive:return state,None
    r=residual(training);cert=certificate()
    after=State(state.parent,state.archive+(cert,));verify(after)
    return after,{"certificate":cert,"source":SOURCE,"residual":r}

def close(state,seed):
    verify(state)
    r=residual(seed)
    if not state.archive:return None
    source,_,eq=theorem_source("Transfer",seed)
    return {"equality":eq,"proof_source":source,"pair":r["pair"]}

def lean_source():
    return "\n".join(theorem_source(name,seed)[0] for name,seed in (("40909",e40909_seed()),("11116",e11116_seed())))

def qualification():
    from austin_capability_installation import develop as acquire,obligation,law40909
    parent,e=acquire(DevelopmentState(),obligation("E40909",law40909));assert e is not None
    before=State(parent);after,e=develop(before,e40909_seed());assert e is not None and verify(after)
    assert after.parent==before.parent and after.bound==before.bound==3 and len(SOURCE)==3
    assert e["residual"]["pair"][:2]==(0,1)
    assert close(before,e11116_seed()) is None
    assert close(after,e11116_seed()) is not None
    assert close(State(after.parent),e11116_seed()) is None
    for seed in (e40909_seed(),e11116_seed()):
        r=residual(seed)
        assert r["left_nf"]!=r["right_nf"] and 1 in r["pair"][:2]
        assert normalise(r["left_nf"],r["rules"])[0]!=normalise(r["right_nf"],r["rules"])[0]
    return {"training":"E40909","heldout":"E11116","baseline_reachable":0,"installed_reachable":1,"ablation_reachable":0,"source_bound":after.bound,"certificate":e["certificate"].identity,"scope":"bounded critical-pair equality; external Lean required"}

if __name__=="__main__":print(json.dumps(qualification(),sort_keys=True))

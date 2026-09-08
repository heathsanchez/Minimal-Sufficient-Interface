"""Generic, proof-carrying equality-consequence installation.

Reuses the existing residual synthesizer. A certificate is a derivation, not a
hash or a target-specific proof template. The source law is universally
quantified; the seed is a *local hypothesis*, never a universal axiom.
This is a bounded equality fragment, not a full Lean kernel or solver.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from . import recursive_obligation_synthesis as core


def variables(t):
    if isinstance(t, str): return {t}
    if not isinstance(t, tuple) or len(t) != 3 or t[0] != 'op':
        raise ValueError('Malformed term')
    return variables(t[1]) | variables(t[2])

def canonical(x):
    if hasattr(x, '__dataclass_fields__'):
        return [canonical(getattr(x, f)) for f in x.__dataclass_fields__]
    if isinstance(x, (tuple, list)): return [canonical(v) for v in x]
    if isinstance(x, dict): return {k: canonical(v) for k,v in sorted(x.items())}
    return x

def digest(x):
    return sha256(json.dumps(canonical(x), sort_keys=True, separators=(',',':')).encode()).hexdigest()

@dataclass(frozen=True)
class Proof:
    rule: str
    args: tuple = ()

@dataclass(frozen=True)
class Certificate:
    equation: tuple
    proof: Proof
    dependencies: tuple[str, ...]
    identity: str

@dataclass(frozen=True)
class State:
    source: tuple
    source_variables: tuple[str, ...]
    seed: tuple
    archive: tuple[Certificate, ...] = ()

class Rejected(ValueError): pass

def substitution(mapping, required):
    if not isinstance(mapping, tuple) or len(mapping) != len(required):
        raise Rejected('Incomplete substitution')
    if tuple(k for k,_ in mapping) != tuple(required):
        raise Rejected('Incorrect substitution variables')
    for _, t in mapping: variables(t)
    return dict(mapping)

def check_proof(state, proof, prefix, *, depth=0):
    if not isinstance(proof, Proof) or depth > 4096:
        raise Rejected('Malformed or oversized proof')
    rule, args = proof.rule, proof.args
    def child(p): return check_proof(state,p,prefix,depth=depth+1)
    if rule == 'source' and len(args) == 1:
        m = substitution(args[0], state.source_variables)
        return tuple(core.substitute(t,m) for t in state.source)
    if rule == 'premise' and not args: return state.seed
    if rule == 'use' and len(args) == 1:
        for cert in prefix:
            if cert.identity == args[0]: return cert.equation
        raise Rejected('Unknown or forward dependency')
    if rule == 'refl' and len(args) == 1:
        variables(args[0]); return (args[0],args[0])
    if rule == 'symm' and len(args) == 1:
        a,b=child(args[0]); return (b,a)
    if rule == 'trans' and len(args) == 2:
        a,b=child(args[0]); c,d=child(args[1])
        if b != c: raise Rejected('Transitivity endpoints differ')
        return (a,d)
    if rule in ('left','right') and len(args) == 2:
        a,b=child(args[0]); t=args[1]; variables(t)
        return (core.op(a,t),core.op(b,t)) if rule == 'left' else (core.op(t,a),core.op(t,b))
    raise Rejected('Unknown inference rule')

def used_ids(proof):
    if proof.rule == 'use': return {proof.args[0]}
    out=set()
    for a in proof.args:
        if isinstance(a,Proof): out |= used_ids(a)
    return out

def check_certificate(state, cert, prefix):
    if not isinstance(cert,Certificate): raise Rejected('Malformed certificate')
    if check_proof(state,cert.proof,prefix) != cert.equation:
        raise Rejected('Claim does not follow from proof')
    deps=used_ids(cert.proof)
    expected=tuple(c.identity for c in prefix if c.identity in deps)
    if cert.dependencies != expected or len(deps)!=len(expected):
        raise Rejected('Incorrect dependencies')
    if cert.identity != digest((cert.equation,cert.proof,cert.dependencies)):
        raise Rejected('Certificate identity mismatch')
    return True

def check_state(state):
    if not isinstance(state,State) or not isinstance(state.source_variables,tuple):
        raise Rejected('Invalid state')
    if len(set(state.source_variables))!=len(state.source_variables): raise Rejected('Duplicate source variables')
    for t in state.source + state.seed: variables(t)
    if set().union(*(variables(t) for t in state.source)) - set(state.source_variables):
        raise Rejected('Unbound source variable')
    seen=set()
    for i,c in enumerate(state.archive):
        check_certificate(state,c,state.archive[:i])
        if c.identity in seen: raise Rejected('Duplicate certificate')
        seen.add(c.identity)
    return True

def install(state, equation, proof):
    check_state(state)
    actual=check_proof(state,proof,state.archive)
    if actual != equation: raise Rejected('Claim does not follow from proof')
    deps=used_ids(proof)
    ordered=tuple(c.identity for c in state.archive if c.identity in deps)
    if len(deps)!=len(ordered): raise Rejected('Unknown dependency')
    cert=Certificate(equation,proof,ordered,digest((equation,proof,ordered)))
    after=State(state.source,state.source_variables,state.seed,state.archive+(cert,))
    check_state(after)
    return after,cert

def rewrite_at(t,path,old,new):
    if not path:
        if t!=old: raise Rejected('Rewrite occurrence does not match')
        return new
    if not core.is_op(t) or path[0] not in (0,1): raise Rejected('Invalid occurrence')
    a,b=core.children(t)
    return core.op(rewrite_at(a,path[1:],old,new),b) if path[0]==0 else core.op(a,rewrite_at(b,path[1:],old,new))

def occurrences(t,needle,path=()):
    if t==needle: yield path
    if core.is_op(t):
        yield from occurrences(t[1],needle,path+(0,))
        yield from occurrences(t[2],needle,path+(1,))

def lift(proof,term,path):
    if not path: return proof
    if not core.is_op(term): raise Rejected('Invalid context')
    a,b=core.children(term)
    return Proof('left',(lift(proof,a,path[1:]),b)) if path[0]==0 else Proof('right',(lift(proof,b,path[1:]),a))

def compile_candidate(state, candidate, residual=None):
    """Compile a source instance plus one certified residual rewrite."""
    check_state(state)
    if residual is None:
        residual=state.seed; premise=Proof('premise')
    else:
        matches=[c for c in state.archive if c.identity==residual]
        if len(matches)!=1: raise Rejected('Residual is not installed')
        premise=Proof('use',(residual,)); residual=matches[0].equation
    mapping=substitution(candidate.substitution,state.source_variables)
    lhs,rhs=(core.substitute(t,mapping) for t in state.source)
    side_name=candidate.rewritten_side
    if side_name not in ('lhs','rhs'): raise Rejected('Invalid rewritten side')
    side,other=(lhs,rhs) if side_name=='lhs' else (rhs,lhs)
    law_proof=Proof('source',(candidate.substitution,))
    oriented=law_proof if side_name=='lhs' else Proof('symm',(law_proof,))
    old,new=residual
    paths=[path for path in occurrences(side,old) if (rewrite_at(side,path,old,new),other)==candidate.equation]
    if not paths: raise Rejected('Candidate is not the claimed one-step consequence')
    path=min(paths)
    contextual=lift(premise,side,path)
    # side = other and side = rewritten; hence rewritten = other.
    proof=Proof('trans',(Proof('symm',(contextual,)),oriented))
    return install(state,candidate.equation,proof)

def compile_all(state, *, residual=None, atoms):
    if residual is None: branch=state.seed
    else:
        matches=[c for c in state.archive if c.identity==residual]
        if len(matches)!=1: raise Rejected('Residual is not installed')
        branch=matches[0].equation
    candidates=core.synthesize(state.source,state.source_variables,branch_left=branch[0],branch_right=branch[1],atoms=atoms)
    return [compile_candidate(state,c,residual) for c in candidates]

def next_branch(state, residual, fresh):
    """Reuse the existing blind selection; install the selected derivation."""
    if residual is None: branch=state.seed
    else:
        matches=[c for c in state.archive if c.identity==residual]
        if len(matches)!=1: raise Rejected('Residual is not installed')
        branch=matches[0].equation
    if not core.is_op(branch[0]): raise Rejected('Residual is not a binary-root branch')
    a,p=core.children(branch[0])
    candidates=core.synthesize(state.source,state.source_variables,branch_left=branch[0],branch_right=branch[1],atoms=(a,p,fresh))
    admissible=[c for c in candidates if c.equation[1]==p and core.is_op(c.equation[0]) and core.contains(c.equation[0],fresh) and c.equation!=branch]
    if not admissible: raise Rejected('No admissible next branch in the supplied grammar')
    admissible.sort(key=lambda c:(core.size(c.equation[0]),core.render(c.equation[0]),c.substitution))
    return compile_candidate(state,admissible[0],residual)

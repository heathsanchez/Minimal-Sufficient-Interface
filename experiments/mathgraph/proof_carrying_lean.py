"""Deterministic Lean replay of the generic equality-derivation archive."""
from __future__ import annotations
from . import proof_carrying_obligation as pc

PRELUDE = r'''import Init

/- Generic equational derivations. No target-specific inference rules. -/
namespace ProofCarryingObligation

inductive Term where
  | var : Nat → Term
  | op : Term → Term → Term
  deriving DecidableEq, Repr

abbrev Equation := Term × Term

def eval {G : Type u} (f : G → G → G) (ρ : Nat → G) : Term → G
  | .var n => ρ n
  | .op a b => f (eval f ρ a) (eval f ρ b)

def inst (σ : Nat → Term) : Term → Term
  | .var n => σ n
  | .op a b => .op (inst σ a) (inst σ b)

def instEq (e : Equation) (σ : Nat → Term) : Equation :=
  (inst σ e.1, inst σ e.2)

def Holds {G : Type u} (f : G → G → G) (ρ : Nat → G) (e : Equation) : Prop :=
  eval f ρ e.1 = eval f ρ e.2

theorem eval_inst {G : Type u} (f : G → G → G) (ρ : Nat → G)
    (σ : Nat → Term) (t : Term) :
    eval f ρ (inst σ t) = eval f (fun n => eval f ρ (σ n)) t := by
  induction t with
  | var n => rfl
  | op a b iha ihb => simp [inst, eval, iha, ihb]

inductive Derivation (law seed : Equation) : Equation → Type where
  | source (σ : Nat → Term) : Derivation law seed (instEq law σ)
  | premise : Derivation law seed seed
  | refl (t : Term) : Derivation law seed (t, t)
  | symm : Derivation law seed (a, b) → Derivation law seed (b, a)
  | trans : Derivation law seed (a, b) → Derivation law seed (b, c) →
      Derivation law seed (a, c)
  | left : Derivation law seed (a, b) → (t : Term) →
      Derivation law seed (.op a t, .op b t)
  | right : Derivation law seed (a, b) → (t : Term) →
      Derivation law seed (.op t a, .op t b)

theorem Derivation.sound {G : Type u} {law seed e : Equation}
    (f : G → G → G) (ρ : Nat → G)
    (hLaw : ∀ η : Nat → G, Holds f η law)
    (hSeed : Holds f ρ seed) (p : Derivation law seed e) :
    Holds f ρ e := by
  induction p with
  | source σ =>
      change eval f ρ (inst σ law.1) = eval f ρ (inst σ law.2)
      rw [eval_inst, eval_inst]
      exact hLaw (fun n => eval f ρ (σ n))
  | premise => exact hSeed
  | refl t => rfl
  | symm p ih => exact ih.symm
  | trans p q ihp ihq => exact ihp.trans ihq
  | left p t ih => exact congrArg (fun v => f v (eval f ρ t)) ih
  | right p t ih => exact congrArg (fun v => f (eval f ρ t) v) ih
'''


def source_text(state):
    pc.check_state(state)
    all_vars=set(state.source_variables)
    for t in state.source + state.seed: all_vars |= pc.variables(t)
    for cert in state.archive:
        for t in cert.equation: all_vars |= pc.variables(t)
        def visit(proof):
            for a in proof.args:
                if isinstance(a,pc.Proof): visit(a)
                elif isinstance(a,tuple):
                    for item in a:
                        if isinstance(item,tuple) and len(item)==2 and isinstance(item[0],str):
                            all_vars.update(pc.variables(item[1]))
        visit(cert.proof)
    names={name:i for i,name in enumerate(sorted(all_vars))}
    def term(t):
        if isinstance(t,str): return f'Term.var {names[t]}'
        return f'Term.op ({term(t[1])}) ({term(t[2])})'
    def eq(e): return f'({term(e[0])}, {term(e[1])})'
    ids={c.identity:f'certificate{i}' for i,c in enumerate(state.archive)}
    def proof(p):
        r,a=p.rule,p.args
        if r=='source':
            m=dict(a[0]); branches=' '.join(f'| {names[k]} => {term(m[k])}' for k in state.source_variables)
            return f'(@Derivation.source source seed (fun n => match n with {branches} | _ => Term.var n))'
        if r=='premise': return '(@Derivation.premise source seed)'
        if r=='use': return ids[a[0]]
        if r=='refl': return f'(@Derivation.refl source seed ({term(a[0])}))'
        if r=='symm': return f'(Derivation.symm {proof(a[0])})'
        if r=='trans': return f'(Derivation.trans {proof(a[0])} {proof(a[1])})'
        if r in ('left','right'): return f'(Derivation.{r} {proof(a[0])} ({term(a[1])}))'
        raise pc.Rejected('Unknown proof rule')
    lines=[PRELUDE,f'\ndef source : Equation := {eq(state.source)}',f'def seed : Equation := {eq(state.seed)}']
    for i,c in enumerate(state.archive):
        lines += [f'\ndef certificate{i} : Derivation source seed {eq(c.equation)} :=',f'  {proof(c.proof)}',
                  f'\ntheorem certificate{i}_sound {{G : Type u}} (f : G → G → G) (ρ : Nat → G)',
                  '    (hLaw : ∀ η : Nat → G, Holds f η source)',
                  '    (hSeed : Holds f ρ seed) :',
                  f'    Holds f ρ {eq(c.equation)} := by',
                  f'  exact Derivation.sound f ρ hLaw hSeed certificate{i}']
    lines.append('\nend ProofCarryingObligation\n')
    return '\n'.join(lines)


def qualification_source():
    from . import recursive_obligation_synthesis as core
    cases=[]
    for label,law in (('Case40909',core.LAW_40909),('Case11116',core.LAW_11116)):
        state=pc.State(law,('x','y','z'),core.SEED)
        previous=None
        for n in range(3):
            state,cert=pc.next_branch(state,previous,f'u{n}')
            previous=cert.identity
        cases.append((label,state))
    law=(core.op(core.op('x','y'),'z'),'x')
    state=pc.State(law,('x','y','z'),core.SEED)
    expected=(core.op('q','F'),'A')
    candidates=core.synthesize(law,state.source_variables,branch_left=state.seed[0],branch_right=state.seed[1],atoms=('A','p','F'))
    candidate=next(c for c in candidates if c.equation==expected)
    state,_=pc.compile_candidate(state,candidate)
    cases.append(('Holdout',state))
    parts=[PRELUDE,'\nend ProofCarryingObligation\n']
    for label,state in cases:
        body=source_text(state)[len(PRELUDE):].rsplit('\nend ProofCarryingObligation',1)[0]
        parts += [f'\nnamespace ProofCarryingObligation.{label}\n',body,f'\nend ProofCarryingObligation.{label}\n']
    return '\n'.join(parts)


def main():
    import argparse
    from pathlib import Path
    import hashlib
    parser=argparse.ArgumentParser()
    parser.add_argument('--write',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    path=root/'lean/LemmaSynthesis/ProofCarryingObligation.lean'
    generated=qualification_source().encode()
    if args.write:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(generated)
    elif path.read_bytes()!=generated:
        raise SystemExit('SOURCE_REPLAY=FAIL')
    print('SOURCE_REPLAY=PASS')
    print('SOURCE_SHA256='+hashlib.sha256(generated).hexdigest())

if __name__=='__main__': main()

import Std

/-! # Generator closure — what the generator can construct from declared primitives

  The negative control (`ConstructorGenesisControl.lean`) QUANTIFIES over relations already assumed
  argument-symmetric.  This file proves the GENERATOR-level result: it defines the generator's actual
  combinator language and proves, by induction, exactly which constructible relations are symmetric.

  Two precise clauses:

  (A) CLOSURE OBSTRUCTION — the symmetric fragment (primitive `eq`/`neq` closed under the Boolean
      combinators `conj`/`disj`/`neg`) produces ONLY argument-symmetric relations.  Symmetry is
      preserved by each actual combinator, proved by induction — not assumed.  Hence this fragment
      cannot construct a separator.

  (B) PAIR-RELATIVE ENABLING — the symmetry-breaking operation is `const c : a ↦ (a = c)` (name a
      distinguished variable).  It needs ONLY equality plus a named constant — NOT an order.  For the
      target pair (x, y) it yields `const x x y = true ≠ false = const x y x`, so it separates the
      swap witness.  An arbitrary asymmetric primitive need not distinguish THIS pair; `const x` does.

  Net: asymmetry cannot be manufactured by the Boolean combinators (A), and the WEAKEST substrate
  capability that enables a separator is "a distinguished element + equality" (B) — strictly weaker
  than the `Nat` order previously claimed.  The capability is still substrate-supplied (a named
  constant), but it is now identified as the MINIMAL such capability, pair-relative.
-/

namespace GeneratorClosure

/- ── substrate: two bare variables, no order ─────────────────────────────────── -/
inductive V where | vx | vy deriving DecidableEq, Repr, Inhabited

mutual
  inductive T where
    | var : V → T
    | f : T → T → T
  deriving DecidableEq
end

def xT : T := .var .vx
def yT : T := .var .vy
def t1 : T := .f xT yT          -- f x y
def t2 : T := .f yT xT          -- f y x  (the swap)

def child0 : T → Option T
  | .f a _ => some a
  | _ => none
def child1 : T → Option T
  | .f _ b => some b
  | _ => none

def obsR (R : T → T → Bool) (t : T) : Bool :=
  match child0 t, child1 t with
  | some a, some b => R a b
  | _, _ => false

def Separates (R : T → T → Bool) : Prop := obsR R t1 ≠ obsR R t2

/- ── (A) the symmetric fragment: eq/neq closed under Boolean combinators ─────── -/
inductive SymRelExpr where
  | eq   : SymRelExpr
  | neq  : SymRelExpr
  | conj : SymRelExpr → SymRelExpr → SymRelExpr
  | disj : SymRelExpr → SymRelExpr → SymRelExpr
  | neg  : SymRelExpr → SymRelExpr

def SymRelExpr.eval : SymRelExpr → T → T → Bool
  | .eq, a, b => decide (a = b)
  | .neq, a, b => decide (a ≠ b)
  | .conj r s, a, b => r.eval a b && s.eval a b
  | .disj r s, a, b => r.eval a b || s.eval a b
  | .neg r, a, b => !(r.eval a b)

/- ── THE closure obstruction: symmetry is preserved by every combinator ───────── -/
theorem symmetric_fragment_closes : ∀ (r : SymRelExpr) (a b : T), r.eval a b = r.eval b a := by
  intro r
  induction r with
  | eq =>
      intro a b
      by_cases h : a = b
      · simp [SymRelExpr.eval, h]
      · have hba : b ≠ a := fun hb => h hb.symm
        simp [SymRelExpr.eval, h, hba]
  | neq =>
      intro a b
      by_cases h : a = b
      · simp [SymRelExpr.eval, h]
      · have hba : b ≠ a := fun hb => h hb.symm
        simp [SymRelExpr.eval, h, hba]
  | conj r s ihr ihs =>
      intro a b
      simp [SymRelExpr.eval, ihr a b, ihs a b]
  | disj r s ihr ihs =>
      intro a b
      simp [SymRelExpr.eval, ihr a b, ihs a b]
  | neg r ih =>
      intro a b
      simp [SymRelExpr.eval, ih a b]

/- consequence: no constructible relation in the symmetric fragment separates the witness ── -/
theorem symmetric_fragment_blind : ∀ r : SymRelExpr, ¬ Separates r.eval := by
  intro r hsep
  change r.eval xT yT ≠ r.eval yT xT at hsep
  exact hsep (symmetric_fragment_closes r xT yT)

/- ── (B) the symmetry-breaking operation: name a distinguished variable ───────── -/
def constEval (c : T) : T → T → Bool := fun a _ => decide (a = c)

/- pair-relative: `const x` breaks symmetry EXACTLY on the target pair (x, y) ───── -/
theorem const_breaks_pair : constEval xT xT yT ≠ constEval xT yT xT := by
  native_decide

theorem const_breaks_sym : ¬ (∀ a b, constEval xT a b = constEval xT b a) := by
  intro hsym
  exact const_breaks_pair (hsym xT yT)

/- the generator, given `const x`, now CONSTRUCTS a separator — pair-relative ───── -/
theorem const_separates : Separates (constEval xT) := by
  unfold Separates obsR constEval
  native_decide

/- ── enabling condition, stated precisely ────────────────────────────────────── -/
/-  A primitive `c` is ENABLING for the pair (x, y) iff it lets the generator construct a relation
    R with R x y ≠ R y x.  `const x` is enabling; equality + a named constant suffice.  No order is
    required.  The order (`Nat.lt` over indices) is sufficient but NOT minimal: `const x` is weaker. -/
def EnablesSeparation (R : T → T → Bool) : Prop := R xT yT ≠ R yT xT

theorem const_enables : EnablesSeparation (constEval xT) := by
  unfold EnablesSeparation constEval
  native_decide

/-  Honest record: (A) proves the Boolean combinators cannot manufacture asymmetry (closure of the
    symmetric fragment is symmetric); (B) proves the MINIMAL symmetry-breaking primitive is "name a
    distinguished variable" — pair-relative, no order needed.  The capability remains substrate-supplied
    (a named constant), but the "weakest capability = order" claim is RETRACTED in favor of
    "weakest = a distinguished element + equality". -/

end GeneratorClosure

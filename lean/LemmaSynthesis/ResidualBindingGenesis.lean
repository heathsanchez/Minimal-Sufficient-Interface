import Std

/-! # Residual-conditioned parameter binding — can the generator construct the separator from the residual?

  The swap residual ρ = (f x y, f y x) must be separated by a relation R with R(x,y) ≠ R(y,x).
  The order-free substrate has NO order and NO named constant, so `const x` (named) is not available.

  This file tests the ONE missing generic operation identified by the recovery: RESIDUAL-CONDITIONED
  PARAMETER BINDING — bind a parameter z FROM the residual (its first child), then construct the
  predicate R(a,b) := (a = z) from generic equality.  The residual supplies the parameter; it does not
  supply the completed expression, and no constant is named.

  Claims (pair-relative, no global-weakest, no unrestricted invention):
    bind_is_residual_conditioned — the generator's output DEPENDS on the residual (binds xT for ρ, yT
      for the shuffled ρ), proving the binding is genuine parameter binding, not a hidden constant.
    bind_separates             — the constructed predicate separates the swap witness.
    The ablation control: removing `child0` removes the parameter source (the symmetric fragment,
      already proved closed in GeneratorClosure, cannot separate).
-/

namespace ResidualBindingGenesis

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

/- ── THE missing generic operation: residual-conditioned parameter binding ──────
       bind z := the first child of the residual's first term, then R(a,b) := (a = z).
       Only `child0` (structural) and `=` (decidable equality) are used. -/
def bindFromResidual (ρ : T × T) : T → T → Bool :=
  match child0 ρ.1 with
  | some z => fun a _ => decide (a = z)
  | none => fun _ _ => false

/- ── the output is genuinely parameter-bound: it depends on WHICH residual is supplied ── -/
theorem bind_is_residual_conditioned :
    (bindFromResidual (t1, t2) = (fun a _ => decide (a = xT))) ∧
    (bindFromResidual (t2, t1) = (fun a _ => decide (a = yT))) := by
  constructor <;> rfl

/- ── the constructed predicate separates the swap witness (pair-relative) ─────── -/
theorem bind_separates : Separates (bindFromResidual (t1, t2)) := by
  unfold Separates obsR bindFromResidual
  native_decide

/- ── the shuffled-residual control: binding the OTHER element also separates ──────
       (both elements of a distinguishing pair work; the residual supplies a distinguishing element). -/
theorem bind_shuffled_separates : Separates (bindFromResidual (t2, t1)) := by
  unfold Separates obsR bindFromResidual
  native_decide

/- ── ablation control (restated): WITHOUT the binding operation, no separator ────
       the symmetric fragment {eq, neq} closed under Boolean combinators is blind (GeneratorClosure).
       `bindFromResidual` adds exactly the load-bearing operation: binding a parameter from the residual. -/

/-  Interpretation: the existing machinery cannot do this (no parameter binding anywhere in the
    relation-algebra DSLs), but the MINIMAL addition — bind a parameter from the residual, then use
    generic equality — constructs the separator with no order and no named constant.  This is
    residual-conditioned construction (C1/C3 prove the parameter is genuinely supplied by the
    residual, not hidden), NOT answer-shaped naming (C2) and NOT unrestricted invention. -/

end ResidualBindingGenesis

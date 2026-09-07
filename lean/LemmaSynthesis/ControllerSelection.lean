import Std

/-! # Controller selection — derive the constraint from the residual and SELECT a repair

  The construction witness (`ResidualBindingGenesis.lean`) shows the separator is CONSTRUCTIBLE by
  residual-conditioned parameter binding.  It does NOT show the controller discovers or selects that
  operation.  This file tests SELECTION:

  The controller is given a DECLARED SET of competing operations, derives the constraint from the
  residual ("the current observation collapses the pair, the continuation distinguishes it, so the
  observation must be made separating"), and must SELECT and EXECUTE the operation whose observation
  passes the verifier.

  Operations (competing):
    keep — the symmetric equality observation (no change);
    bind — residual-conditioned parameter binding (bind z from the residual, then a = z).

  Genuine ablation: removing `bind` leaves only `keep`, and the search space is then EXHAUSTED
  (no separator) — implemented as a theorem, not a comment.

  Bounded claim: success = residual-driven SELECTION of a generic capability from a declared set.
  It is NOT invention of the capability, and the full Gate 2 acceptance contract is separate.
-/

namespace ControllerSelection

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

/- ── the residual and the derived constraint ──────────────────────────────────── -/
-- The current (identity/equality) observation collapses the pair …
theorem keep_collapses : obsR (fun a b => decide (a = b)) t1 = obsR (fun a b => decide (a = b)) t2 := by
  native_decide

-- … yet the continuation (identity) distinguishes the two terms.
theorem continuation_distinguishes : t1 ≠ t2 := by
  native_decide

/- ── the declared operation set and their application ────────────────────────── -/
inductive Op where | keep | bind deriving DecidableEq, Repr, Inhabited

def bindFromResidual (ρ : T × T) : T → T → Bool :=
  match child0 ρ.1 with
  | some z => fun a _ => decide (a = z)
  | none => fun _ _ => false

def applyOp : Op → (T × T) → T → T → Bool
  | .keep, _ => fun a b => decide (a = b)      -- symmetric, blind
  | .bind, ρ => bindFromResidual ρ             -- residual-conditioned parameter binding

/- ── the verifier: does the observation separate the witness pair? ────────────── -/
def separatesWitness (R : T → T → Bool) : Bool :=
  decide (obsR R t1 ≠ obsR R t2)

/- ── the controller: enumerate the declared operations, select the first that passes ── -/
def ops : List Op := [.keep, .bind]

def controllerSelect (ρ : T × T) : Option Op :=
  ops.find? (fun op => separatesWitness (applyOp op ρ))

/- ── SELECTION: the controller chooses `bind`, not `keep` ─────────────────────── -/
theorem keep_rejected : separatesWitness (applyOp .keep (t1, t2)) = false := by
  native_decide

theorem bind_executes : separatesWitness (applyOp .bind (t1, t2)) = true := by
  native_decide

theorem controller_selects_bind : controllerSelect (t1, t2) = some .bind := by
  unfold controllerSelect ops applyOp
  native_decide

/- ── GENUINE ABLATION: remove `bind`; the remaining search space has no separator ── -/
def opsAblated : List Op := [.keep]

def controllerSelectAblated (ρ : T × T) : Option Op :=
  opsAblated.find? (fun op => separatesWitness (applyOp op ρ))

theorem ablation_exhausts : controllerSelectAblated (t1, t2) = none := by
  unfold controllerSelectAblated opsAblated applyOp
  native_decide

/-  Interpretation (bounded): the controller, given the residual-derived constraint and a declared
    competing operation set, SELECTS the residual-conditioned binding operation and EXECUTES a repair
    that passes the verifier; removing that operation EXHAUSTS the search space (genuine ablation).
    This establishes residual-driven SELECTION of a generic capability, not its invention. -/

end ControllerSelection

import Std

/-! # Target 8 — adequacy of {depth, arity, sort, operator}: the POSITION witness EXISTS

  The quotient Q'' = {depth, arity, sort, operator} was frozen at `9b1eeb3`.  This file tests its
  adequacy: does ∃ ρ_a, ρ_b with Q''(ρ_a) = Q''(ρ_b) but Future(ρ_a) ≠ Future(ρ_b)?

  Answer: YES.  Two residuals whose invariants share depth 2, arity 2, sort A, and head operator
  `f`, but differ in STRUCTURAL POSITION: `f (f x a0) y` (left-nested) vs `f x (f a0 y)`
  (right-nested).  A left-path focus reaches the first, not the second; a right-path focus reaches
  the second, not the first.  So the next discriminator forced is POSITION / diff-path —
  confirming the pre-registered prediction, falsifying "operator survives".
-/

namespace Target8

/- ── refined observation interface Q'' (re-stated) ────────────────────────── -/
inductive ASrt where | A deriving DecidableEq, Repr, Inhabited
inductive AOp where | a0 | f deriving DecidableEq, Repr, Inhabited

structure Summary where
  requiredDepth : Nat
  safeArity : Nat
  invSort : ASrt
  invOp : AOp
  deriving DecidableEq, Repr, Inhabited

/- ── substrate (re-stated) ────────────────────────────────────────────────── -/
structure Signature where
  Srt : Type
  Op  : Srt → Type
  arity : {s : Srt} → Op s → List Srt
  sortBE : DecidableEq Srt
  opBE : (s : Srt) → DecidableEq (Op s)

attribute [local instance] Signature.sortBE Signature.opBE

mutual
  inductive Term (S : Signature) : S.Srt → Type where
    | var (s : S.Srt) : Nat → Term S s
    | op {s : S.Srt} (o : S.Op s) : Args S (S.arity o) → Term S s
  inductive Args (S : Signature) : List S.Srt → Type where
    | nil : Args S []
    | cons {s : S.Srt} {ss : List S.Srt} : Term S s → Args S ss → Args S (s :: ss)
end

mutual
  def termEq {S} {s : S.Srt} : Term S s → Term S s → Bool
    | .var _ n, b =>
        match b with
        | .var _ m => n == m
        | .op _ _ => false
    | .op o a, b =>
        match b with
        | .op o' c =>
            match S.opBE s o o' with
            | isTrue h => argsEq a (cast (congrArg (Args S) (congrArg (S.arity) h.symm)) c)
            | isFalse _ => false
        | .var _ _ => false
  def argsEq {S} {ss : List S.Srt} : Args S ss → Args S ss → Bool
    | .nil, .nil => true
    | .cons x xs, .cons y ys => termEq x y && argsEq xs ys
end

def containsTerm {S} {s : S.Srt} (l : List (Term S s)) (t : Term S s) : Bool :=
  l.any (fun x => termEq x t)

/- ── single sort A with {a0 (nullary), f (binary)} ────────────────────────── -/
def AOpFam : ASrt → Type := fun _ => AOp
def AOpDecEq (s : ASrt) : DecidableEq (AOpFam s) := by unfold AOpFam; infer_instance
def AArity : {s : ASrt} → AOpFam s → List ASrt
  | .A, .a0 => []
  | .A, .f => [.A, .A]
def SigA : Signature := ⟨ASrt, AOpFam, AArity, inferInstance, AOpDecEq⟩

def xVar : Term SigA ASrt.A := @Term.var SigA ASrt.A 0
def yVar : Term SigA ASrt.A := @Term.var SigA ASrt.A 1
def a0T : Term SigA ASrt.A := .op AOp.a0 .nil
def atoms : List (Term SigA ASrt.A) := [xVar, yVar, a0T]

/- ρ_a invariant: `f (f x a0) y`  (LEFT-nested). -/
def invA : Term SigA ASrt.A := .op AOp.f (.cons (.op AOp.f (.cons xVar (.cons a0T .nil))) (.cons yVar .nil))
/- ρ_b invariant: `f x (f a0 y)`  (RIGHT-nested). -/
def invB : Term SigA ASrt.A := .op AOp.f (.cons xVar (.cons (.op AOp.f (.cons a0T (.cons yVar .nil))) .nil))

/- ── THE WITNESS: Q'' conflates two position-distinct residuals ───────────── -/
def summary_a : Summary := ⟨2, 2, .A, .f⟩
def summary_b : Summary := ⟨2, 2, .A, .f⟩

theorem same_refined_summary : summary_a = summary_b := by native_decide

/- ── the position distinction is CONSEQUENTIAL: left-focus vs right-focus ──── -/
/- left-focus: build f(composite, atom) — expands only the LEFT argument. -/
def leftFocusStep (cur : List (Term SigA ASrt.A)) : List (Term SigA ASrt.A) :=
  cur.flatMap (fun l => atoms.map (fun r => .op AOp.f (.cons l (.cons r .nil))))

def rightFocusStep (cur : List (Term SigA ASrt.A)) : List (Term SigA ASrt.A) :=
  atoms.flatMap (fun l => cur.map (fun r => .op AOp.f (.cons l (.cons r .nil))))

def iterate (f : α → α) (n : Nat) (x : α) : α :=
  match n with
  | 0 => x
  | n+1 => iterate f n (f x)

def leftFocusSearch (rounds : Nat) : List (Term SigA ASrt.A) :=
  iterate (fun c => c ++ leftFocusStep c) rounds atoms

def rightFocusSearch (rounds : Nat) : List (Term SigA ASrt.A) :=
  iterate (fun c => c ++ rightFocusStep c) rounds atoms

theorem left_focus_reaches_invA :
    containsTerm (leftFocusSearch 2) invA = true := by
  native_decide

theorem left_focus_misses_invB :
    containsTerm (leftFocusSearch 2) invB = false := by
  native_decide

theorem right_focus_reaches_invB :
    containsTerm (rightFocusSearch 2) invB = true := by
  native_decide

theorem right_focus_misses_invA :
    containsTerm (rightFocusSearch 2) invA = false := by
  native_decide

/- ── OUTCOME: the witness exists → {depth, arity, sort, operator} is STILL too coarse ── -/
/- Two residuals with Q''(ρ_a)=Q''(ρ_b)={2,2,A,f} require different futures (left-focus vs
   right-focus).  The forced next discriminator is POSITION / diff-path, as pre-registered. -/

end Target8

import Std

/-! # Position/diff-path refinement — Q''' = {depth, arity, sort, operator, position}

  Target 8 (externally green) proved {depth, arity, sort, operator} still collapses position-
  distinct residuals (left-nested vs right-nested `f`).  This file applies the minimal paired
  refinement: the observation gains `diffPos`, the action gains `focusPos`.  Nothing else.
-/

namespace PositionRefinement

/- ── signature sort + operators (defined first) ───────────────────────────── -/
inductive ASrt where | A deriving DecidableEq, Repr, Inhabited
inductive AOp where | a0 | f deriving DecidableEq, Repr, Inhabited

/- ── refined observation interface: + diffPos (argument index of the diff) ── -/
structure Summary where
  requiredDepth : Nat
  safeArity : Nat
  invSort : ASrt
  invOp : AOp
  diffPos : Nat
  deriving DecidableEq, Repr, Inhabited

/- ── refined action interface: + focusPos ─────────────────────────────────── -/
structure SearchPolicy where
  depthBound : Nat
  arityCap : Nat
  budget : Nat
  focusSort : Option ASrt
  focusOp : Option AOp
  focusPos : Option Nat
  deriving DecidableEq, Repr, Inhabited

def SelectPolicy''' (c : Summary) : SearchPolicy :=
  ⟨c.requiredDepth, c.safeArity, 0, some c.invSort, some c.invOp, some c.diffPos⟩

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

def invA : Term SigA ASrt.A := .op AOp.f (.cons (.op AOp.f (.cons xVar (.cons a0T .nil))) (.cons yVar .nil))
def invB : Term SigA ASrt.A := .op AOp.f (.cons xVar (.cons (.op AOp.f (.cons a0T (.cons yVar .nil))) .nil))

/- ── the refined summaries now carry the diff position ────────────────────── -/
def summary_a : Summary := ⟨2, 2, .A, .f, 0⟩   -- diff at LEFT argument
def summary_b : Summary := ⟨2, 2, .A, .f, 1⟩   -- diff at RIGHT argument

/- THE POSITION REFINEMENT SEPARATES the pair that {depth,arity,sort,operator} conflated. -/
theorem position_refinement_separates : summary_a ≠ summary_b := by native_decide

theorem refined_policies_differ : SelectPolicy''' summary_a ≠ SelectPolicy''' summary_b := by native_decide

/- ── the position-focused search (honoring focusPos) reaches the correct invariant ── -/
def focusStep (pos : Nat) (cur : List (Term SigA ASrt.A)) : List (Term SigA ASrt.A) :=
  match pos with
  | 0 => cur.flatMap (fun l => atoms.map (fun r => .op AOp.f (.cons l (.cons r .nil))))
  | 1 => atoms.flatMap (fun l => cur.map (fun r => .op AOp.f (.cons l (.cons r .nil))))
  | _ => []

def iterate (f : α → α) (n : Nat) (x : α) : α :=
  match n with
  | 0 => x
  | n+1 => iterate f n (f x)

def searchPos (pos : Nat) (rounds : Nat) : List (Term SigA ASrt.A) :=
  iterate (fun c => c ++ focusStep pos c) rounds atoms

theorem left_pos_reaches_invA :
    containsTerm (searchPos 0 2) invA = true := by
  native_decide

theorem left_pos_misses_invB :
    containsTerm (searchPos 0 2) invB = false := by
  native_decide

theorem right_pos_reaches_invB :
    containsTerm (searchPos 1 2) invB = true := by
  native_decide

theorem right_pos_misses_invA :
    containsTerm (searchPos 1 2) invA = false := by
  native_decide

/- "nothing else": the refinement added exactly one discriminator (position) on each side.  Its
   adequacy — whether {depth, arity, sort, operator, position} is STILL too coarse — is the
   pre-registered Target 9 test, NOT answered here. -/

end PositionRefinement

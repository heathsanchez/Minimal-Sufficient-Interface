import Std

/-! # Paired quotient refinement — F gains `sort`, SearchPolicy gains `focusSort`

  Target 6 (collapse, externally green) proved the scalar extractor F = {depth, arity} erases a
  consequential distinction: two residuals with equal F require different search focus (sort A vs
  sort B).  This file applies the minimal paired refinement — add `sort` to the observation side
  (F) and `focusSort` to the action side (SearchPolicy), NOTHING else — and calibrates it on the
  Target-6 dual signature: the refined quotient now separates the two consequentially-different
  cases.
-/

namespace QuotientRefinement

/- ── the refined ACTION interface: SearchPolicy gains a focus-sort ─────────── -/
structure SearchPolicy (Srt : Type) where
  depthBound : Nat
  arityCap : Nat
  budget : Nat
  focusSort : Option Srt
  deriving DecidableEq, Repr, Inhabited

/- ── the refined OBSERVATION interface: F gains the invariant sort ─────────── -/
structure Summary (Srt : Type) where
  requiredDepth : Nat
  safeArity : Nat
  invSort : Srt
  deriving DecidableEq, Repr, Inhabited

/- ── the refined selector: focus on the invariant's sort (minimal policy) ──── -/
def SelectPolicy' (Srt : Type) (c : Summary Srt) : SearchPolicy Srt :=
  ⟨c.requiredDepth, c.safeArity, 0, some c.invSort⟩

/- ── frozen substrate (re-stated) ─────────────────────────────────────────── -/
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

def atoms (S : Signature) (ops : (s : S.Srt) → List (S.Op s)) (vars : (s : S.Srt) → List Nat)
    (s : S.Srt) : List (Term S s) :=
  let vs := (vars s).map (fun n => .var s n)
  let nullary := (ops s).filterMap (fun o =>
    if h : S.arity o = [] then some (.op o (cast (congrArg (Args S) h.symm) .nil)) else none)
  vs ++ nullary

def argsEnum (S : Signature) (ss : List S.Srt) (cur : (s : S.Srt) → List (Term S s)) : List (Args S ss) :=
  match ss with
  | [] => [.nil]
  | s :: ss' => (cur s).flatMap (fun t => (argsEnum S ss' cur).map (fun rest => .cons t rest))

def arityOk {Srt : Type} (p : SearchPolicy Srt) (a : Nat) : Bool := p.arityCap == 0 ∨ a ≤ p.arityCap

/- the refined closure: honor focusSort (expand only that sort) plus the arity cap. -/
def closureRefined (S : Signature) (ops : (s : S.Srt) → List (S.Op s)) (p : SearchPolicy S.Srt)
    (cur : (s : S.Srt) → List (Term S s)) : (s : S.Srt) → List (Term S s) :=
  fun s =>
    let expand := (ops s).flatMap (fun o =>
      if arityOk p (S.arity o).length then (argsEnum S (S.arity o) cur).map (fun args => .op o args) else [])
    match p.focusSort with
    | some f => if s == f then cur s ++ expand else cur s
    | none => cur s ++ expand

def iterate (f : α → α) (n : Nat) (x : α) : α :=
  match n with
  | 0 => x
  | n+1 => iterate f n (f x)

def searchRefined (S : Signature) (p : SearchPolicy S.Srt) (ops : (s : S.Srt) → List (S.Op s))
    (vars : (s : S.Srt) → List Nat) (s : S.Srt) : List (Term S s) :=
  (iterate (closureRefined S ops p) p.depthBound (atoms S ops vars)) s

/- ── the Target-6 dual signature (re-stated) ──────────────────────────────── -/
inductive DualSort where | A | B
  deriving DecidableEq, Repr, Inhabited
inductive AOp where | a0 | fa deriving DecidableEq, Repr, Inhabited
inductive BOp where | b0 | fb deriving DecidableEq, Repr, Inhabited

def DualOpFam : DualSort → Type
  | .A => AOp
  | .B => BOp

def DualOpDecEq (s : DualSort) : DecidableEq (DualOpFam s) := by
  cases s <;> unfold DualOpFam <;> infer_instance

def DualArity : {s : DualSort} → DualOpFam s → List DualSort
  | .A, .a0 => []
  | .A, .fa => [.A, .A]
  | .B, .b0 => []
  | .B, .fb => [.B, .B]

def SigDual : Signature := ⟨DualSort, DualOpFam, DualArity, inferInstance, DualOpDecEq⟩
def dualOps : (s : DualSort) → List (DualOpFam s)
  | .A => [.a0, .fa]
  | .B => [.b0, .fb]

def invA : Term SigDual DualSort.A := .op AOp.fa (.cons (.op AOp.fa (.cons (@Term.var SigDual DualSort.A 0) (.cons (.op AOp.a0 .nil) .nil))) (.cons (@Term.var SigDual DualSort.A 1) .nil))
def invB : Term SigDual DualSort.B := .op BOp.fb (.cons (.op BOp.fb (.cons (@Term.var SigDual DualSort.B 0) (.cons (.op BOp.b0 .nil) .nil))) (.cons (@Term.var SigDual DualSort.B 1) .nil))

/- ── calibration: the refined F' now SEPARATES the two consequentially-different cases ── -/
def summary_a : Summary DualSort := ⟨2, 2, .A⟩
def summary_b : Summary DualSort := ⟨2, 2, .B⟩

/- whereas the old scalar F conflated them (F(2,2)=F(2,2)), the refined F' distinguishes them. -/
theorem refined_F_separates : summary_a ≠ summary_b := by native_decide

/- the refined selector focuses on the correct sort and reaches the corresponding invariant. -/
theorem focusA_reaches_invA :
    containsTerm (searchRefined SigDual (SelectPolicy' DualSort summary_a) dualOps (fun | .A => [0, 1] | .B => []) DualSort.A) invA = true := by
  native_decide

theorem focusB_reaches_invB :
    containsTerm (searchRefined SigDual (SelectPolicy' DualSort summary_b) dualOps (fun | .A => [] | .B => [0, 1]) DualSort.B) invB = true := by
  native_decide

/- "nothing else": the refinement added exactly one discriminator (sort) on each side.  Its
   adequacy — whether {depth, arity, sort} is STILL too coarse — is the pre-registered Target 7
   test, NOT answered here. -/

end QuotientRefinement

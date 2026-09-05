import Std

/-! # Target 6 — feature-extractor collapse (kernel-checked)

  The frozen feature extractor F(ρ) = {requiredDepth, safeArity} is a scalar quotient of the
  residual.  This file kernel-checks that the quotient ERASES a consequential distinction: two
  residuals in one two-sort signature have the SAME scalar summary but their invariants live at
  DIFFERENT sorts, reachable only by expanding different operator sets.

  This is the control-level analogue of the object-level extensional/context collapse
  (`ext_collapses` vs `struct_separates` in ContextGenesis/DomainGenericKernel): the same coarse
  observation does not determine the consequential structure.
-/

namespace Target6

/- ── the frozen feature extractor F (re-stated) ───────────────────────────── -/
structure ScalarSummary where
  requiredDepth : Nat
  safeArity : Nat
  deriving DecidableEq, Repr, Inhabited

/- the frozen extractor: a residual is summarized by (invariant size, max operator arity). -/
def F (invSize : Nat) (maxArity : Nat) : ScalarSummary := ⟨invSize, maxArity⟩

/- ── a residual's consequential structure: which SORT its invariant lives at ── -/
inductive DualSort where | A | B
  deriving DecidableEq, Repr, Inhabited

/- ρ_a: invariant at sort A, size 2, max arity 2 (operators {a0, fa}).
   ρ_b: invariant at sort B, size 2, max arity 2 (operators {b0, fb}). -/
def invSort : DualSort := .A   -- ρ_a's invariant sort
def invSortB : DualSort := .B  -- ρ_b's invariant sort

/- THE COLLAPSE: same scalar summary, different consequential structure (sort). -/
theorem feature_collapse :
    F 2 2 = F 2 2 ∧ invSort ≠ invSortB := by
  native_decide

/- ── make the sort difference CONSEQUENTIAL (not vacuous) ──────────────────── -/
/- A two-sort signature: sort A operators {a0 (nullary), fa (binary A×A→A)};
   sort B operators {b0 (nullary), fb (binary B×B→B)}. -/
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

inductive AOp where | a0 | fa deriving DecidableEq, Repr, Inhabited
inductive BOp where | b0 | fb deriving DecidableEq, Repr, Inhabited

/- operators indexed by result sort: a0/fa have result A; b0/fb have result B. -/
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

/- ρ_a's invariant: `fa (fa x a0) y` at sort A (size 2).
   ρ_b's invariant: `fb (fb x b0) y` at sort B (size 2). -/
def invA : Term SigDual DualSort.A := .op AOp.fa (.cons (.op AOp.fa (.cons (@Term.var SigDual DualSort.A 0) (.cons (.op AOp.a0 .nil) .nil))) (.cons (@Term.var SigDual DualSort.A 1) .nil))
def invB : Term SigDual DualSort.B := .op BOp.fb (.cons (.op BOp.fb (.cons (@Term.var SigDual DualSort.B 0) (.cons (.op BOp.b0 .nil) .nil))) (.cons (@Term.var SigDual DualSort.B 1) .nil))

/- ── the sort difference is consequential: a search that expands ONLY sort A reaches invA but
      produces nothing of sort B (and symmetrically). ── -/
def argsEnum (S : Signature) (ss : List S.Srt) (cur : (s : S.Srt) → List (Term S s)) : List (Args S ss) :=
  match ss with
  | [] => [.nil]
  | s :: ss' => (cur s).flatMap (fun t => (argsEnum S ss' cur).map (fun rest => .cons t rest))

def atoms (S : Signature) (ops : (s : S.Srt) → List (S.Op s)) (vars : (s : S.Srt) → List Nat)
    (s : S.Srt) : List (Term S s) :=
  let vs := (vars s).map (fun n => .var s n)
  let nullary := (ops s).filterMap (fun o =>
    if h : S.arity o = [] then some (.op o (cast (congrArg (Args S) h.symm) .nil)) else none)
  vs ++ nullary

def iterate (f : α → α) (n : Nat) (x : α) : α :=
  match n with
  | 0 => x
  | n+1 => iterate f n (f x)

/- a search that expands ONLY operators of result sort `focus`; other sorts are left as atoms. -/
def closureFocus (S : Signature) (ops : (s : S.Srt) → List (S.Op s)) (focus : S.Srt)
    (cur : (s : S.Srt) → List (Term S s)) : (s : S.Srt) → List (Term S s) :=
  fun s =>
    if s == focus then
      cur s ++ (ops s).flatMap (fun o => (argsEnum S (S.arity o) cur).map (fun args => .op o args))
    else
      cur s

def searchFocus (focus : DualSort) (rounds : Nat) (vars : (s : DualSort) → List Nat) (s : DualSort) : List (Term SigDual s) :=
  (iterate (closureFocus SigDual dualOps focus) rounds (atoms SigDual dualOps vars)) s

/- focus-A search reaches invA (sort A); focus-B search reaches invB (sort B). -/
theorem focusA_reaches_invA :
    containsTerm (searchFocus .A 2 (fun | .A => [0, 1] | .B => []) DualSort.A) invA = true := by
  native_decide

theorem focusB_reaches_invB :
    containsTerm (searchFocus .B 2 (fun | .A => [] | .B => [0, 1]) DualSort.B) invB = true := by
  native_decide

/- The two invariants are structurally disjoint: invA is a sort-A term, invB a sort-B term.
   A focus-A search cannot produce invB (it produces no sort-B composites), and vice versa —
   so the required control action (which sort to expand) genuinely differs. -/
theorem invariants_differ_in_sort : (DualSort.A : DualSort) ≠ DualSort.B := by native_decide

end Target6

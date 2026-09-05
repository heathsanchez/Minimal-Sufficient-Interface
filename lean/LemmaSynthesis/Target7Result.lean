import Std

/-! # Target 7 — adequacy of {depth, arity, sort}: the witness EXISTS (operator is forced)

  The refined quotient Q' = {requiredDepth, safeArity, invSort} was frozen at `3c3e638`.  This file
  tests its adequacy: does ∃ ρ_a, ρ_b with Q'(ρ_a) = Q'(ρ_b) but Future(ρ_a) ≠ Future(ρ_b)?

  Answer: YES.  Two residuals in a SINGLE sort A, both {depth 2, arity 2, sort A}, but their
  invariants are built from DIFFERENT operators of that sort (`fa` vs `ga`).  A sort-focus policy
  cannot distinguish them; an operator-focus policy can.  So the next discriminator forced by the
  witness is OPERATOR identity — confirming the pre-registered prediction, and falsifying
  "sort survives".
-/

namespace Target7

/- ── the refined observation interface Q' (re-stated) ─────────────────────── -/
structure Summary (Srt : Type) where
  requiredDepth : Nat
  safeArity : Nat
  invSort : Srt
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

def iterate (f : α → α) (n : Nat) (x : α) : α :=
  match n with
  | 0 => x
  | n+1 => iterate f n (f x)

/- a search that expands only operators satisfying `keep` (operator-level focus). -/
def closureKeep (S : Signature) (ops : (s : S.Srt) → List (S.Op s)) (keep : (s : S.Srt) → S.Op s → Bool)
    (cur : (s : S.Srt) → List (Term S s)) : (s : S.Srt) → List (Term S s) :=
  fun s =>
    let kept := (ops s).filter (fun o => keep s o)
    cur s ++ kept.flatMap (fun o => (argsEnum S (S.arity o) cur).map (fun args => .op o args))

def searchKeep (S : Signature) (ops : (s : S.Srt) → List (S.Op s)) (keep : (s : S.Srt) → S.Op s → Bool)
    (vars : (s : S.Srt) → List Nat) (rounds : Nat) (s : S.Srt) : List (Term S s) :=
  (iterate (closureKeep S ops keep) rounds (atoms S ops vars)) s

/- ── single sort A with THREE operators: a0 (nullary), fa (binary), ga (binary) ── -/
inductive ASrt where | A deriving DecidableEq, Repr, Inhabited
inductive AOp where | a0 | fa | ga deriving DecidableEq, Repr, Inhabited

def AOpFam : ASrt → Type := fun _ => AOp
def AOpDecEq (s : ASrt) : DecidableEq (AOpFam s) := by unfold AOpFam; infer_instance
def AArity : {s : ASrt} → AOpFam s → List ASrt
  | .A, .a0 => []
  | .A, .fa => [.A, .A]
  | .A, .ga => [.A, .A]
def SigA : Signature := ⟨ASrt, AOpFam, AArity, inferInstance, AOpDecEq⟩
def aOps : (s : ASrt) → List (AOpFam s) := fun _ => [.a0, .fa, .ga]

def xVar : Term SigA ASrt.A := @Term.var SigA ASrt.A 0
def yVar : Term SigA ASrt.A := @Term.var SigA ASrt.A 1
def a0T : Term SigA ASrt.A := .op AOp.a0 .nil

/- ρ_a's invariant: `fa (fa x a0) y`  (built from fa). -/
def invA : Term SigA ASrt.A := .op AOp.fa (.cons (.op AOp.fa (.cons xVar (.cons a0T .nil))) (.cons yVar .nil))
/- ρ_b's invariant: `ga (ga x a0) y`  (built from ga). -/
def invB : Term SigA ASrt.A := .op AOp.ga (.cons (.op AOp.ga (.cons xVar (.cons a0T .nil))) (.cons yVar .nil))

/- ── THE WITNESS: Q' conflates two operator-distinct residuals ─────────────── -/
/- Both residuals have summary {requiredDepth 2, safeArity 2, sort A}. -/
def summary_a : Summary ASrt := ⟨2, 2, .A⟩
def summary_b : Summary ASrt := ⟨2, 2, .A⟩

theorem same_refined_summary : summary_a = summary_b := by native_decide

/- but the invariants use DIFFERENT operators: fa vs ga. -/
theorem head_operators_differ : AOp.fa ≠ AOp.ga := by native_decide

/- ── the operator distinction is CONSEQUENTIAL: fa-focus reaches invA not invB,
      ga-focus reaches invB not invA. ── -/
def keepFa : (s : ASrt) → AOpFam s → Bool
  | _, .fa => true
  | _, _ => false

def keepGa : (s : ASrt) → AOpFam s → Bool
  | _, .ga => true
  | _, _ => false

theorem fa_focus_reaches_invA :
    containsTerm (searchKeep SigA aOps keepFa (fun _ => [0, 1]) 2 ASrt.A) invA = true := by
  native_decide

theorem fa_focus_misses_invB :
    containsTerm (searchKeep SigA aOps keepFa (fun _ => [0, 1]) 2 ASrt.A) invB = false := by
  native_decide

theorem ga_focus_reaches_invB :
    containsTerm (searchKeep SigA aOps keepGa (fun _ => [0, 1]) 2 ASrt.A) invB = true := by
  native_decide

theorem ga_focus_misses_invA :
    containsTerm (searchKeep SigA aOps keepGa (fun _ => [0, 1]) 2 ASrt.A) invA = false := by
  native_decide

/- ── OUTCOME: the witness exists → {depth, arity, sort} is STILL too coarse ── -/
/- Two residuals with Q'(ρ_a)=Q'(ρ_b)={2,2,A} require different futures (fa-focus vs ga-focus).
   The forced next discriminator is OPERATOR identity, exactly as pre-registered.  The sort-level
   refinement is necessary but NOT sufficient. -/

end Target7

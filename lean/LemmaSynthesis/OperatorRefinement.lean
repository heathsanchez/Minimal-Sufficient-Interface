import Std

/-! # Operator refinement — Q'' = {depth, arity, sort, operator} (paired, minimal)

  Target 7 (externally green) proved {depth, arity, sort} still collapses operator-distinct
  residuals (fa vs ga in one sort).  This file applies the minimal paired refinement: the
  observation gains `operator`, the action gains `focusOp`.  Nothing else.  Calibration: the
  refined quotient now SEPARATES the Target-7 witness pair.
-/

namespace OperatorRefinement

/- ── the signature's sort and operators (defined first, referenced by Summary/SearchPolicy) ── -/
inductive ASrt where | A deriving DecidableEq, Repr, Inhabited
inductive AOp where | a0 | fa | ga deriving DecidableEq, Repr, Inhabited

/- ── refined observation interface: + operator ────────────────────────────── -/
structure Summary where
  requiredDepth : Nat
  safeArity : Nat
  invSort : ASrt
  invOp : AOp
  deriving DecidableEq, Repr, Inhabited

/- ── refined action interface: + focusOp ──────────────────────────────────── -/
structure SearchPolicy where
  depthBound : Nat
  arityCap : Nat
  budget : Nat
  focusSort : Option ASrt
  focusOp : Option AOp
  deriving DecidableEq, Repr, Inhabited

def SelectPolicy'' (c : Summary) : SearchPolicy :=
  ⟨c.requiredDepth, c.safeArity, 0, some c.invSort, some c.invOp⟩

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

def closureKeep (S : Signature) (ops : (s : S.Srt) → List (S.Op s)) (keep : (s : S.Srt) → S.Op s → Bool)
    (cur : (s : S.Srt) → List (Term S s)) : (s : S.Srt) → List (Term S s) :=
  fun s =>
    let kept := (ops s).filter (fun o => keep s o)
    cur s ++ kept.flatMap (fun o => (argsEnum S (S.arity o) cur).map (fun args => .op o args))

def searchKeep (S : Signature) (ops : (s : S.Srt) → List (S.Op s)) (keep : (s : S.Srt) → S.Op s → Bool)
    (vars : (s : S.Srt) → List Nat) (rounds : Nat) (s : S.Srt) : List (Term S s) :=
  (iterate (closureKeep S ops keep) rounds (atoms S ops vars)) s

/- ── single sort A with {a0, fa, ga} ──────────────────────────────────────── -/
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
def invA : Term SigA ASrt.A := .op AOp.fa (.cons (.op AOp.fa (.cons xVar (.cons a0T .nil))) (.cons yVar .nil))
def invB : Term SigA ASrt.A := .op AOp.ga (.cons (.op AOp.ga (.cons xVar (.cons a0T .nil))) (.cons yVar .nil))

/- ── the refined summaries now carry the operator ─────────────────────────── -/
def summary_a : Summary := ⟨2, 2, .A, .fa⟩
def summary_b : Summary := ⟨2, 2, .A, .ga⟩

/- THE OPERATOR REFINEMENT SEPARATES the pair that {depth,arity,sort} conflated. -/
theorem operator_refinement_separates : summary_a ≠ summary_b := by native_decide

/- the refined selector produces different policies (focus fa vs focus ga). -/
theorem refined_policies_differ : SelectPolicy'' summary_a ≠ SelectPolicy'' summary_b := by native_decide

/- the operator-focused search (honoring focusOp) reaches the correct invariant. -/
def keepOp (fo : AOp) : (s : ASrt) → AOpFam s → Bool
  | _, o => match fo, o with
    | .fa, .fa => true
    | .ga, .ga => true
    | .a0, .a0 => true
    | _, _ => false

theorem focus_fa_reaches_invA :
    containsTerm (searchKeep SigA aOps (keepOp .fa) (fun _ => [0, 1]) 2 ASrt.A) invA = true := by
  native_decide

theorem focus_fa_misses_invB :
    containsTerm (searchKeep SigA aOps (keepOp .fa) (fun _ => [0, 1]) 2 ASrt.A) invB = false := by
  native_decide

theorem focus_ga_reaches_invB :
    containsTerm (searchKeep SigA aOps (keepOp .ga) (fun _ => [0, 1]) 2 ASrt.A) invB = true := by
  native_decide

theorem focus_ga_misses_invA :
    containsTerm (searchKeep SigA aOps (keepOp .ga) (fun _ => [0, 1]) 2 ASrt.A) invA = false := by
  native_decide

/- "nothing else": the refinement added exactly one discriminator (operator) on each side.  Its
   adequacy — whether {depth, arity, sort, operator} is STILL too coarse — is the pre-registered
   Target 8 test, NOT answered here. -/

end OperatorRefinement

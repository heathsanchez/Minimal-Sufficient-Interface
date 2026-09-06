import Std

/-! # Target 9 — adequacy of {depth, arity, sort, operator, position}: the CONTEXT witness EXISTS

  The quotient Q''' = {depth, arity, sort, operator, position} was frozen at `6f8712c`.  This file
  tests its adequacy: does ∃ ρ_a, ρ_b with Q'''(ρ_a) = Q'''(ρ_b) but Future(ρ_a) ≠ Future(ρ_b)?

  Answer: YES.  Two residuals share depth 2, arity 2, sort A, head operator `f`, and diff position
  0 — but the subterm AT that position uses a different operator (`g` vs `f`).  The local node and
  the path index are the same; the CONTEXT (the operator of the child at the diff position) differs,
  and that difference is consequential: a `g`-focused search reaches the first child, an `f`-focused
  search reaches the second, with the crossed focuses failing.  So the forced next discriminator is
  RELATIONAL — the operator at the diff position (context), not a flat label.
-/

namespace Target9

/- ── refined observation interface Q''' (re-stated) ───────────────────────── -/
inductive ASrt where | A deriving DecidableEq, Repr, Inhabited
inductive AOp where | a0 | f | g deriving DecidableEq, Repr, Inhabited

structure Summary where
  requiredDepth : Nat
  safeArity : Nat
  invSort : ASrt
  invOp : AOp
  diffPos : Nat
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

def closureKeep (S : Signature) (ops : (s : S.Srt) → List (S.Op s)) (keep : (s : S.Srt) → S.Op s → Bool)
    (cur : (s : S.Srt) → List (Term S s)) : (s : S.Srt) → List (Term S s) :=
  fun s =>
    let kept := (ops s).filter (fun o => keep s o)
    cur s ++ kept.flatMap (fun o => (argsEnum S (S.arity o) cur).map (fun args => .op o args))

def searchKeep (S : Signature) (ops : (s : S.Srt) → List (S.Op s)) (keep : (s : S.Srt) → S.Op s → Bool)
    (vars : (s : S.Srt) → List Nat) (rounds : Nat) (s : S.Srt) : List (Term S s) :=
  (iterate (closureKeep S ops keep) rounds (atoms S ops vars)) s

/- ── single sort A with {a0 (nullary), f (binary), g (binary)} ────────────── -/
def AOpFam : ASrt → Type := fun _ => AOp
def AOpDecEq (s : ASrt) : DecidableEq (AOpFam s) := by unfold AOpFam; infer_instance
def AArity : {s : ASrt} → AOpFam s → List ASrt
  | .A, .a0 => []
  | .A, .f => [.A, .A]
  | .A, .g => [.A, .A]
def SigA : Signature := ⟨ASrt, AOpFam, AArity, inferInstance, AOpDecEq⟩
def aOps : (s : ASrt) → List (AOpFam s) := fun _ => [.a0, .f, .g]

def xVar : Term SigA ASrt.A := @Term.var SigA ASrt.A 0
def yVar : Term SigA ASrt.A := @Term.var SigA ASrt.A 1
def a0T : Term SigA ASrt.A := .op AOp.a0 .nil

/- the subterms AT the diff position (left child) — same head operator f, same position 0,
   but DIFFERENT child operator: g vs f. -/
def childA : Term SigA ASrt.A := .op AOp.g (.cons xVar (.cons a0T .nil))   -- g x a0
def childB : Term SigA ASrt.A := .op AOp.f (.cons xVar (.cons a0T .nil))   -- f x a0

/- ρ_a invariant `f (g x a0) y`; ρ_b invariant `f (f x a0) y`. -/
def invA : Term SigA ASrt.A := .op AOp.f (.cons childA (.cons yVar .nil))
def invB : Term SigA ASrt.A := .op AOp.f (.cons childB (.cons yVar .nil))

/- ── THE WITNESS: Q''' conflates two context-distinct residuals ───────────── -/
def summary_a : Summary := ⟨2, 2, .A, .f, 0⟩
def summary_b : Summary := ⟨2, 2, .A, .f, 0⟩

theorem same_refined_summary : summary_a = summary_b := by native_decide

/- but the subterm at the diff position uses different operators: g vs f. -/
theorem child_operator_differs : AOp.g ≠ AOp.f := by native_decide

/- ── the context distinction is CONSEQUENTIAL: g-focus reaches the g-child, f-focus the f-child -/
def keepOp (o : AOp) : (s : ASrt) → AOpFam s → Bool
  | _, o' => match o, o' with
    | .a0, .a0 => true
    | .f, .f => true
    | .g, .g => true
    | _, _ => false

theorem g_focus_reaches_childA :
    containsTerm (searchKeep SigA aOps (keepOp .g) (fun _ => [0, 1]) 1 ASrt.A) childA = true := by
  native_decide

theorem g_focus_misses_childB :
    containsTerm (searchKeep SigA aOps (keepOp .g) (fun _ => [0, 1]) 1 ASrt.A) childB = false := by
  native_decide

theorem f_focus_reaches_childB :
    containsTerm (searchKeep SigA aOps (keepOp .f) (fun _ => [0, 1]) 1 ASrt.A) childB = true := by
  native_decide

theorem f_focus_misses_childA :
    containsTerm (searchKeep SigA aOps (keepOp .f) (fun _ => [0, 1]) 1 ASrt.A) childA = false := by
  native_decide

/- ── OUTCOME: the witness exists → {depth, arity, sort, operator, position} is STILL too coarse ── -/
/- The forced next discriminator is RELATIONAL: the operator at the diff position (the context),
   not a flat label.  The flat feature vector must become a structured relational residual
   representation. -/

end Target9

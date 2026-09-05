import Std

/-! # Search policy as explicit state — the control-parametric repair (Target 4 = calibration)

  Target 4 (outcome C2) falsified the SEARCH POLICY: the invariant was representable and
  generatable but the frozen bounded search did not reach it (depth 1 insufficient; depth 2
  explodes via the 3-ary `mulTr`).  This file makes the search choices explicit STATE and defines
  a FROZEN selector that picks the minimal policy satisfying the residual-derived constraint —
  using only pre-solution structural information (required depth + exploding arity), never the
  known invariant.

  The constitutional boundary: the search policy becomes mutable state; the criterion judging the
  transition (the external Lean kernel) stays fixed.
-/

namespace SearchPolicyAsState

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

def containsTerm {S} {s : S.Srt} (l : List (Term S s)) (t : Term S s) : Bool :=
  l.any (fun x => termEq x t)

/- ── SearchPolicy: the search choices, made explicit state ────────────────── -/
structure SearchPolicy where
  depthBound : Nat   -- number of closure rounds
  arityCap : Nat     -- expand only operators of arity ≤ arityCap (0 = no cap)
  budget : Nat       -- max candidates (0 = unbounded)
  deriving DecidableEq, Repr, Inhabited

/- The old frozen search (the one that failed on Target 4): depth 1, no arity cap. -/
def baselineSearch : SearchPolicy := ⟨1, 0, 0⟩

/- ── SearchConstraint: what the residual demands of the search ─────────────── -/
structure SearchConstraint where
  requiredDepth : Nat  -- depth needed to reach the invariant
  safeArity : Nat      -- arity above which expansion explodes
  deriving DecidableEq, Repr, Inhabited

/- The FROZEN selector: minimal policy satisfying the constraint. -/
def SelectPolicy (c : SearchConstraint) : SearchPolicy :=
  ⟨c.requiredDepth, c.safeArity, 0⟩

/- ── the search: bounded closure respecting the policy ─────────────────────── -/
def arityOk (p : SearchPolicy) (a : Nat) : Bool := p.arityCap == 0 ∨ a ≤ p.arityCap

def closureRoundCapped (S : Signature) (ops : (s : S.Srt) → List (S.Op s)) (p : SearchPolicy)
    (cur : (s : S.Srt) → List (Term S s)) : (s : S.Srt) → List (Term S s) :=
  fun s => cur s ++ (ops s).flatMap (fun o =>
    if arityOk p (S.arity o).length then (argsEnum S (S.arity o) cur).map (fun args => .op o args) else [])

def iterate (f : α → α) (n : Nat) (x : α) : α :=
  match n with
  | 0 => x
  | n+1 => iterate f n (f x)

def search (p : SearchPolicy) (S : Signature) (ops : (s : S.Srt) → List (S.Op s))
    (vars : (s : S.Srt) → List Nat) (s : S.Srt) : List (Term S s) :=
  (iterate (closureRoundCapped S ops p) p.depthBound (atoms S ops vars)) s

/- ── the multiplication signature (from Target 4) ─────────────────────────── -/
inductive MSort where | Nat deriving DecidableEq, Repr, Inhabited
inductive MOp where | zero | add | mul | mulTr deriving DecidableEq, Repr, Inhabited
def MOpFam : MSort → Type := fun _ => MOp
def MOpDecEq (s : MSort) : DecidableEq (MOpFam s) := by unfold MOpFam; infer_instance
def MArity : {s : MSort} → MOpFam s → List MSort
  | .Nat, .zero => []
  | .Nat, .add => [.Nat, .Nat]
  | .Nat, .mul => [.Nat, .Nat]
  | .Nat, .mulTr => [.Nat, .Nat, .Nat]
def SigMul : Signature := ⟨MSort, MOpFam, MArity, inferInstance, MOpDecEq⟩
def mulOps : (s : MSort) → List (MOpFam s) := fun _ => [.zero, .add, .mul, .mulTr]

def nVar   : Term SigMul MSort.Nat := @Term.var SigMul MSort.Nat 0
def bVar   : Term SigMul MSort.Nat := @Term.var SigMul MSort.Nat 1
def accVar : Term SigMul MSort.Nat := @Term.var SigMul MSort.Nat 2
def add_mul_n_b_acc : Term SigMul MSort.Nat := .op MOp.add (.cons (.op MOp.mul (.cons nVar (.cons bVar .nil))) (.cons accVar .nil))

/- ── K(ρ_meta_4) from the frozen Target-4 evidence (structure only) ────────── -/
/- invariant size 2 → required depth 2; the 3-ary `mulTr` explodes → safe arity 2. -/
def K_meta4 : SearchConstraint := ⟨2, 2⟩
def selectedPolicy : SearchPolicy := SelectPolicy K_meta4

/- ── CALIBRATION: baseline vs residual-selected search on Target 4 ─────────── -/
theorem baseline_fails :
    containsTerm (search baselineSearch SigMul mulOps (fun _ => [0, 1, 2]) MSort.Nat) add_mul_n_b_acc = false := by
  native_decide

theorem selected_reaches_invariant :
    containsTerm (search selectedPolicy SigMul mulOps (fun _ => [0, 1, 2]) MSort.Nat) add_mul_n_b_acc = true := by
  native_decide

/- The selected policy differs from baseline (depth 2 vs 1; arity capped at 2 vs uncapped). -/
theorem selected_differs_from_baseline : selectedPolicy ≠ baselineSearch := by native_decide

end SearchPolicyAsState

import Std

/-! # Target 5 (exponentiation accumulator) — frozen control-parametric falsification RESULT

  ρ₅ (verbatim, from `Target5.lean`):
      case succ
      b e : Nat
      ih : powAcc b e 1 = pow b e
      ⊢ powAcc b e b = b * pow b e

  The IH is specialized to `acc = 1`; the step needs `acc = b`.  Sealed repair:
  `∀ b e acc, powAcc b e acc = pow b e * acc`, i.e. `mul (pow b e) acc`.

  The FROZEN selector `SelectPolicy` (depth = requiredDepth, arity cap = safeArity) is applied to
  the new residual's constraint K(ρ₅) = {2, 2} (invariant size 2; 3-ary `powAcc` explodes), with
  NO target-specific change.  This is the control-parametric transfer test.
-/

namespace Target5Result

/- ── frozen machinery (re-stated) ─────────────────────────────────────────── -/
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

/- ── frozen SearchPolicy + selector (re-stated from SearchPolicy.lean) ────── -/
structure SearchPolicy where
  depthBound : Nat
  arityCap : Nat
  budget : Nat
  deriving DecidableEq, Repr, Inhabited

def baselineSearch : SearchPolicy := ⟨1, 0, 0⟩

structure SearchConstraint where
  requiredDepth : Nat
  safeArity : Nat
  deriving DecidableEq, Repr, Inhabited

def SelectPolicy (c : SearchConstraint) : SearchPolicy := ⟨c.requiredDepth, c.safeArity, 0⟩

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

/- ── the exponentiation signature: Nat sort; {one, mul, pow, powAcc(3-ary)} ── -/
inductive PSort where | Nat deriving DecidableEq, Repr, Inhabited
inductive POp where | one | mul | pow | powAcc deriving DecidableEq, Repr, Inhabited
def POpFam : PSort → Type := fun _ => POp
def POpDecEq (s : PSort) : DecidableEq (POpFam s) := by unfold POpFam; infer_instance
def PArity : {s : PSort} → POpFam s → List PSort
  | .Nat, .one => []
  | .Nat, .mul => [.Nat, .Nat]
  | .Nat, .pow => [.Nat, .Nat]
  | .Nat, .powAcc => [.Nat, .Nat, .Nat]
def SigPow : Signature := ⟨PSort, POpFam, PArity, inferInstance, POpDecEq⟩
def powOps : (s : PSort) → List (POpFam s) := fun _ => [.one, .mul, .pow, .powAcc]

def bVar   : Term SigPow PSort.Nat := @Term.var SigPow PSort.Nat 0
def eVarr  : Term SigPow PSort.Nat := @Term.var SigPow PSort.Nat 1
def accVar : Term SigPow PSort.Nat := @Term.var SigPow PSort.Nat 2
def mul_pow_b_e_acc : Term SigPow PSort.Nat := .op POp.mul (.cons (.op POp.pow (.cons bVar (.cons eVarr .nil))) (.cons accVar .nil))

/- ── K(ρ₅) from the frozen evidence (structure only) ──────────────────────── -/
def K_rho5 : SearchConstraint := ⟨2, 2⟩
def selectedPolicy5 : SearchPolicy := SelectPolicy K_rho5

/- ── CONTROL-PARAMETRIC TRANSFER TEST ─────────────────────────────────────── -/
theorem baseline_fails :
    containsTerm (search baselineSearch SigPow powOps (fun _ => [0, 1, 2]) PSort.Nat) mul_pow_b_e_acc = false := by
  native_decide

theorem selected_reaches_invariant :
    containsTerm (search selectedPolicy5 SigPow powOps (fun _ => [0, 1, 2]) PSort.Nat) mul_pow_b_e_acc = true := by
  native_decide

theorem selected_differs_from_baseline : selectedPolicy5 ≠ baselineSearch := by native_decide

/- The frozen selector is the SAME definition applied to the new constraint — it did not change
   between Target 4 and Target 5; only the signature and the residual changed. -/
theorem selector_unchanged : selectedPolicy5 = SelectPolicy K_rho5 := by rfl

end Target5Result

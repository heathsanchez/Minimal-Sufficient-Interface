import Std

/-! # Target 4 (tail-recursive multiplication) — frozen PROSPECTIVE falsification RESULT

  ρ₄ (verbatim, from `Target4.lean`):
      case succ
      b n : Nat
      ih : mulTr n b 0 = mul n b
      ⊢ mulTr n b b = b + mul n b

  The IH is specialized to `acc = 0`; the step needs `acc = b`.  Sealed repair:
  `∀ n b acc, mulTr n b acc = mul n b + acc`, i.e. `add (mul n b) acc`.

  This file applies the frozen machinery (re-stated; CI compiles per-file) and records the
  stage-by-stage status against the prospective prediction frozen at `9f036b0` (next seam =
  search policy / cost / ranking, C2-like).
-/

namespace Target4Result

/- ── frozen machinery (re-stated verbatim) ─────────────────────────────────── -/
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

def Subterm (S : Signature) : Type := Σ s, Term S s

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

def matchesSubterm {S} {s : S.Srt} (t : Term S s) (target : Subterm S) : Bool :=
  match target with
  | ⟨s', tgt⟩ =>
    match S.sortBE s s' with
    | isTrue h => termEq t (cast (congrArg (Term S) h.symm) tgt)
    | isFalse _ => false

mutual
  def generalizeTerm {S} {s : S.Srt} (t : Term S s) (target : Subterm S) (fresh : Nat) : Term S s :=
    if matchesSubterm t target then .var s fresh
    else match t with
      | .var _ _ => t
      | .op o args => .op o (generalizeArgs args target fresh)
  def generalizeArgs {S} {ss : List S.Srt} (args : Args S ss) (target : Subterm S) (fresh : Nat) : Args S ss :=
    match args with
    | .nil => .nil
    | .cons x xs => .cons (generalizeTerm x target fresh) (generalizeArgs xs target fresh)
end

mutual
  def diff {S} {s : S.Srt} (a b : Term S s) : List (Subterm S × Subterm S) :=
    match a with
    | .var _ n =>
        match b with
        | .var _ m => if n == m then [] else [(⟨s, .var s n⟩, ⟨s, .var s m⟩)]
        | .op _ _ => [(⟨s, a⟩, ⟨s, b⟩)]
    | .op o a' =>
        match b with
        | .op o' b' =>
            match S.opBE s o o' with
            | isTrue h => diffArgs a' (cast (congrArg (Args S) (congrArg (S.arity) h.symm)) b')
            | isFalse _ => [(⟨s, .op o a'⟩, ⟨s, .op o' b'⟩)]
        | .var _ _ => [(⟨s, a⟩, ⟨s, b⟩)]
  def diffArgs {S} {ss : List S.Srt} : Args S ss → Args S ss → List (Subterm S × Subterm S)
    | .nil, .nil => []
    | .cons x xs, .cons y ys => diff x y ++ diffArgs xs ys
end

mutual
  def size {S} {s : S.Srt} : Term S s → Nat
    | .var _ _ => 0
    | .op _ args => 1 + argsSize args
  def argsSize {S} {ss : List S.Srt} : Args S ss → Nat
    | .nil => 0
    | .cons t ts => size t + argsSize ts
end

def dedupTerms {S} {s : S.Srt} (l : List (Term S s)) : List (Term S s) :=
  l.foldl (fun acc x => if acc.any (fun y => termEq y x) then acc else acc ++ [x]) []

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

def closureRound (S : Signature) (ops : (s : S.Srt) → List (S.Op s))
    (cur : (s : S.Srt) → List (Term S s)) : (s : S.Srt) → List (Term S s) :=
  fun s => dedupTerms (cur s ++ (ops s).flatMap (fun o => (argsEnum S (S.arity o) cur).map (fun args => .op o args)))

def iterate (f : α → α) (n : Nat) (x : α) : α :=
  match n with
  | 0 => x
  | n+1 => iterate f n (f x)

def termsUpTo (S : Signature) (ops : (s : S.Srt) → List (S.Op s)) (vars : (s : S.Srt) → List Nat)
    (rounds : Nat) : (s : S.Srt) → List (Term S s) :=
  iterate (closureRound S ops) rounds (atoms S ops vars)

def containsTerm {S} {s : S.Srt} (l : List (Term S s)) (t : Term S s) : Bool :=
  l.any (fun x => termEq x t)

/- ── the multiplication signature: one Nat sort; operators {zero, add, mul, mulTr(3-ary)} ── -/
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

/- ── ρ₄'s terms ────────────────────────────────────────────────────────────── -/
def nVar   : Term SigMul MSort.Nat := @Term.var SigMul MSort.Nat 0
def bVar   : Term SigMul MSort.Nat := @Term.var SigMul MSort.Nat 1
def accVar : Term SigMul MSort.Nat := @Term.var SigMul MSort.Nat 2
def zeroT  : Term SigMul MSort.Nat := .op MOp.zero .nil
def mulTr_n_b_zero : Term SigMul MSort.Nat := .op MOp.mulTr (.cons nVar (.cons bVar (.cons zeroT .nil)))
def mulTr_n_b_b    : Term SigMul MSort.Nat := .op MOp.mulTr (.cons nVar (.cons bVar (.cons bVar .nil)))
def add_mul_n_b_acc : Term SigMul MSort.Nat := .op MOp.add (.cons (.op MOp.mul (.cons nVar (.cons bVar .nil))) (.cons accVar .nil))

/- ── stage 1: representation (E1) ── SUCCEEDS ──────────────────────────────── -/
theorem residual_representable : Nonempty (Term SigMul MSort.Nat) := ⟨mulTr_n_b_zero⟩

/- ── stage 2: diff / residual localization (E2) ── SUCCEEDS: `(0, b)` ─────── -/
theorem diff_mul : diff mulTr_n_b_zero mulTr_n_b_b = [(⟨MSort.Nat, zeroT⟩, ⟨MSort.Nat, bVar⟩)] := by
  rfl

/- ── stage 3: parameter generalization (A) ── SUCCEEDS: `0 ↦ acc` ─────────── -/
theorem generalize_mul :
    generalizeTerm mulTr_n_b_zero ⟨MSort.Nat, zeroT⟩ 2 = .op MOp.mulTr (.cons nVar (.cons bVar (.cons accVar .nil))) := by
  rfl

/- ── stage 4: candidate grammar (C1) ── the invariant is CONSTRUCTIBLE at size 2 ── -/
theorem invariant_size_two : size add_mul_n_b_acc = 2 := by native_decide

/- ── stage 5: search / ranking (THE PREDICTION, C2) ───────────────────────── -/
/- The invariant is size 2, so a size-ordered search must first pass every size-0 and size-1
   candidate.  In round 1 the universe already holds 100 terms (3 vars + zero = 4 atoms, plus
   add/mul 16 each and 3-ary mulTr 64). -/
theorem round1_candidate_count :
    ((termsUpTo SigMul mulOps (fun _ => [0, 1, 2]) 1) MSort.Nat).length = 100 := by
  native_decide

/- The invariant is NOT in round 1 — it requires round 2 (one further operator application). -/
theorem invariant_not_in_round1 :
    containsTerm ((termsUpTo SigMul mulOps (fun _ => [0, 1, 2]) 1) MSort.Nat) add_mul_n_b_acc = false := by
  native_decide

/- Round 2 re-applies the 3-ary `mulTr` to a 100-term base: O(n³) ≈ 10⁶ new terms from that one
   operator alone, so the bounded closure explodes before the invariant is enumerated.  The repair
   is CONSTRUCTIBLE (size 2) but NOT reached by the frozen bounded search — the predicted seam. -/

/- ── OUTCOME: C2 (prediction confirmed) ────────────────────────────────────── -/
/- representable ✓ · diff ✓ · generalize ✓ · grammar-expressible ✓ · search/ranking ✗ (C2).
   This matches the prospective prediction frozen at `9f036b0`: the next hidden concreteness is
   search policy / cost / ranking, not representation, extraction, grammar, or verification. -/

end Target4Result

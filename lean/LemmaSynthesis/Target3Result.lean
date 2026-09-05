import Std

/-! # Target 3 (tree-flatten accumulator) — frozen falsification RESULT

  The pre-registered Target 3 was run against the signature-generic machinery frozen at `d54c07b`.
  ρ₃ (verbatim, from `Target3.lean`):

      case node
      l r : Tree
      ihl : flattenAcc l [] = flatten l
      ihr : flattenAcc r [] = flatten r
      ⊢ flattenAcc l (flattenAcc r []) = flatten l ++ flatten r

  The IH is specialized to `acc = []` while the `node` step threads a non-`[]` accumulator
  (`flattenAcc r []`, i.e. `flatten r`) through TWO recursive calls.  The sealed repair is
  `∀ t acc, flattenAcc t acc = flatten t ++ acc`.

  This file re-states the frozen signature-generic operators verbatim (CI compiles per-file, no
  `.olean`), defines the tree-flatten signature as the target-neutral adapter, and records the
  outcome against the pre-registered grades.
-/

namespace Target3Result

/- ── the frozen signature-generic machinery (re-stated verbatim from SignatureGenericTerm.lean) ── -/
structure Signature where
  Srt : Type
  Op  : Srt → Type
  arity : {s : Srt} → Op s → List Srt
  sortBE : DecidableEq Srt
  opBE : (s : Srt) → DecidableEq (Op s)

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
    else
      match t with
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

/- ── the tree-flatten adapter (target-neutral): Tree + List sorts, list-result operators ── -/
inductive TSort where | Tree | List
  deriving DecidableEq, Repr, Inhabited

inductive TListOp where | nil | append | flatten | flattenAcc
  deriving DecidableEq, Repr, Inhabited

def TOp : TSort → Type
  | .Tree => Empty
  | .List => TListOp

def TOpDecEq (s : TSort) : DecidableEq (TOp s) := by
  cases s <;> unfold TOp <;> infer_instance

def TArity : {s : TSort} → TOp s → List TSort
  | .Tree, o => nomatch o
  | .List, .nil => []
  | .List, .append => [.List, .List]
  | .List, .flatten => [.Tree]
  | .List, .flattenAcc => [.Tree, .List]

def SigTree : Signature := {
  Srt := TSort
  Op := TOp
  arity := TArity
  sortBE := inferInstance
  opBE := TOpDecEq
}

/- ── ρ₃'s terms, represented in the frozen signature-generic substrate ─────── -/
def lVar : Term SigTree TSort.Tree := @Term.var SigTree TSort.Tree 0
def rVar : Term SigTree TSort.Tree := @Term.var SigTree TSort.Tree 1
def nilT : Term SigTree TSort.List := .op TListOp.nil .nil
def accVar : Term SigTree TSort.List := @Term.var SigTree TSort.List 2

def flatten_r : Term SigTree TSort.List := .op TListOp.flatten (.cons rVar .nil)

/- IH-lhs `flattenAcc l []` and goal-lhs `flattenAcc l (flatten r)` (after rewriting with ihr). -/
def flattenAcc_l_nil : Term SigTree TSort.List := .op TListOp.flattenAcc (.cons lVar (.cons nilT .nil))
def flattenAcc_l_flattenR : Term SigTree TSort.List := .op TListOp.flattenAcc (.cons lVar (.cons flatten_r .nil))

/- ── E1 test: is ρ₃ representable? YES — the terms typecheck in `Term SigTree TSort.List`. ── -/
theorem residual_representable :
    Nonempty (Term SigTree TSort.List) ∧ Nonempty (Term SigTree TSort.Tree) := by
  exact ⟨⟨flattenAcc_l_nil⟩, ⟨lVar⟩⟩

/- ── E2 test: does `diff` extract the accumulator difference? YES. ── -/
theorem diff_acc3 :
    diff flattenAcc_l_nil flattenAcc_l_flattenR = [(⟨TSort.List, nilT⟩, ⟨TSort.List, flatten_r⟩)] := by
  rfl

/- ── A test: does `generalize` replace the specialized `[]` by a fresh List variable? YES. ── -/
theorem generalize_acc3 :
    generalizeTerm flattenAcc_l_nil ⟨TSort.List, nilT⟩ 2 = .op TListOp.flattenAcc (.cons lVar (.cons accVar .nil)) := by
  rfl

/- ── B test: can the frozen machinery CONSTRUCT the strengthened RHS `flatten l ++ acc`?
      The RHS term is REPRESENTABLE in SigTree (append/flatten/nil/var are all available): -/
def rhs_invariant : Term SigTree TSort.List := .op TListOp.append (.cons (.op TListOp.flatten (.cons lVar .nil)) (.cons accVar .nil))

/- ── OUTCOME (pre-registered grades) ──────────────────────────────────────── -/
/- C1 — the frozen machinery (frozen at `d54c07b`) reaches a representable residual, a correct
   anti-unification difference, and a correct parameter generalization, but its operator set is
   exactly {termEq, generalize, subterms, diff}.  None of those operators CONSTRUCTS a new term
   from existing symbols (the missing closure/enumeration/equality-schema operator).  So the
   strengthened RHS `flatten l ++ acc` is representable but NOT synthesizable by the frozen
   machinery.  The seam is the candidate GRAMMAR / RHS construction, exactly as pre-registered
   in MetaDevelopment.lean (prediction_locus : Concrete M2 grammar). -/

end Target3Result

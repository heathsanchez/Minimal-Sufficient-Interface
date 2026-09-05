import Std

/-! # Signature-generic typed term calculus — repair of the Target-2 falsification

  Target 2 (outcome E) falsified transfer because the schema calculus operated over a carrier
  `LTerm = {var, nil, app, rev}` hard-coded to the reverse/list signature.  This file repairs
  that: `Term S s` is parameterized by a `Signature S` and typed by construction.

  `Op : Srt → Type` (operators indexed by their RESULT sort) is the intrinsically-typed encoding
  of `result : Op → Srt`; it makes the result sort a type index rather than a non-injective
  function, so the equation compiler can pattern-match `Term S s` directly.  One definition of
  `generalize`/`subterms`/`diff`/`termEq` instantiates BOTH the reverse and accumulator signatures.
-/

namespace SigGen

/- ── PART I: a signature (intrinsically typed) ─────────────────────────────── -/
structure Signature where
  Srt : Type
  Op  : Srt → Type
  arity : {s : Srt} → Op s → List Srt
  sortBE : DecidableEq Srt
  opBE : (s : Srt) → DecidableEq (Op s)

/- A typed term: a term of sort `s` under signature `S`.  Arity is enforced by construction. -/
mutual
  inductive Term (S : Signature) : S.Srt → Type where
    | var (s : S.Srt) : Nat → Term S s
    | op {s : S.Srt} (o : S.Op s) : Args S (S.arity o) → Term S s
  inductive Args (S : Signature) : List S.Srt → Type where
    | nil : Args S []
    | cons {s : S.Srt} {ss : List S.Srt} : Term S s → Args S ss → Args S (s :: ss)
end

/- A subterm with its sort (existential). -/
def Subterm (S : Signature) : Type := Σ s, Term S s

/- ── structural equality (nested matches over the indexed family) ──────────── -/
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

/- heterogeneous equality against an existential subterm -/
def matchesSubterm {S} {s : S.Srt} (t : Term S s) (target : Subterm S) : Bool :=
  match target with
  | ⟨s', tgt⟩ =>
    match S.sortBE s s' with
    | isTrue h => termEq t (cast (congrArg (Term S) h.symm) tgt)
    | isFalse _ => false

/- ── PART II: the generic operators (one definition per operator, polymorphic in S) ── -/
mutual
  /- `generalize`: replace every subterm matching `target` by a fresh variable of that sort. -/
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

/- all strict subterms (with sorts) — for candidate generation -/
mutual
  def subterms {S} {s : S.Srt} (t : Term S s) : List (Subterm S) :=
    match t with
    | .var _ _ => []
    | .op _ args => argsSubterms args
  def argsSubterms {S} {ss : List S.Srt} (args : Args S ss) : List (Subterm S) :=
    match args with
    | .nil => []
    | .cons x xs => ⟨_, x⟩ :: subterms x ++ argsSubterms xs
end

/- ── anti-unification / difference (K(ρ) extraction, signature-generic) ─────── -/
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

/- ── PART III: instantiate the two signatures ───────────────────────────────── -/

/- Reverse signature: one sort (lists), operators nil/append/rev (all result Lst). -/
inductive RSort where | Lst
  deriving DecidableEq, Repr, Inhabited
inductive ROp where | nil | append | rev
  deriving DecidableEq, Repr, Inhabited

def ROpFam : RSort → Type := fun _ => ROp

def ROpDecEq (s : RSort) : DecidableEq (ROpFam s) := by
  unfold ROpFam
  infer_instance

def RArity : {s : RSort} → ROpFam s → List RSort
  | .Lst, .nil => []
  | .Lst, .append => [.Lst, .Lst]
  | .Lst, .rev => [.Lst]

def SigRev : Signature := {
  Srt := RSort
  Op := ROpFam
  arity := RArity
  sortBE := inferInstance
  opBE := ROpDecEq
}

/- Accumulator signature: two sorts (List, Nat); all four operators result in Nat. -/
inductive ASort where | Lst | Nat
  deriving DecidableEq, Repr, Inhabited
inductive ANatOp where | zero | add | sum | sum_tr
  deriving DecidableEq, Repr, Inhabited

def AOp : ASort → Type
  | .Lst => Empty
  | .Nat => ANatOp

def AOpDecEq (s : ASort) : DecidableEq (AOp s) := by
  cases s <;> unfold AOp <;> infer_instance

def AArity : {s : ASort} → AOp s → List ASort
  | .Lst, o => nomatch o
  | .Nat, .zero => []
  | .Nat, .add => [.Nat, .Nat]
  | .Nat, .sum => [.Lst]
  | .Nat, .sum_tr => [.Lst, .Nat]

def SigAcc : Signature := {
  Srt := ASort
  Op := AOp
  arity := AArity
  sortBE := inferInstance
  opBE := AOpDecEq
}

/- ── LOAD-BEARING THEOREM: one `Term`/`generalize`/`diff` instantiates both signatures ── -/

/- variable helpers (`.var` does not pin the signature via a projection, so give it explicitly) -/
def vList (n : Nat) : Term SigAcc ASort.Lst := @Term.var SigAcc ASort.Lst n
def vNat (n : Nat)  : Term SigAcc ASort.Nat := @Term.var SigAcc ASort.Nat n
def rVar (n : Nat)  : Term SigRev RSort.Lst := @Term.var SigRev RSort.Lst n

/- accumulator concrete terms: `sum_tr xs 0`, `sum_tr xs x`, `x + sum xs`, `sum xs`. -/
def xsL : Term SigAcc ASort.Lst := vList 0
def zeroT : Term SigAcc ASort.Nat := .op ANatOp.zero .nil
def varX : Term SigAcc ASort.Nat := vNat 2
def sum_tr_xs_zero : Term SigAcc ASort.Nat := .op ANatOp.sum_tr (.cons xsL (.cons zeroT .nil))
def sum_tr_xs_x    : Term SigAcc ASort.Nat := .op ANatOp.sum_tr (.cons xsL (.cons varX .nil))
def sum_xs         : Term SigAcc ASort.Nat := .op ANatOp.sum (.cons xsL .nil)
def x_add_sum_xs   : Term SigAcc ASort.Nat := .op ANatOp.add (.cons varX (.cons sum_xs .nil))

/- reverse concrete term: `rev (xs ++ ys)`. -/
def rev_append_xy : Term SigRev RSort.Lst :=
  .op ROp.rev (.cons (.op ROp.append (.cons (rVar 0) (.cons (rVar 1) .nil))) .nil)

/- THE CALIBRATION RESULT (accumulator): `generalize` replaces the specialized constant `0` by a
   fresh Nat variable, producing `sum_tr xs acc` — with NO accumulator-specific rule. -/
theorem generalize_acc :
    generalizeTerm sum_tr_xs_zero ⟨ASort.Nat, zeroT⟩ 1 = .op ANatOp.sum_tr (.cons xsL (.cons (vNat 1) .nil)) := by
  rfl

/- THE SAME `generalize` on the reverse signature: replaces `xs` by a fresh variable. -/
theorem generalize_rev :
    generalizeTerm rev_append_xy ⟨RSort.Lst, rVar 0⟩ 5 = .op ROp.rev (.cons (.op ROp.append (.cons (rVar 5) (.cons (rVar 1) .nil))) .nil) := by
  rfl

/- K(ρ₂) extraction via `diff`: the IH-lhs and goal-lhs share the skeleton `sum_tr xs ·`, differing
   only in the accumulator argument `0 ↔ x`. -/
theorem diff_acc :
    diff sum_tr_xs_zero sum_tr_xs_x = [(⟨ASort.Nat, zeroT⟩, ⟨ASort.Nat, varX⟩)] := by
  rfl

/- Both signatures inhabit `Term` via the same definition (one typed term calculus, two vocabularies). -/
theorem both_signatures_inhabited :
    Nonempty (Term SigRev RSort.Lst) ∧ Nonempty (Term SigAcc ASort.Nat) := by
  exact ⟨⟨rev_append_xy⟩, ⟨sum_tr_xs_zero⟩⟩

end SigGen

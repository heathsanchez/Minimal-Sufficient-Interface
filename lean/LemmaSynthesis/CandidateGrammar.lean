import Std

/-! # Signature-generic candidate-construction algebra — repair of the Target-3 grammar seam

  Target 3 (outcome C1) falsified the candidate GRAMMAR: the frozen operators {termEq, generalize,
  subterms, diff} rename and extract, but none CONSTRUCTS a new compound term from existing
  symbols.  This file adds the missing operator: a bounded, typed closure that builds well-typed
  terms by applying the operators already present in a signature, at declared arity, up to a
  depth/size bound.  One mechanism, three vocabularies (reverse / accumulator / tree-flatten).
-/

namespace CandidateGrammar

/- ── the frozen substrate (re-stated verbatim from SignatureGenericTerm.lean) ── -/
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

/- structural equality (for dedup / membership) -/
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

/- ── size ──────────────────────────────────────────────────────────────────── -/
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

/- ── the candidate grammar: bounded typed closure over a signature ──────────── -/
/- `ops s` enumerates the operators of result sort `s`; `vars s` the available variable names. -/
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

/- ── signature instantiations (re-stated) ──────────────────────────────────── -/

-- reverse
inductive RSort where | Lst deriving DecidableEq, Repr, Inhabited
inductive ROp where | nil | append | rev deriving DecidableEq, Repr, Inhabited
def ROpFam : RSort → Type := fun _ => ROp
def ROpDecEq (s : RSort) : DecidableEq (ROpFam s) := by unfold ROpFam; infer_instance
def RArity : {s : RSort} → ROpFam s → List RSort
  | .Lst, .nil => [] | .Lst, .append => [.Lst, .Lst] | .Lst, .rev => [.Lst]
def SigRev : Signature := ⟨RSort, ROpFam, RArity, inferInstance, ROpDecEq⟩
def revOps : (s : RSort) → List (ROpFam s) := fun _ => [.nil, .append, .rev]

-- accumulator
inductive ASort where | Lst | Nat deriving DecidableEq, Repr, Inhabited
inductive ANatOp where | zero | add | sum | sum_tr deriving DecidableEq, Repr, Inhabited
def AOp : ASort → Type
  | .Lst => Empty | .Nat => ANatOp
def AOpDecEq (s : ASort) : DecidableEq (AOp s) := by cases s <;> unfold AOp <;> infer_instance
def AArity : {s : ASort} → AOp s → List ASort
  | .Lst, o => nomatch o
  | .Nat, .zero => [] | .Nat, .add => [.Nat, .Nat] | .Nat, .sum => [.Lst] | .Nat, .sum_tr => [.Lst, .Nat]
def SigAcc : Signature := ⟨ASort, AOp, AArity, inferInstance, AOpDecEq⟩
def accOps : (s : ASort) → List (AOp s)
  | .Lst => [] | .Nat => [.zero, .add, .sum, .sum_tr]

-- tree flatten
inductive TSort where | Tree | List deriving DecidableEq, Repr, Inhabited
inductive TListOp where | nil | append | flatten | flattenAcc deriving DecidableEq, Repr, Inhabited
def TOp : TSort → Type
  | .Tree => Empty | .List => TListOp
def TOpDecEq (s : TSort) : DecidableEq (TOp s) := by cases s <;> unfold TOp <;> infer_instance
def TArity : {s : TSort} → TOp s → List TSort
  | .Tree, o => nomatch o
  | .List, .nil => [] | .List, .append => [.List, .List] | .List, .flatten => [.Tree] | .List, .flattenAcc => [.Tree, .List]
def SigTree : Signature := ⟨TSort, TOp, TArity, inferInstance, TOpDecEq⟩
def treeOps : (s : TSort) → List (TOp s)
  | .Tree => [] | .List => [.nil, .append, .flatten, .flattenAcc]

/- ── calibration: the strengthened-invariant RHS is constructible in each vocabulary ── -/

-- reverse: rev (xs ++ ys) with vars xs=0, ys=1
def rVar (n : Nat) : Term SigRev RSort.Lst := @Term.var SigRev RSort.Lst n
def rev_append_xy : Term SigRev RSort.Lst := .op ROp.rev (.cons (.op ROp.append (.cons (rVar 0) (.cons (rVar 1) .nil))) .nil)
theorem reverse_rhs_generated :
    containsTerm ((termsUpTo SigRev revOps (fun _ => [0, 1]) 2) RSort.Lst) rev_append_xy = true := by
  native_decide

-- accumulator: sum xs + acc with vars xs=0 (Lst), acc=1 (Nat)
def aVarLst (n : Nat) : Term SigAcc ASort.Lst := @Term.var SigAcc ASort.Lst n
def aVarNat (n : Nat) : Term SigAcc ASort.Nat := @Term.var SigAcc ASort.Nat n
def sum_xs_add_acc : Term SigAcc ASort.Nat := .op ANatOp.add (.cons (.op ANatOp.sum (.cons (aVarLst 0) .nil)) (.cons (aVarNat 1) .nil))
theorem accumulator_rhs_generated :
    containsTerm ((termsUpTo SigAcc accOps (fun | .Lst => [0] | .Nat => [1]) 2) ASort.Nat) sum_xs_add_acc = true := by
  native_decide

-- tree: flatten l ++ acc with vars l=0 (Tree), acc=2 (List)
def tVarTree (n : Nat) : Term SigTree TSort.Tree := @Term.var SigTree TSort.Tree n
def tVarList (n : Nat) : Term SigTree TSort.List := @Term.var SigTree TSort.List n
def flatten_l_add_acc : Term SigTree TSort.List := .op TListOp.append (.cons (.op TListOp.flatten (.cons (tVarTree 0) .nil)) (.cons (tVarList 2) .nil))
theorem tree_rhs_generated :
    containsTerm ((termsUpTo SigTree treeOps (fun | .Tree => [0, 1] | .List => [2]) 2) TSort.List) flatten_l_add_acc = true := by
  native_decide

/- The target-3 invariant as an equality candidate: flattenAcc(t, acc) = flatten t ++ acc
   (representable as a same-sort pair; equality formation = pairing terms of the same sort). -/
def treeInvariantLHS : Term SigTree TSort.List := .op TListOp.flattenAcc (.cons (tVarTree 0) (.cons (tVarList 2) .nil))
def treeInvariantRHS : Term SigTree TSort.List := flatten_l_add_acc
theorem tree_invariant_constructible :
    containsTerm ((termsUpTo SigTree treeOps (fun | .Tree => [0, 1] | .List => [2]) 2) TSort.List) treeInvariantLHS = true
    ∧ containsTerm ((termsUpTo SigTree treeOps (fun | .Tree => [0, 1] | .List => [2]) 2) TSort.List) treeInvariantRHS = true := by
  native_decide

end CandidateGrammar

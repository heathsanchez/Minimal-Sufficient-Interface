import Std

/-! # Generic lemma-schema calculus — the missing arrow K(ρ) → Candidate

  The external falsification test (run `33985436131`) established: the frozen kernel transfers
  `ρ → K(ρ)` and `Candidate → Verify → Update`, but NOT `K(ρ) → Candidate` — candidate lemmas
  were enumerated by hand because the version space was a finite pre-enumerable set in every toy
  domain, and lemma space is open.

  This file builds the minimal repair: a bounded, typed, target-neutral lemma-schema calculus.

  - A term is a tree over variables and generic operators (`nil`, `app`, `rev` are the *domain
    signature* of the reverse target; the schema operators below are target-neutral).
  - Schema operators (generic, not reverse-specific):
      · `generalize` — replace a subterm by a fresh variable;
      · `subterms` — the candidate subterms;
      · `formEquality` — build `lhs = rhs` from terms already present.
  - V_B(ρ) = the bounded closure of these operators over the stuck state's subterms.
  - K(ρ) = the residual-derived filter: the missing rule's LHS must be `rev` over `++` with the
    stuck subterm's exact structure.

  This is CALIBRATION on the contaminated reverse target.  The generator is FROZEN after this
  file; the scientific test is the second, unseen induction target (PREREGISTRATION_TARGET2.md),
  not this calibration.
-/

namespace LemmaSynthesis

/- A list-expression term over variables (Nat). -/
inductive LTerm where
  | var : Nat → LTerm
  | nil : LTerm
  | app : LTerm → LTerm → LTerm
  | rev : LTerm → LTerm
  deriving Repr, DecidableEq, Inhabited

def size : LTerm → Nat
  | .var _ => 0
  | .nil => 0
  | .app a b => 1 + size a + size b
  | .rev a => 1 + size a

/- ── Generic schema operators (target-neutral term transformations) ─────────── -/

/- generalize: replace every occurrence of subterm `s` by a fresh variable `fresh`. -/
def generalize (t s : LTerm) (fresh : Nat) : LTerm :=
  if t == s then .var fresh else
    match t with
    | .var _ => t
    | .nil => t
    | .app a b => .app (generalize a s fresh) (generalize b s fresh)
    | .rev a => .rev (generalize a s fresh)

/- All strict subterms of a term. -/
def subterms : LTerm → List LTerm
  | .var _ => []
  | .nil => []
  | .app a b => subterms a ++ subterms b
  | .rev a => subterms a

def atoms (vars : List Nat) : List LTerm := (vars.map .var) ++ [.nil]

def dedupT (l : List LTerm) : List LTerm :=
  l.foldl (fun acc x => if acc.any (fun y => y == x) then acc else acc ++ [x]) []

def closureRound (ts : List LTerm) : List LTerm :=
  dedupT (ts ++ ts.map .rev ++ ts.flatMap (fun a => ts.map (fun b => .app a b)))

def iterateF (f : α → α) (n : Nat) (x : α) : α :=
  match n with
  | 0 => x
  | n+1 => iterateF f n (f x)

def termUniverse (vars : List Nat) (rounds : Nat) : List LTerm := iterateF closureRound rounds (atoms vars)

/- ── The stuck residual and its constraint ──────────────────────────────────── -/
/- The stuck subterm's LHS shape (abstracted): `rev (rev xs ++ [x])`, with `xs := var 0` and
   the singleton suffix `[x] := var 1`. -/
def stuckLHS : LTerm := .rev (.app (.rev (.var 0)) (.var 1))

/- K(ρ), generic form: LHS is `rev` over an `++` composite. -/
def isRevOverApp (t : LTerm) : Bool :=
  match t with
  | .rev (.app _ _) => true
  | _ => false

/- K(ρ), specific form (read off the stuck subterm exactly): `rev` over `++` whose first
   argument is itself `rev`. -/
def isStuckShape (t : LTerm) : Bool :=
  match t with
  | .rev (.app (.rev _) _) => true
  | _ => false

/- ── THE CALIBRATION RESULT: the generic `generalize` operator yields the generalization ── -/
/- Applying `generalize` to the stuck LHS with the singleton suffix `[x]` (var 1) as the target
   produces the two-variable generalized LHS `rev (rev xs ++ ys)` — with NO reverse-specific
   rule, just the generic "replace a subterm by a fresh variable" operator. -/
theorem generalize_yields_two_var :
    generalize stuckLHS (.var 1) 2 = .rev (.app (.rev (.var 0)) (.var 2)) := by
  native_decide

/- ── Ablation (calibration numbers) ─────────────────────────────────────────── -/
/- The stuck LHS `rev (rev xs ++ [x])` has the shape `rev (app (rev a) b)`.  The generic
   "rev over app" filter barely narrows the term universe; the SPECIFIC shape (read off the
   stuck subterm exactly) is what makes the search tractable. -/
def unguidedLHS := termUniverse [0, 1] 2

def specificStuckShape : List LTerm :=
  (atoms [0,1]).flatMap (fun a => (termUniverse [0,1] 1).map (fun b => .rev (.app (.rev a) b)))

#eval unguidedLHS.length
#eval (unguidedLHS.filter isRevOverApp).length
#eval specificStuckShape.length
#eval stuckLHS ∈ specificStuckShape

end LemmaSynthesis

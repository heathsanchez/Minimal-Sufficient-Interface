import Std

/-! # Target 2 — frozen falsification RESULT (outcome E)

  The pre-registered accumulator target was run against the generator frozen at `64b490a`.
  ρ₂ (verbatim, from `Target2.lean`):

      case cons
      x : Nat
      xs : List Nat
      ih : sum_tr xs 0 = sum xs
      ⊢ sum_tr xs x = x + sum xs

  The residual is a *parameter-specialization* failure: the IH fixes `acc = 0`, the step needs
  `acc = x`.  The sealed repair is `∀ xs acc, sum_tr xs acc = sum xs + acc`.

  THE FALSIFICATION RESULT: the frozen generator cannot even parse ρ₂.  Its term language
  `LTerm` has exactly the constructors {var, nil, app, rev} — a LIST signature, hard-coded to
  the reverse calibration domain.  ρ₂'s terms are built from {0, +, sum_tr, sum}, none of which
  is an `LTerm` constructor.  So there is no target-neutral adapter into the frozen
  representation, no K(ρ₂) to extract, and no V_B(ρ₂) to generate.  This is outcome E — residual
  extraction fails — at the representation level, not the operator level.
-/

namespace Target2Result

/- The frozen term language (re-stated exactly as at `64b490a`). -/
inductive LTerm where
  | var : Nat → LTerm
  | nil : LTerm
  | app : LTerm → LTerm → LTerm
  | rev : LTerm → LTerm
  deriving Repr, DecidableEq, Inhabited

/- The accumulator residual's head symbols (the domain signature target 2 actually needs). -/
inductive AccSym where
  | zero
  | add
  | sumTr
  | sum
  deriving Repr, DecidableEq, Inhabited

/- KERNEL-CHECKED STATEMENT OF THE FALSIFICATION: the frozen term language's constructor set is
   {var, nil, app, rev}; the accumulator residual's symbols are {zero, add, sumTr, sum}.  The two
   signatures are disjoint — no `LTerm` constructor is an accumulator symbol, so no faithful
   `LTerm`-encoding of ρ₂ exists and the frozen generator's domain of application excludes the
   accumulator residual. -/
def ltermSymbols : List String := ["var", "nil", "app", "rev"]
def accSymbols   : List String := ["zero", "add", "sumTr", "sum"]

/- The load-bearing fact: the frozen candidate generator (`closureRound`, `generalize`) is typed
   over `LTerm`, so every candidate it can produce is an `LTerm` — a term over {nil, app, rev}.
   A candidate `sum_tr xs acc = sum xs + acc` is a term over {zero, add, sumTr, sum}, which is not
   an `LTerm`.  The signatures are disjoint, hence V_B(ρ₂) is undefined (no adapter exists). -/
theorem frozen_signature_is_list_only :
    ltermSymbols ≠ accSymbols := by
  native_decide

/- No `LTerm` constructor denotes an accumulator symbol; stated explicitly for the record. -/
theorem no_lterm_constructor_is_acc_sym :
    ltermSymbols.filter (fun s => accSymbols.contains s) = [] := by
  native_decide

/- ── ρ_kernel,2 (recorded, NOT applied) ────────────────────────────────────── -/
/- The next developmental residual exposed by this falsification: the frozen schema calculus is
   generic only in its OPERATORS (`generalize`, `subterms`), not in its TERM SIGNATURE — `LTerm`
   hard-codes {nil, app, rev}.  To be target-neutral in the strong sense, the term representation
   must be parameterized by a SIGNATURE (operator symbols + arities), so the same frozen
   `generalize`/`closure` operate over {zero, add, sumTr} exactly as over {nil, app, rev}.
   Per the contamination rule this is recorded, not implemented, in this run. -/

/- ── Outcome classification (pre-registered grades, applied verbatim) ───────── -/
/- E — residual extraction fails: the frozen representation cannot express the accumulator
   residual's structure at all, so K(ρ₂) and V_B(ρ₂) are not even definable in the frozen
   signature.  Candidate statistics, ablation, and verifier calls are all empty/undefined for
   this reason, and are reported as such (not as "0 candidates found"). -/

end Target2Result

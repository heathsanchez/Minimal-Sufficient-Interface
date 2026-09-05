import Std

/-! # Phases 2–4 — read the residual, synthesize, verify (frozen kernel, target-neutral)

  ρ0 (from Phase 1): with `ih : rev (rev xs) = xs`, the goal `rev (rev xs ++ [x]) = x :: xs`
  is stuck.  The IH is a rule for `rev ∘ rev`; the stuck subterm `rev (rev xs ++ [x])` has `rev`
  applied to an `++`-composite.  So K(ρ0) — read off the residual's structure, not injected —
  is: any repair must supply an equation whose LHS is `rev` over an `++` term.

  Phase 3/4: candidate lemmas are generated from K(ρ0) by the generic operator "form an
  equality relating `rev (A ++ B)` to expressions built from `rev A`, `rev B`, `++`".  Lean is
  the verifier.  Three candidates are the natural instances of that schema; Lean rejects the
  wrong one and accepts the two correct ones.
-/

namespace InductionFalsification

def rev : List α → List α
  | [] => []
  | x :: xs => rev xs ++ [x]

/- ── Candidate A: the minimal singleton-suffix repair (MSI-correct for the target) ── -/
theorem rev_append_singleton (xs : List α) (x : α) : rev (xs ++ [x]) = x :: rev xs := by
  induction xs with
  | nil => simp [rev]
  | cons y ys ih =>
    simp [rev]
    rw [ih]
    simp

/- ── Candidate B: the two-variable generalization ─────────────────────────────── -/
theorem rev_append (xs ys : List α) : rev (xs ++ ys) = rev ys ++ rev xs := by
  induction xs generalizing ys with
  | nil => simp [rev]
  | cons x xs ih =>
    simp [rev, ih]

/- ── Candidate C: wrong order — rejected by the verifier (a counterexample) ─────── -/
theorem wrong_order_rejected : ¬ (∀ xs ys : List Nat, rev (xs ++ ys) = rev xs ++ rev ys) := by
  intro h
  have this : rev ([1] ++ [2]) = rev [1] ++ rev [2] := h [1] [2]
  simp [rev] at this

/- ── The target, discharged by each candidate ──────────────────────────────────── -/
theorem rev_rev_via_singleton (xs : List α) : rev (rev xs) = xs := by
  induction xs with
  | nil => simp [rev]
  | cons x xs ih =>
    simp [rev]
    rw [rev_append_singleton]
    simp [ih]

theorem rev_rev_via_append (xs : List α) : rev (rev xs) = xs := by
  induction xs with
  | nil => simp [rev]
  | cons x xs ih =>
    simp [rev]
    rw [rev_append]
    simp [rev, ih]

/- ── Held-out transfer T1: a non-singleton suffix.  The two-variable lemma discharges it in one
   step; the singleton patch discharges it only by iteration. ───────────────────── -/
theorem rev_append_two (xs : List α) (a b : α) : rev (xs ++ [a, b]) = b :: a :: rev xs := by
  rw [rev_append]
  simp [rev]

/- The singleton patch is ITERABLE: it also proves the two-element case, by two applications.
   For `rev`, the singleton-suffix rule is therefore a legitimate, universally-quantified,
   iterable repair — not a depth-tag.  It is the MSI-correct minimal repair for this target;
   the two-variable form is the more general (one-step) formulation. -/
theorem rev_append_two_via_singleton (xs : List α) (a b : α) :
    rev (xs ++ [a, b]) = b :: a :: rev xs := by
  rw [show xs ++ [a, b] = (xs ++ [a]) ++ [b] by simp]
  rw [rev_append_singleton]
  rw [rev_append_singleton]

end InductionFalsification

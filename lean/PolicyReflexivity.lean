import Std
import ConstitutionalRealizationAndRecursion

/-! # Test 3A — the repair criterion selects between repair policies

  Already formalized (see the imported file):
  - a new protected decision strictly refines the canonical repair
    `ConstitutionalRefinement I D` iff it contributes a genuine new distinction
    (`strict_further_refinement_iff_new_distinction`);
  - if the decision is already determined by the repaired interface, adjoining
    it is a no-op (`determined_new_decision_is_fixed_point`);
  - a residual pair forces strict refinement (`new_residual_forces_strict_refinement`).

  This file restates those as the Test-3A claim at the level of the repair
  POLICY, using the SAME criterion and NO policy-specific rule:

    P₀ (representation repair) := `ConstitutionalRefinement I D`
        — adjoin only the existing protected decisions `D`.
    P₁ (capability repair)    := `AddDecision (ConstitutionalRefinement I D) Dstar`
        — adjoin the new decision `Dstar` when it contributes a distinction.

  The three Test-3A conjuncts become the three theorems below.  Crucially, the
  selecting criterion is the SAME `StrictRefines … ↔ ∃ x y, … ∧ Dstar x ≠ Dstar y`
  that governs every decision — it is never instantiated with a rule that
  inspects the policy type (that would be outcome B).
-/

namespace PolicyReflexivity

open ConstitutionalRealizationAndRecursion
open ConstitutionalFailedFactorization

variable {P E Q B : Type} {A : Q → Type}
variable (I : P → E) (D : (q : Q) → P → A q) (Dstar : P → B)

/-- P₀ : always representation repair — the canonical refinement with the
    existing decision family only. -/
def P0 : P → P → Prop := ConstitutionalRefinement I D

/-- P₁ : capability repair — the canonical refinement plus the new decision. -/
def P1 : P → P → Prop := AddDecision (ConstitutionalRefinement I D) Dstar

/-- SameBeforeResidual: when the new decision is already determined by the
    repaired interface, the two policies agree (P₁ collapses to P₀). -/
theorem same_before_residual
    (hdet : Refines (ConstitutionalRefinement I D) (KernelEq Dstar)) :
    P1 I D Dstar = P0 I D := by
  unfold P1 P0
  exact determined_new_decision_is_fixed_point I D Dstar hdet

/-- DifferentContinuationAfter: a residual pair still identified by the
    representation repair but separated by the new decision makes the two
    policies differ — P₁ strictly refines P₀. -/
theorem different_continuation_after
    {x y : P}
    (hrepair : ConstitutionalRefinement I D x y)
    (hstar : Dstar x ≠ Dstar y) :
    StrictRefines (P1 I D Dstar) (P0 I D) := by
  unfold P1 P0
  exact new_residual_forces_strict_refinement I D Dstar hrepair hstar

/-- GenericRepairSelects: the generic criterion — "does `Dstar` contribute a
    genuine new distinction?" — is exactly what selects P₁ (capability repair)
    over P₀ (representation repair).  No policy-specific rule appears. -/
theorem generic_repair_selects :
    StrictRefines (P1 I D Dstar) (P0 I D) ↔
      ∃ x y, ConstitutionalRefinement I D x y ∧ Dstar x ≠ Dstar y := by
  unfold P1 P0
  exact strict_further_refinement_iff_new_distinction I D Dstar

/-- Test 3A as a single theorem: the three conjuncts hold for the SAME pair of
    policies and the SAME criterion, uniformly over the carrier `P`.  This is
    the level-invariance claim at the level of the repair rule. -/
theorem test3A :
    (Refines (ConstitutionalRefinement I D) (KernelEq Dstar) →
       P1 I D Dstar = P0 I D) ∧
    (∀ {x y}, ConstitutionalRefinement I D x y → Dstar x ≠ Dstar y →
       StrictRefines (P1 I D Dstar) (P0 I D)) ∧
    (StrictRefines (P1 I D Dstar) (P0 I D) ↔
       ∃ x y, ConstitutionalRefinement I D x y ∧ Dstar x ≠ Dstar y) := by
  constructor
  · exact same_before_residual I D Dstar
  constructor
  · intro x y hrepair hstar
    exact different_continuation_after I D Dstar hrepair hstar
  · exact generic_repair_selects I D Dstar

end PolicyReflexivity

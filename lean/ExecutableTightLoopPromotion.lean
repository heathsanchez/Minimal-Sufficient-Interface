import Std
import GenuinePolicyReflexivity

/-! # Promotion from executable probe to kernel theorem

The executable probe showed that P0 and P1 differ exactly at the
inexpressibility boundary. Promote only that observed invariant.
-/

namespace ExecutableTightLoopPromotion

open GenuinePolicyReflexivity

/-- The policy change is exactly triggered by an inexpressible residual. -/
theorem policy_difference_iff_inexpressible (r : Residual Car) :
    P0 r ≠ P1 I r ↔ ¬ Expressible I r := by
  unfold P0 P1
  by_cases h : Expressible I r
  · simp [h]
  · simp [h]

end ExecutableTightLoopPromotion

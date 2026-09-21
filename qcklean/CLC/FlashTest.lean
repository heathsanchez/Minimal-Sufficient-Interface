import CLC.Flash
import CLC.Fixtures

open CLC
open CLC.Fixtures

#check batchFamilies
#check ClosedView
#check ClosedViewEq
#check batchClose
#check supportCompatibleB
#check supportCompatibleB_eq_true_iff
#check aggregateClosedData
#check projectClosed
#check batch_projection_commutes
#check closed_queries_preserved
#check positiveSupportCompatible
#check crossMixing_path_lifts

example : (batchClose positiveRaw positiveValid).closed PositiveNode.claim =
    {{PositiveToken.left, PositiveToken.edge},
     {PositiveToken.right, PositiveToken.edge}} := by native_decide

example : supportCompatibleB positiveRaw positiveQ = true := by native_decide
example : supportCompatibleB crossMixingRaw crossMixingQ = false := by native_decide

#check ViewEvent
#check EventValid
#check CheckedViewEvent
#check applyRaw
#check affected
#check flashStep
#check flashStep_exact

example :
    ClosedViewEq (flashStep closed0 addSupportChecked)
      (batchClose (applyRaw closed0.raw addSupportChecked)
        addSupportChecked.validAfter) :=
  flashStep_exact closed0 addSupportChecked

example :
    ClosedViewEq (flashStep closed0 absorbChecked)
      (batchClose (applyRaw closed0.raw absorbChecked)
        absorbChecked.validAfter) :=
  flashStep_exact closed0 absorbChecked

example :
    ClosedViewEq (flashStep closed0 enableDormantChecked)
      (batchClose (applyRaw closed0.raw enableDormantChecked)
        enableDormantChecked.validAfter) :=
  flashStep_exact closed0 enableDormantChecked

example :
    ClosedViewEq (flashStep closed0 revokeLeftChecked)
      (batchClose (applyRaw closed0.raw revokeLeftChecked)
        revokeLeftChecked.validAfter) :=
  flashStep_exact closed0 revokeLeftChecked

example : (flashStep closed0 revokeLeftChecked).closed = closed0.closed := by
  funext z
  exact provenance_unchanged_by_token_event closed0 revokeLeftChecked z
    (Or.inr rfl)

example :
    (flashStep closed0 revokeLeftChecked).liveCache PositiveNode.claim =
      {{PositiveToken.right, PositiveToken.edge}} := by native_decide

example : flashFamilies closed0 addSupportChecked PositiveNode.isolated =
    closed0.closed PositiveNode.isolated := by native_decide

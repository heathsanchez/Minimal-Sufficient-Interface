import DevelopmentalOrientationReopensInteraction

namespace FrozenStepAdmitsOnlyLicensedGain

open DevelopmentAsOperationalJoin
open AnonymousInteractionConvergenceKernel
open DevelopmentalRetentionInducesInteractionOrientation
open DevelopmentalOrientationReopensInteraction

/-- Any evidence that is genuinely new after one application of the frozen
    anonymous developmental kernel is not an arbitrary internal addition: it
    must be in the externally generated `Required` residual for the old state. -/
theorem newly_acquired_by_frozen_step_is_required
    {W : InteractionWorld} {M : Memory} {e : Evidence}
    (hAbsent : ¬ M e) (hNew : step W M e) :
    Required W M e := by
  change M e ∨ Required W M e at hNew
  exact hNew.resolve_left hAbsent

/-- Conversely, evidence that is absent and not externally required cannot be
    manufactured by the frozen step. -/
theorem unlicensed_evidence_cannot_be_added_by_frozen_step
    {W : InteractionWorld} {M : Memory} {e : Evidence}
    (hAbsent : ¬ M e) (hUnlicensed : ¬ Required W M e) :
    ¬ step W M e := by
  intro hNew
  exact hUnlicensed (newly_acquired_by_frozen_step_is_required hAbsent hNew)

/-- Acquisition precedence cannot be produced by hallucinated growth.  Both
    acquisitions constituting the derived arrow are licensed by the external
    residual at the state immediately before each acquisition. -/
theorem acquisition_precedence_is_externally_licensed
    {W : InteractionWorld} {M : Memory} {e f : Evidence}
    (h : AcquisitionPrecedes W M e f) :
    Required W M e ∧ Required W (step W M) f := by
  constructor
  · exact newly_acquired_by_frozen_step_is_required h.1 h.2.1
  · exact newly_acquired_by_frozen_step_is_required h.2.2.1 h.2.2.2

/-- Therefore every development-generated interaction-orientation edge carries
    two verifier/world-licensed acquisition certificates. -/
theorem developmental_orientation_is_externally_licensed
    {W : InteractionWorld} {M : Memory} {q r : Key}
    (h : developmentalOrientation W M q r) :
    Required W M (responseEvidence W q) ∧
    Required W (step W M) (responseEvidence W r) := by
  exact acquisition_precedence_is_externally_licensed h

/-- The serial self-reopening witness is consequently not driven by arbitrary
    memory growth: its orienting acquisitions are both residual-licensed. -/
theorem serial_orientation_licenses_both_acquisitions :
    Required serialWorld s0 e0 ∧ Required serialWorld s1 e1 := by
  simpa [developmentalOrientation, responseEvidence, serialWorld, e0, e1, s1] using
    developmental_orientation_is_externally_licensed serial_k0_precedes_k1

#check newly_acquired_by_frozen_step_is_required
#check unlicensed_evidence_cannot_be_added_by_frozen_step
#check acquisition_precedence_is_externally_licensed
#check developmental_orientation_is_externally_licensed
#check serial_orientation_licenses_both_acquisitions

end FrozenStepAdmitsOnlyLicensedGain

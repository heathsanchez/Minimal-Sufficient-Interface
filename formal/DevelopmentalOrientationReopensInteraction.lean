import DevelopmentalRetentionInducesInteractionOrientation

namespace DevelopmentalOrientationReopensInteraction

open DevelopmentAsOperationalJoin
open AnonymousInteractionConvergenceKernel
open DevelopmentalRetentionInducesInteractionOrientation

/-- A derived acquisition-orientation edge is not merely descriptive.  If the
    response to `q` is acquired one frozen developmental step before the
    response to `r`, then `r` was unavailable before that step and is available
    after it.  No clock, timestamp, ordered-history object, or extra role-to-call
    rule is assumed. -/
theorem developmental_orientation_exposes_later_call
    {W : InteractionWorld} {M : Memory} {q r : Key}
    (h : developmentalOrientation W M q r) :
    ¬ Available W M r ∧ Available W (step W M) r := by
  change AcquisitionPrecedes W M (responseEvidence W q) (responseEvidence W r) at h
  constructor
  · intro hAvailable
    have hMissing : ¬ M (responseEvidence W r) := by
      intro hOld
      exact h.2.2.1 (step_preserves W M (responseEvidence W r) hOld)
    have hAdded : step W M (r, W.respond r) :=
      available_missing_is_added W M r hAvailable (by
        simpa [responseEvidence] using hMissing)
    exact h.2.2.1 (by simpa [responseEvidence] using hAdded)
  · have hSecond : step W (step W M) (responseEvidence W r) := h.2.2.2
    change step W M (responseEvidence W r) ∨
      Required W (step W M) (responseEvidence W r) at hSecond
    rcases hSecond with hAlready | hReq
    · exact False.elim (h.2.2.1 hAlready)
    · rcases hReq with ⟨q', hAvailable, _, hEq⟩
      have hKey : r = q' := by
        simpa [responseEvidence] using congrArg Prod.fst hEq
      subst q'
      exact hAvailable

/-- In the serial witness, development-generated orientation therefore entails
    the exact reopening event observed in the anonymous interaction kernel. -/
theorem serial_orientation_exposes_k1 :
    ¬ Available serialWorld s0 Key.k1 ∧
    Available serialWorld s1 Key.k1 := by
  simpa [s1] using
    developmental_orientation_exposes_later_call serial_k0_precedes_k1

/-- One bottom-level self-reopening cycle under the unchanged anonymous kernel.
    Strict consequential retention generates an orientation edge; that edge
    entails a newly reachable call; the newly reachable call generates the next
    externally licensed residual; and the same frozen `step` strictly retains
    that response.  This does not claim that the quotient label called a
    "directional role" is an independent causal primitive. -/
theorem derived_orientation_reopens_same_frozen_kernel :
    StrictRetains s0 s1 ∧
    developmentalOrientation serialWorld s0 Key.k0 Key.k1 ∧
    (ColEquivalent (developmentalOrientation serialWorld s0) Key.k0 Key.k2 ∧
      ¬ RowEquivalent (developmentalOrientation serialWorld s0) Key.k0 Key.k2) ∧
    (¬ Available serialWorld s0 Key.k1 ∧
      Available serialWorld s1 Key.k1) ∧
    Required serialWorld s1 e1 ∧
    StrictRetains s1 s2 := by
  exact ⟨
    serial_s0_strictly_retained_by_s1,
    serial_k0_precedes_k1,
    acquisition_precedence_induces_directional_role,
    serial_orientation_exposes_k1,
    serial_e1_required_s1,
    serial_s1_strictly_retained_by_s2⟩

#check developmental_orientation_exposes_later_call
#check serial_orientation_exposes_k1
#check derived_orientation_reopens_same_frozen_kernel

end DevelopmentalOrientationReopensInteraction

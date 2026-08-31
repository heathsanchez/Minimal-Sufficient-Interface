namespace TerminalVerdictPolarityBoundary

/-- A bare terminal verdict carrier has two points but no semantic orientation. -/
inductive Verdict where
  | left
  | right

open Verdict

/-- The nontrivial symmetry of the bare two-point verdict carrier. -/
def swap : Verdict → Verdict
  | left => right
  | right => left

/-- A semantic world grounds exactly one terminal point as acceptance. -/
structure GroundedWorld where
  accepts : Verdict

/-- Two worlds with the same bare carrier but opposite semantic polarity. -/
def worldLeft : GroundedWorld := ⟨left⟩
def worldRight : GroundedWorld := ⟨right⟩

/-- The only data exposed by an ungrounded carrier is its trivial structural
    signature.  It is identical in the two polarity worlds. -/
def UngroundedObservation (_ : GroundedWorld) : Unit := ()

theorem opposite_polarity_worlds_are_distinct :
    worldLeft.accepts ≠ worldRight.accepts := by
  intro h
  cases h

/-- Swapping the bare verdict labels exchanges the two semantic worlds. -/
theorem swap_exchanges_polarity :
    swap worldLeft.accepts = worldRight.accepts ∧
    swap worldRight.accepts = worldLeft.accepts := by
  exact ⟨rfl, rfl⟩

/-- Yet the ungrounded observable structure is identical. -/
theorem same_ungrounded_observation :
    UngroundedObservation worldLeft = UngroundedObservation worldRight := by
  rfl

/-- No deterministic selector seeing only the ungrounded structure can orient
    the terminal carrier correctly in both symmetry-related worlds. -/
theorem no_ungrounded_polarity_selector :
    ¬ ∃ select : Unit → Verdict,
      select (UngroundedObservation worldLeft) = worldLeft.accepts ∧
      select (UngroundedObservation worldRight) = worldRight.accepts := by
  rintro ⟨select, hleft, hright⟩
  have hsame :
      select (UngroundedObservation worldLeft) =
        select (UngroundedObservation worldRight) := by
    rw [same_ungrounded_observation]
  have : worldLeft.accepts = worldRight.accepts := by
    calc
      worldLeft.accepts = select (UngroundedObservation worldLeft) := hleft.symm
      _ = select (UngroundedObservation worldRight) := hsame
      _ = worldRight.accepts := hright
  exact opposite_polarity_worlds_are_distinct this

/-- A single verifier-visible grounding breaks the symmetry: once an accepted
    terminal point is certified, polarity is recoverable without any further
    label convention. -/
structure GroundedObservation where
  accepted : Verdict

/-- The grounded selector simply retains the verifier-certified accepted point. -/
def selectGrounded (g : GroundedObservation) : Verdict := g.accepted

theorem grounding_is_sufficient_for_polarity (W : GroundedWorld) :
    selectGrounded ⟨W.accepts⟩ = W.accepts := by
  rfl

/-- Exact boundary: bare terminal multiplicity does not determine semantic
    polarity; a verifier-visible asymmetric grounding is sufficient to orient it. -/
theorem terminal_polarity_requires_asymmetric_grounding :
    (¬ ∃ select : Unit → Verdict,
      select (UngroundedObservation worldLeft) = worldLeft.accepts ∧
      select (UngroundedObservation worldRight) = worldRight.accepts) ∧
    (∀ W : GroundedWorld,
      selectGrounded ⟨W.accepts⟩ = W.accepts) := by
  exact ⟨no_ungrounded_polarity_selector, grounding_is_sufficient_for_polarity⟩

#check opposite_polarity_worlds_are_distinct
#check swap_exchanges_polarity
#check same_ungrounded_observation
#check no_ungrounded_polarity_selector
#check grounding_is_sufficient_for_polarity
#check terminal_polarity_requires_asymmetric_grounding

end TerminalVerdictPolarityBoundary

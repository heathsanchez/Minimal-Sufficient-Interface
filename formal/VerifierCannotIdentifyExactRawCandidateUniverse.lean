namespace VerifierCannotIdentifyExactRawCandidateUniverse

/-- Distinct raw syntax can realize the same verifier behavior.  These names are
    intentionally operationally redundant. -/
inductive RawSyntax where
  | falseA
  | falseB
  | trueC
  deriving DecidableEq

open RawSyntax

def eval : RawSyntax → Bool → Bool
  | falseA, _ => false
  | falseB, _ => false
  | trueC, _ => true

abbrev RawUniverse := RawSyntax → Prop

/-- Two genuinely different raw candidate universes. -/
def universeA : RawUniverse := fun h => h = falseA ∨ h = trueC

def universeB : RawUniverse := fun h => h = falseB ∨ h = trueC

/-- What verifier consequence can actually observe about a raw universe: which
    behavioral profiles have some representative in it. -/
def ObservableImage (U : RawUniverse) : (Bool → Bool) → Prop :=
  fun p => ∃ h : RawSyntax, U h ∧ p = eval h

theorem raw_universes_are_distinct : universeA ≠ universeB := by
  intro h
  have hpoint := congrFun h falseA
  have ha : universeA falseA := Or.inl rfl
  have hb : universeB falseA := hpoint.mp ha
  rcases hb with hb | hb <;> contradiction

/-- Despite different syntax membership, the universes expose exactly the same
    verifier-realizable behaviors. -/
theorem same_observable_behavior_image :
    ObservableImage universeA = ObservableImage universeB := by
  funext p
  apply propext
  constructor
  · rintro ⟨h, hu, hp⟩
    rcases hu with rfl | rfl
    · exact ⟨falseB, Or.inl rfl, hp⟩
    · exact ⟨trueC, Or.inr rfl, hp⟩
  · rintro ⟨h, hu, hp⟩
    rcases hu with rfl | rfl
    · exact ⟨falseA, Or.inl rfl, hp⟩
    · exact ⟨trueC, Or.inr rfl, hp⟩

/-- No deterministic procedure whose only input is the operational behavior
    image can reconstruct both exact raw syntax universes. -/
theorem no_behavior_image_reconstructor_recovers_both :
    ¬ ∃ infer : (((Bool → Bool) → Prop) → RawUniverse),
      infer (ObservableImage universeA) = universeA ∧
      infer (ObservableImage universeB) = universeB := by
  rintro ⟨infer, hA, hB⟩
  apply raw_universes_are_distinct
  calc
    universeA = infer (ObservableImage universeA) := hA.symm
    _ = infer (ObservableImage universeB) := by rw [same_observable_behavior_image]
    _ = universeB := hB

/-- Operational quotient is the justified object: exact raw syntax identity is
    underdetermined whenever verifier-equivalent raw candidates exist. -/
theorem verifier_consequence_does_not_identify_exact_raw_candidate_universe :
    universeA ≠ universeB ∧
    ObservableImage universeA = ObservableImage universeB ∧
    ¬ ∃ infer : (((Bool → Bool) → Prop) → RawUniverse),
      infer (ObservableImage universeA) = universeA ∧
      infer (ObservableImage universeB) = universeB := by
  exact ⟨raw_universes_are_distinct,
    same_observable_behavior_image,
    no_behavior_image_reconstructor_recovers_both⟩

#check raw_universes_are_distinct
#check same_observable_behavior_image
#check no_behavior_image_reconstructor_recovers_both
#check verifier_consequence_does_not_identify_exact_raw_candidate_universe

end VerifierCannotIdentifyExactRawCandidateUniverse

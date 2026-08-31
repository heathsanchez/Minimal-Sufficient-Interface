namespace RawHypothesisCarrierIdentifiabilityBoundary

/-- A raw hypothesis world exposes only a carrier of hypotheses and the verifier
    consequence produced by each raw hypothesis.  No syntax, grammar, or
    enumeration of hypotheses is assumed. -/
structure HypothesisWorld where
  Hyp : Type
  verdict : Hyp → Bool

/-- What consequence can currently observe of a raw hypothesis carrier: the set
    of verifier verdicts realized somewhere in that carrier. -/
def ObservableImage (W : HypothesisWorld) : Bool → Prop :=
  fun b => ∃ h : W.Hyp, W.verdict h = b

/-- A one-hypothesis raw carrier. -/
def unitWorld : HypothesisWorld where
  Hyp := Unit
  verdict := fun _ => false

/-- A two-hypothesis raw carrier with exactly the same current consequence on
    every hypothesis. -/
def boolWorld : HypothesisWorld where
  Hyp := Bool
  verdict := fun _ => false

/-- The two raw carriers differ in a genuine structural invariant: one has no
    distinct pair of hypotheses, while the other does. -/
def HasDistinctHypotheses (W : HypothesisWorld) : Prop :=
  ∃ a b : W.Hyp, a ≠ b

theorem unit_world_has_no_distinct_hypotheses :
    ¬ HasDistinctHypotheses unitWorld := by
  rintro ⟨a, b, hab⟩
  apply hab
  cases a
  cases b
  rfl

theorem bool_world_has_distinct_hypotheses :
    HasDistinctHypotheses boolWorld := by
  refine ⟨false, true, ?_⟩
  intro h
  cases h

/-- Despite their different raw carrier structure, the currently observable
    consequence images are extensionally identical. -/
theorem same_current_consequence_image :
    ObservableImage unitWorld = ObservableImage boolWorld := by
  funext b
  apply propext
  constructor
  · rintro ⟨h, hh⟩
    exact ⟨false, hh⟩
  · rintro ⟨h, hh⟩
    exact ⟨(), hh⟩

/-- No deterministic classifier seeing only the current consequence image can
    correctly decide raw-carrier multiplicity in both worlds. -/
theorem no_consequence_only_multiplicity_classifier :
    ¬ ∃ infer : (Bool → Prop) → Bool,
      infer (ObservableImage unitWorld) = false ∧
      infer (ObservableImage boolWorld) = true := by
  rintro ⟨infer, hunit, hbool⟩
  have hsame :
      infer (ObservableImage unitWorld) = infer (ObservableImage boolWorld) := by
    rw [same_current_consequence_image]
  have : false = true := by
    calc
      false = infer (ObservableImage unitWorld) := hunit.symm
      _ = infer (ObservableImage boolWorld) := hsame
      _ = true := hbool
  cases this

/-- Consequently, current verifier consequence does not determine even the
    elementary invariant "does the raw hypothesis carrier contain two distinct
    hypotheses?".  Exact raw carrier reconstruction is therefore not justified
    by this consequence alone. -/
theorem raw_hypothesis_carrier_not_identifiable_from_current_consequence :
    (¬ HasDistinctHypotheses unitWorld) ∧
    HasDistinctHypotheses boolWorld ∧
    ObservableImage unitWorld = ObservableImage boolWorld ∧
    ¬ ∃ infer : (Bool → Prop) → Bool,
      infer (ObservableImage unitWorld) = false ∧
      infer (ObservableImage boolWorld) = true := by
  exact ⟨
    unit_world_has_no_distinct_hypotheses,
    bool_world_has_distinct_hypotheses,
    same_current_consequence_image,
    no_consequence_only_multiplicity_classifier⟩

#check unit_world_has_no_distinct_hypotheses
#check bool_world_has_distinct_hypotheses
#check same_current_consequence_image
#check no_consequence_only_multiplicity_classifier
#check raw_hypothesis_carrier_not_identifiable_from_current_consequence

end RawHypothesisCarrierIdentifiabilityBoundary

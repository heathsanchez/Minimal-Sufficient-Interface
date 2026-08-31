import RawHypothesisCarrierIdentifiabilityBoundary

namespace VerifierInducesOperationalHypothesisQuotient

open RawHypothesisCarrierIdentifiabilityBoundary

/-- Verifier-indistinguishability is the operational equality justified by the
    current consequence. -/
def verifierSetoid {α : Type} (V : α → Bool) : Setoid α where
  r a b := V a = V b
  iseqv := {
    refl := fun _ => rfl
    symm := fun h => h.symm
    trans := fun h₁ h₂ => h₁.trans h₂
  }

/-- The canonical hypothesis type justified by the verifier: raw hypotheses
    modulo current consequential indistinguishability. -/
abbrev OperationalHypothesis {α : Type} (V : α → Bool) :=
  Quotient (verifierSetoid V)

def roleOf {α : Type} (V : α → Bool) (h : α) : OperationalHypothesis V :=
  Quotient.mk (verifierSetoid V) h

/-- The verifier descends canonically to the operational quotient. -/
def verdictOnOperational {α : Type} (V : α → Bool) :
    OperationalHypothesis V → Bool :=
  Quotient.lift V (by
    intro a b hab
    exact hab)

theorem quotient_is_sufficient_for_verifier {α : Type} (V : α → Bool) (h : α) :
    verdictOnOperational V (roleOf V h) = V h := by
  rfl

/-- Equality in the induced quotient is exactly current verifier
    indistinguishability. -/
theorem same_operational_hypothesis_iff_same_verdict
    {α : Type} (V : α → Bool) (a b : α) :
    roleOf V a = roleOf V b ↔ V a = V b := by
  constructor
  · intro h
    exact Quotient.exact h
  · intro h
    exact Quotient.sound h

/-- Every representation sufficient to reproduce the verifier must distinguish
    hypotheses that the verifier distinguishes. -/
theorem every_sufficient_encoding_preserves_verifier_distinctions
    {α β : Type} (V : α → Bool)
    (encode : α → β) (decode : β → Bool)
    (sufficient : ∀ h, decode (encode h) = V h)
    {a b : α} (hdiff : V a ≠ V b) :
    encode a ≠ encode b := by
  intro hab
  apply hdiff
  calc
    V a = decode (encode a) := (sufficient a).symm
    _ = decode (encode b) := by rw [hab]
    _ = V b := sufficient b

/-- In the two-element raw witness from the carrier-identifiability boundary,
    the current verifier justifiably collapses both hidden hypotheses. -/
theorem hidden_raw_multiplicity_collapses_operationally :
    roleOf boolWorld.verdict false = roleOf boolWorld.verdict true := by
  apply Quotient.sound
  rfl

/-- A genuinely new consequence over the same raw carrier can withdraw that
    permission to forget and split the formerly collapsed class. -/
def refinedVerdict : Bool → Bool := fun b => b

theorem new_consequence_splits_previously_collapsed_class :
    roleOf refinedVerdict false ≠ roleOf refinedVerdict true := by
  intro h
  have hv : refinedVerdict false = refinedVerdict true :=
    Quotient.exact h
  cases hv

/-- Main result: consequence canonically induces an operational hypothesis type;
    this quotient is sufficient for the verifier, every sufficient encoding must
    preserve its verifier-visible distinctions, hidden raw multiplicity may be
    collapsed, and new consequence can refine the induced type by splitting an
    old class. -/
theorem verifier_induces_and_refines_operational_hypothesis_type :
    roleOf boolWorld.verdict false = roleOf boolWorld.verdict true ∧
    roleOf refinedVerdict false ≠ roleOf refinedVerdict true := by
  exact ⟨
    hidden_raw_multiplicity_collapses_operationally,
    new_consequence_splits_previously_collapsed_class⟩

#check quotient_is_sufficient_for_verifier
#check same_operational_hypothesis_iff_same_verdict
#check every_sufficient_encoding_preserves_verifier_distinctions
#check hidden_raw_multiplicity_collapses_operationally
#check new_consequence_splits_previously_collapsed_class
#check verifier_induces_and_refines_operational_hypothesis_type

end VerifierInducesOperationalHypothesisQuotient

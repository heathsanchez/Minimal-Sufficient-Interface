import KernelPurificationCycle8
import ResidualGeneratedProbeGenesis

namespace KernelPurificationCycle9

open KernelPurificationCycle8
open ResidualGeneratedProbeGenesis

universe u v w

/-- A current consequence language is only an index type together with the
    proposition-valued observations its coordinates denote. -/
structure ConsequenceLanguage (Ω : Type u) (I : Type v) where
  observe : I → Ω → Prop

/-- A certified residual is invisible to every coordinate in the current
    language.  No candidate new coordinate occurs in this witness. -/
structure LanguageBlindResidual
    {Ω : Type u} {I : Type v}
    (L : ConsequenceLanguage Ω I) (r : Residual Ω) : Prop where
  oldBlind : ∀ i : I, L.observe i r.left ↔ L.observe i r.right

/-- The residual itself extends the coordinate language by one freely generated
    coordinate.  The new coordinate's denotation is `generatedProbe r`; no
    externally supplied probe identity or candidate list is an argument. -/
def extendFromResidual
    {Ω : Type u} {I : Type v}
    (L : ConsequenceLanguage Ω I) (r : Residual Ω) :
    ConsequenceLanguage Ω (Sum I Unit) where
  observe
    | Sum.inl i => L.observe i
    | Sum.inr _ => generatedProbe r

/-- Every old consequence coordinate is retained definitionally. -/
theorem old_coordinates_retained
    {Ω : Type u} {I : Type v}
    (L : ConsequenceLanguage Ω I) (r : Residual Ω) (i : I) :
    (extendFromResidual L r).observe (Sum.inl i) = L.observe i := rfl

/-- The newly generated coordinate is exactly the observation constructed from
    the residual itself. -/
theorem residual_coordinate_is_generated
    {Ω : Type u} {I : Type v}
    (L : ConsequenceLanguage Ω I) (r : Residual Ω) :
    (extendFromResidual L r).observe (Sum.inr ()) = generatedProbe r := rfl

/-- The generated coordinate separates the very residual that forced its
    existence. -/
theorem residual_coordinate_separates
    {Ω : Type u} {I : Type v}
    (L : ConsequenceLanguage Ω I) (r : Residual Ω) :
    ¬ (extendFromResidual L r).observe (Sum.inr ()) r.left ∧
      (extendFromResidual L r).observe (Sum.inr ()) r.right := by
  exact generatedProbe_separates r

/-- If the current language is blind to the residual, every old coordinate
    still aliases the failed pair. -/
theorem old_language_remains_blind
    {Ω : Type u} {I : Type v}
    (L : ConsequenceLanguage Ω I) (r : Residual Ω)
    (hblind : LanguageBlindResidual L r) :
    ∀ i : I, L.observe i r.left ↔ L.observe i r.right := by
  exact hblind.oldBlind

/-- Under certified old-language blindness, the residual-generated coordinate
    is genuinely new: it cannot denote the same consequence as any old
    coordinate. -/
theorem generated_coordinate_not_old
    {Ω : Type u} {I : Type v}
    (L : ConsequenceLanguage Ω I) (r : Residual Ω)
    (hblind : LanguageBlindResidual L r) :
    ∀ i : I, L.observe i ≠ generatedProbe r := by
  intro i heq
  have hold := hblind.oldBlind i
  have hsep := generatedProbe_separates r
  have hleft : ¬ L.observe i r.left := by
    intro hl
    have : generatedProbe r r.left := by
      rw [← heq]
      exact hl
    exact hsep.1 this
  have hright : L.observe i r.right := by
    rw [heq]
    exact hsep.2
  exact hleft (hold.mpr hright)

/-- The language extension is the free coproduct of the old coordinate type
    with the single residual-generated coordinate: any interpretation of the
    old coordinates plus an interpretation of the generated coordinate extends
    uniquely over the new language. -/
def languageLift
    {I : Type v} {J : Type w}
    (oldMap : I → J) (generated : J) : Sum I Unit → J
  | Sum.inl i => oldMap i
  | Sum.inr _ => generated

theorem languageLift_old
    {I : Type v} {J : Type w}
    (oldMap : I → J) (generated : J) (i : I) :
    languageLift oldMap generated (Sum.inl i) = oldMap i := rfl

theorem languageLift_generated
    {I : Type v} {J : Type w}
    (oldMap : I → J) (generated : J) :
    languageLift oldMap generated (Sum.inr ()) = generated := rfl

theorem languageLift_unique
    {I : Type v} {J : Type w}
    (oldMap : I → J) (generated : J)
    (f : Sum I Unit → J)
    (hold : ∀ i : I, f (Sum.inl i) = oldMap i)
    (hgen : f (Sum.inr ()) = generated) :
    f = languageLift oldMap generated := by
  funext x
  cases x with
  | inl i => exact hold i
  | inr u =>
      cases u
      exact hgen

/-- Exact ablation: before extension, every available coordinate aliases the
    residual; after extension, a self-generated coordinate separates it. -/
theorem residual_language_genesis_is_causal
    {Ω : Type u} {I : Type v}
    (L : ConsequenceLanguage Ω I) (r : Residual Ω)
    (hblind : LanguageBlindResidual L r) :
    (∀ i : I, L.observe i r.left ↔ L.observe i r.right) ∧
    (¬ (extendFromResidual L r).observe (Sum.inr ()) r.left ∧
      (extendFromResidual L r).observe (Sum.inr ()) r.right) := by
  exact ⟨hblind.oldBlind, residual_coordinate_separates L r⟩

/-- Cycle-9 decision: the identity of the next consequence coordinate and the
    one-step language extension need not be supplied.  Certified blindness plus
    the residual itself determines a genuinely new separating coordinate, and
    the resulting coordinate extension has the expected free universal
    property. -/
theorem residual_generates_free_consequence_language_extension
    {Ω : Type u} {I : Type v}
    (L : ConsequenceLanguage Ω I) (r : Residual Ω)
    (hblind : LanguageBlindResidual L r) :
    (∀ i : I, L.observe i ≠ generatedProbe r) ∧
    (¬ (extendFromResidual L r).observe (Sum.inr ()) r.left ∧
      (extendFromResidual L r).observe (Sum.inr ()) r.right) ∧
    (∀ (J : Type) (oldMap : I → J) (generated : J)
      (f : Sum I Unit → J),
      (∀ i : I, f (Sum.inl i) = oldMap i) →
      f (Sum.inr ()) = generated →
      f = languageLift oldMap generated) := by
  constructor
  · exact generated_coordinate_not_old L r hblind
  constructor
  · exact residual_coordinate_separates L r
  · intro J oldMap generated f hold hgen
    exact languageLift_unique oldMap generated f hold hgen

#check old_coordinates_retained
#check residual_coordinate_is_generated
#check residual_coordinate_separates
#check generated_coordinate_not_old
#check languageLift_unique
#check residual_language_genesis_is_causal
#check residual_generates_free_consequence_language_extension

end KernelPurificationCycle9

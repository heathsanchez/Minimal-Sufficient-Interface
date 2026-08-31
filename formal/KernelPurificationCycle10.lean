import KernelPurificationCycle9
import VerifiedConsequenceGenesis

namespace KernelPurificationCycle10

open KernelPurificationCycle9
open ResidualGeneratedProbeGenesis
open VerifiedConsequenceGenesis

universe u v w

/-- For proposition-valued consequences, fiber constancy is already enough for
    factorization through an arbitrary representation.  No section or
    surjectivity witness for the representation is required. -/
theorem prop_fiber_constancy_implies_factorsThrough
    {X : Type u} {R : Type v}
    (q : X → R) (c : X → Prop)
    (hconst : ∀ x y : X, q x = q y → (c x ↔ c y)) :
    FactorsThrough q c := by
  refine ⟨fun r => ∃ x : X, q x = r ∧ c x, ?_⟩
  intro x
  apply propext
  constructor
  · intro hx
    exact ⟨x, rfl, hx⟩
  · rintro ⟨y, hy, hcy⟩
    exact (hconst y x hy).mp hcy

/-- The canonical support of a global factorization failure consists of all
    pairs collapsed by the current representation but separated by the
    consequentially required proposition. -/
def NonFactorSupport
    {X : Type u} {R : Type v}
    (q : X → R) (c : X → Prop) (p : X × X) : Prop :=
  q p.1 = q p.2 ∧ ¬ (c p.1 ↔ c p.2)

abbrev ResidualIndex
    {X : Type u} {R : Type v}
    (q : X → R) (c : X → Prop) :=
  {p : X × X // NonFactorSupport q c p}

/-- A global non-factorization certificate necessarily makes the canonical
    residual support nonempty.  No failed pair is supplied as input. -/
theorem nonfactorization_support_nonempty
    {X : Type u} {R : Type v}
    (q : X → R) (c : X → Prop)
    (hfail : ¬ FactorsThrough q c) :
    Nonempty (ResidualIndex q c) := by
  classical
  by_cases h : ∃ p : X × X, NonFactorSupport q c p
  · rcases h with ⟨p, hp⟩
    exact ⟨⟨p, hp⟩⟩
  · exfalso
    apply hfail
    apply prop_fiber_constancy_implies_factorsThrough q c
    intro x y hq
    by_cases hxy : c x ↔ c y
    · exact hxy
    · exact False.elim (h ⟨(x, y), hq, hxy⟩)

/-- Every canonical failed pair is genuinely a residual and therefore carries
    its own self-generated separator. -/
def residualOfSupport
    {X : Type u} {R : Type v}
    {q : X → R} {c : X → Prop}
    (p : ResidualIndex q c) : Residual X where
  left := p.1.1
  right := p.1.2
  distinct := by
    intro heq
    apply p.2.2
    subst heq
    rfl

/-- The old consequence language is representation-mediated: each old
    coordinate factors through q. -/
def LanguageFactorsThrough
    {X : Type u} {I : Type v} {R : Type w}
    (L : ConsequenceLanguage X I) (q : X → R) : Prop :=
  ∀ i : I, FactorsThrough q (L.observe i)

/-- Any old coordinate that factors through q is blind to every pair in the
    canonical non-factorization support. -/
theorem old_language_blind_on_nonfactor_support
    {X : Type u} {I : Type v} {R : Type w}
    (L : ConsequenceLanguage X I) (q : X → R) (c : X → Prop)
    (hfactor : LanguageFactorsThrough L q)
    (p : ResidualIndex q c) :
    L.observe p.1.1 p.1.2 ↔ L.observe p.1.1 p.1.1 := by
  have heq : L.observe p.1.1 p.1.1 = L.observe p.1.1 p.1.2 :=
    factorsThrough_implies_fiber_constancy q (L.observe p.1.1)
      (hfactor p.1.1) p.1.1 p.1.2 p.2.1
  exact (iff_of_eq heq).symm

/-- Extend the old language by *all* consequence coordinates generated from the
    canonical non-factorization support.  Neither a failed pair nor a new probe
    identity is selected externally. -/
def extendFromNonfactorSupport
    {X : Type u} {I : Type v} {R : Type w}
    (L : ConsequenceLanguage X I) (q : X → R) (c : X → Prop) :
    ConsequenceLanguage X (Sum I (ResidualIndex q c)) where
  observe
    | Sum.inl i => L.observe i
    | Sum.inr p => generatedProbe (residualOfSupport p)

/-- Old coordinates are retained exactly. -/
theorem nonfactor_extension_retains_old
    {X : Type u} {I : Type v} {R : Type w}
    (L : ConsequenceLanguage X I) (q : X → R) (c : X → Prop)
    (i : I) :
    (extendFromNonfactorSupport L q c).observe (Sum.inl i) = L.observe i := rfl

/-- Every generated support-coordinate separates its own certified failed pair. -/
theorem every_nonfactor_support_coordinate_separates
    {X : Type u} {I : Type v} {R : Type w}
    (L : ConsequenceLanguage X I) (q : X → R) (c : X → Prop)
    (p : ResidualIndex q c) :
    ¬ (extendFromNonfactorSupport L q c).observe (Sum.inr p) p.1.1 ∧
      (extendFromNonfactorSupport L q c).observe (Sum.inr p) p.1.2 := by
  exact generatedProbe_separates (residualOfSupport p)

/-- Under representation-mediated old observations, every support-generated
    coordinate is genuinely absent from the old language. -/
theorem support_generated_coordinates_are_new
    {X : Type u} {I : Type v} {R : Type w}
    (L : ConsequenceLanguage X I) (q : X → R) (c : X → Prop)
    (hfactor : LanguageFactorsThrough L q)
    (p : ResidualIndex q c) :
    ∀ i : I, L.observe i ≠ generatedProbe (residualOfSupport p) := by
  intro i heq
  have holdEq : L.observe i p.1.1 = L.observe i p.1.2 :=
    factorsThrough_implies_fiber_constancy q (L.observe i)
      (hfactor i) p.1.1 p.1.2 p.2.1
  have hsep := generatedProbe_separates (residualOfSupport p)
  have hleft : ¬ L.observe i p.1.1 := by
    intro hl
    have : generatedProbe (residualOfSupport p) p.1.1 := by
      rw [← heq]
      exact hl
    exact hsep.1 this
  have hright : L.observe i p.1.2 := by
    rw [heq]
    exact hsep.2
  exact hleft (Eq.mp holdEq.symm hright)

/-- The full support extension has the coproduct universal property: any target
    receiving all old coordinates and all support-generated coordinates admits
    one unique interpretation of the enlarged coordinate language. -/
def fullLanguageLift
    {I : Type v} {G : Type w} {J : Type u}
    (oldMap : I → J) (genMap : G → J) : Sum I G → J
  | Sum.inl i => oldMap i
  | Sum.inr g => genMap g

theorem fullLanguageLift_unique
    {I : Type v} {G : Type w} {J : Type u}
    (oldMap : I → J) (genMap : G → J)
    (f : Sum I G → J)
    (hold : ∀ i, f (Sum.inl i) = oldMap i)
    (hgen : ∀ g, f (Sum.inr g) = genMap g) :
    f = fullLanguageLift oldMap genMap := by
  funext x
  cases x with
  | inl i => exact hold i
  | inr g => exact hgen g

/-- Cycle-10 decision: even the failed pair need not be supplied.  A global
    verifier-visible non-factorization determines a canonical *support of all
    failed pairs*; those pairs generate their own new consequence coordinates,
    and the resulting language extension is free. -/
theorem global_nonfactorization_generates_residual_language
    {X : Type u} {I : Type v} {R : Type w}
    (L : ConsequenceLanguage X I) (q : X → R) (c : X → Prop)
    (hfactor : LanguageFactorsThrough L q)
    (hfail : ¬ FactorsThrough q c) :
    Nonempty (ResidualIndex q c) ∧
    (∀ p : ResidualIndex q c,
      (∀ i : I, L.observe i ≠ generatedProbe (residualOfSupport p)) ∧
      (¬ (extendFromNonfactorSupport L q c).observe (Sum.inr p) p.1.1 ∧
        (extendFromNonfactorSupport L q c).observe (Sum.inr p) p.1.2)) := by
  constructor
  · exact nonfactorization_support_nonempty q c hfail
  · intro p
    exact ⟨support_generated_coordinates_are_new L q c hfactor p,
      every_nonfactor_support_coordinate_separates L q c p⟩

#check prop_fiber_constancy_implies_factorsThrough
#check nonfactorization_support_nonempty
#check residualOfSupport
#check extendFromNonfactorSupport
#check support_generated_coordinates_are_new
#check fullLanguageLift_unique
#check global_nonfactorization_generates_residual_language

end KernelPurificationCycle10

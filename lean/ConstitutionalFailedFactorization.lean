import Std

universe u v w z

namespace ConstitutionalFailedFactorization

/-- The kernel equivalence induced by an interface. -/
def KernelEq {P : Type u} {E : Type v} (I : P → E) : P → P → Prop :=
  fun x y => I x = I y

/-- Refinement order on binary relations: `R` is finer than `S`. -/
def Refines {P : Type u} (R S : P → P → Prop) : Prop :=
  ∀ ⦃x y⦄, R x y → S x y

/-- The decision-sufficient constitutional refinement: preserve the old
    interface and every protected decision distinction. -/
def ConstitutionalRefinement
    {P : Type u} {E : Type v} {Q : Type w} {A : Q → Type z}
    (I : P → E) (D : (q : Q) → P → A q) : P → P → Prop :=
  fun x y => I x = I y ∧ ∀ q, D q x = D q y

/-- Theorem A: if the evidence interface identifies two constitutions but a
    protected decision separates them, that decision cannot factor through
    the interface. -/
theorem failed_factorization
    {P : Type u} {E : Type v} {A : Type w}
    (I : P → E) (D : P → A) {p₁ p₂ : P}
    (hI : I p₁ = I p₂) (hD : D p₁ ≠ D p₂) :
    ¬ ∃ g : E → A, ∀ p, D p = g (I p) := by
  rintro ⟨g, hg⟩
  apply hD
  calc
    D p₁ = g (I p₁) := hg p₁
    _ = g (I p₂) := congrArg g hI
    _ = D p₂ := (hg p₂).symm

/-- Equivalent kernel form of Theorem A. -/
theorem residual_witnesses_insufficiency
    {P : Type u} {E : Type v} {A : Type w}
    (I : P → E) (D : P → A) {p₁ p₂ : P}
    (hI : KernelEq I p₁ p₂) (hD : D p₁ ≠ D p₂) :
    ¬ Refines (KernelEq I) (KernelEq D) := by
  intro h
  exact hD (h hI)

/-- Theorem B, part 1: the canonical constitutional repair refines the
    original evidence interface. -/
theorem refinement_refines_interface
    {P : Type u} {E : Type v} {Q : Type w} {A : Q → Type z}
    (I : P → E) (D : (q : Q) → P → A q) :
    Refines (ConstitutionalRefinement I D) (KernelEq I) := by
  intro x y h
  exact h.1

/-- Theorem B, part 2: every protected decision is constant on classes of
    the canonical constitutional repair. -/
theorem refinement_is_decision_sufficient
    {P : Type u} {E : Type v} {Q : Type w} {A : Q → Type z}
    (I : P → E) (D : (q : Q) → P → A q) (q : Q) :
    Refines (ConstitutionalRefinement I D) (KernelEq (D q)) := by
  intro x y h
  exact h.2 q

/-- Theorem B, universal property: every relation that refines the old
    interface and preserves every protected decision is finer than the
    canonical repair. Hence the canonical repair is the unique coarsest
    decision-sufficient refinement at the relation level. -/
theorem coarsest_decision_sufficient_refinement
    {P : Type u} {E : Type v} {Q : Type w} {A : Q → Type z}
    (I : P → E) (D : (q : Q) → P → A q)
    (R : P → P → Prop)
    (hI : Refines R (KernelEq I))
    (hD : ∀ q, Refines R (KernelEq (D q))) :
    Refines R (ConstitutionalRefinement I D) := by
  intro x y hxy
  exact ⟨hI hxy, fun q => hD q hxy⟩

/-- A residual forces strict refinement: the old interface relates a pair
    that the canonical repair separates. -/
theorem residual_forces_strict_refinement
    {P : Type u} {E : Type v} {Q : Type w} {A : Q → Type z}
    (I : P → E) (D : (q : Q) → P → A q)
    {q : Q} {p₁ p₂ : P}
    (hI : I p₁ = I p₂) (hD : D q p₁ ≠ D q p₂) :
    KernelEq I p₁ p₂ ∧ ¬ ConstitutionalRefinement I D p₁ p₂ := by
  constructor
  · exact hI
  · intro h
    exact hD (h.2 q)

/-- Theorem C: deterministic post-processing cannot split a fibre already
    collapsed by the evidence interface. Equivalently,
    `ker(I) ⊆ ker(R ∘ I)`. -/
theorem postprocessing_cannot_split
    {P : Type u} {E : Type v} {E' : Type w}
    (I : P → E) (R : E → E') :
    Refines (KernelEq I) (KernelEq (R ∘ I)) := by
  intro x y h
  exact congrArg R h

/-- Corollary of Theorem C specialized to a residual pair. -/
theorem missing_distinction_not_from_postprocessing
    {P : Type u} {E : Type v} {E' : Type w} {A : Type z}
    (I : P → E) (R : E → E') (D : P → A) {p₁ p₂ : P}
    (hI : I p₁ = I p₂) (hD : D p₁ ≠ D p₂) :
    (R ∘ I) p₁ = (R ∘ I) p₂ ∧ D p₁ ≠ D p₂ := by
  exact ⟨congrArg R hI, hD⟩

end ConstitutionalFailedFactorization

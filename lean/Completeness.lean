import Kernel

universe u v w

namespace MSICompleteness

open EquivalentOn

variable {X : Type u} {C : Type v} {O : Type w}
variable (P : X → C → O)

/-- There is a live global residual exactly when a pair is merged by B but split by T. -/
def GlobalResidual (B T : List C) : Prop :=
  ∃ x y : X, EquivalentOn P B x y ∧ ¬ EquivalentOn P T x y

/-- No residual means every current equivalence is valid under the protected target family. -/
def NoResidual (B T : List C) : Prop :=
  ∀ x y : X, EquivalentOn P B x y → EquivalentOn P T x y

/-- Existential residual and universal no-residual are exact negations. -/
theorem noResidual_iff_not_globalResidual (B T : List C) :
    NoResidual P B T ↔ ¬ GlobalResidual P B T := by
  constructor
  · intro h hres
    rcases hres with ⟨x, y, hB, hnotT⟩
    exact hnotT (h x y hB)
  · intro h x y hB
    by_contra hnotT
    exact h ⟨x, y, hB, hnotT⟩

/-- If the retained family B is covered by target T, target-equivalence implies B-equivalence. -/
theorem target_implies_current
    (B T : List C)
    (hsub : ∀ c, c ∈ B → c ∈ T)
    {x y : X}
    (hT : EquivalentOn P T x y) :
    EquivalentOn P B x y := by
  intro c hc
  exact hT c (hsub c hc)

/-- Exact stopping theorem.

Under coverage B ⊆ T, absence of any global residual is equivalent to the
current and protected equivalence relations agreeing extensionally.
-/
theorem noResidual_iff_extensional_sufficiency
    (B T : List C)
    (hsub : ∀ c, c ∈ B → c ∈ T) :
    NoResidual P B T ↔
      ∀ x y : X, EquivalentOn P B x y ↔ EquivalentOn P T x y := by
  constructor
  · intro h x y
    constructor
    · exact h x y
    · intro hT
      exact target_implies_current P B T hsub hT
  · intro h x y hB
    exact (h x y).mp hB

/-- Counterexample form of the stopping theorem. -/
theorem complete_iff_no_counterexample
    (B T : List C)
    (hsub : ∀ c, c ∈ B → c ∈ T) :
    (∀ x y : X, EquivalentOn P B x y ↔ EquivalentOn P T x y) ↔
      ¬ GlobalResidual P B T := by
  rw [← noResidual_iff_extensional_sufficiency P B T hsub]
  exact noResidual_iff_not_globalResidual P B T

end MSICompleteness

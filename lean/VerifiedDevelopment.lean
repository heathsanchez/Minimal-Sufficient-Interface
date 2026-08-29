import Std
import ResidualRegimeBridge
import GeneratedStage
import FactorizationSufficiency
import ResourceIndexedConsequence

universe u v w

namespace VerifiedDevelopment

open BehaviouralCongruence
open ResidualRegimeBridge

variable {M : Type u} {X : Type v} {O : Type w}
variable (A : ActionMonoid M X) (obs : X → O)

/-- Everything the existing semantic kernel can certify from one verified
    residual, packaged as one developmental step. -/
structure VerifiedStep (B : List M) (c : M) : Prop where
  strict : ∃ x y, EqBy A obs B x y ∧ ¬ EqBy A obs (c :: B) x y
  coarsest : ∀ R : X → X → Prop,
    AdmissibleRepair A obs B c R →
    ∀ x y, R x y → EqBy A obs (c :: B) x y
  blockedBefore : ¬ CanDescend A obs B c
  enabledAfter : CanDescend A obs (c :: B) c
  ablationRestores : ¬ CanDescend A obs B c

/-- A verified residual is sufficient to derive the entire one-step transition:
    strict ontology change, unique coarsest repair, capability gain, and exact
    ablation. No search or representation-choice axiom is needed here. -/
theorem residual_yields_verified_step
    (B : List M) (c : M)
    (hρ : Residual A obs B c) :
    VerifiedStep A obs B c := by
  have h := residual_to_minimal_regime_and_capability A obs B c hρ
  exact {
    strict := h.1
    coarsest := h.2.1
    blockedBefore := h.2.2.1
    enabledAfter := h.2.2.2.1
    ablationRestores := h.2.2.2.2
  }

/-- The precise extra ingredient required to turn arbitrary task failure into a
    recursive developmental transition. The existing quotient/refinement
    theorems do not manufacture a distinguishing continuation from an opaque
    failure; some sound generator/oracle must expose one. -/
def SeparatorOracle (Failure : List M → Prop) : Prop :=
  ∀ B, Failure B → ∃ c, Residual A obs B c

/-- Once the separator oracle is supplied, arbitrary certified failure lifts
    immediately into an actual verified developmental step. Thus the missing
    theorem boundary is exactly `Failure B -> exists c, Residual ...`, not the
    quotient repair or capability transition after a separator is known. -/
theorem failure_yields_verified_development
    (Failure : List M → Prop)
    (oracle : SeparatorOracle A obs Failure)
    (B : List M) (hFail : Failure B) :
    ∃ c, VerifiedStep A obs B c := by
  rcases oracle B hFail with ⟨c, hρ⟩
  exact ⟨c, residual_yields_verified_step A obs B c hρ⟩

/-- A two-generation compounding theorem. The second step may be generated only
    after the first repaired regime exists. This is the formal recursive shape
    seen in the branch experiments; the only non-kernel hypotheses are the two
    separator-generation facts. -/
theorem two_generation_compounding
    (B : List M) (c₁ c₂ : M)
    (h₁ : Residual A obs B c₁)
    (h₂ : Residual A obs (c₁ :: B) c₂) :
    VerifiedStep A obs B c₁ ∧
    VerifiedStep A obs (c₁ :: B) c₂ := by
  exact ⟨
    residual_yields_verified_step A obs B c₁ h₁,
    residual_yields_verified_step A obs (c₁ :: B) c₂ h₂
  ⟩

/-- Exact ancestor ablation statement for the two-generation case: deleting
    the first promotion returns to a regime in which the first continuation is
    again impossible to execute through the quotient. -/
theorem ancestor_ablation_restores_first_obstruction
    (B : List M) (c₁ : M)
    (h₁ : Residual A obs B c₁) :
    ¬ CanDescend A obs B c₁ := by
  exact residual_blocks_old_capability A obs B c₁ h₁

end VerifiedDevelopment

import Std
import DevelopmentalFailureTaxonomy
import FiniteProtectedCompleteness

universe u v w

namespace VerifiedDevelopmentalController

open DevelopmentalFailureTaxonomy
open FiniteProtectedCompleteness
open EquivalentOn

/-- A certified regime always has a deterministic lawful controller move. This
    theorem is intentionally conditional on an external evidence certificate;
    it does not classify arbitrary opaque failure. -/
theorem certified_regime_has_lawful_move
    (e : EvidenceClass) :
    ∃ m : DevelopmentMove, route e = m := by
  exact ⟨route e, rfl⟩

/-- Every certified evidence class routes to exactly one controller action. -/
theorem certified_route_unique
    (e : EvidenceClass) (m₁ m₂ : DevelopmentMove)
    (h₁ : route e = m₁) (h₂ : route e = m₂) :
    m₁ = m₂ := by
  exact h₁.symm.trans h₂

/-- The five certified regimes are exhaustive for the evidence type itself. -/
theorem five_way_route
    (e : EvidenceClass) :
    route e = .split ∨
    route e = .extend ∨
    route e = .promote ∨
    route e = .wait ∨
    route e = .observe := by
  cases e <;> simp [route]

/-- In a finite protected regime with explicit coverage, the controller never
    faces an opaque extensional inadequacy: either the current interface is
    already complete for the protected family, or separator evidence exists and
    the lawful next controller move is SPLIT. -/
theorem finite_covered_regime_stops_or_splits
    {X : Type u} {C : Type v} {O : Type w}
    (P : X → C → O) (B T : List C)
    (hsub : ∀ c, c ∈ B → c ∈ T) :
    (∀ x y : X, EquivalentOn P B x y ↔ EquivalentOn P T x y) ∨
    (∃ x y : X,
      EquivalentOn P B x y ∧
      ProtectedSeparator (fun t x => P x t) T x y ∧
      route .separator = .split) := by
  rcases finite_protected_completeness P B T hsub with hcomplete | hsep
  · exact Or.inl hcomplete
  · right
    rcases hsep with ⟨x, y, hB, hs⟩
    exact ⟨x, y, hB, hs, rfl⟩

/-- Opaque failure is therefore not a valid controller state once finite
    protected coverage and extensional inadequacy have both been certified. -/
theorem finite_covered_inadequacy_forces_split
    {X : Type u} {C : Type v} {O : Type w}
    (P : X → C → O) (B T : List C)
    (hsub : ∀ c, c ∈ B → c ∈ T)
    (hbad : ¬ (∀ x y : X,
      EquivalentOn P B x y ↔ EquivalentOn P T x y)) :
    ∃ x y : X,
      EquivalentOn P B x y ∧
      ProtectedSeparator (fun t x => P x t) T x y ∧
      route .separator = .split := by
  rcases inadequacy_yields_protected_member_residual P B T hsub hbad with
    ⟨c, hc, hres⟩
  rcases member_residual_yields_separator_evidence P B T c hc hres with
    ⟨x, y, hB, hs⟩
  exact ⟨x, y, hB, hs, rfl⟩

end VerifiedDevelopmentalController

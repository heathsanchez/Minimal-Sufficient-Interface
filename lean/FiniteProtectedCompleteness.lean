import Std
import Completeness
import DevelopmentalFailureTaxonomy

universe u v w

namespace FiniteProtectedCompleteness

open EquivalentOn
open MSICompleteness
open DevelopmentalFailureTaxonomy

variable {X : Type u} {C : Type v} {O : Type w}
variable (P : X → C → O)

/-- A single protected consequence witnesses exactly which current equivalence
    class is too coarse. -/
def IndividualResidual (B : List C) (c : C) : Prop :=
  ∃ x y : X, EquivalentOn P B x y ∧ P x c ≠ P y c

/-- Every global residual over a finite protected list contains a concrete
    member consequence that separates the offending current-equivalent pair. -/
theorem globalResidual_yields_member_residual
    (B T : List C)
    (h : GlobalResidual P B T) :
    ∃ c, c ∈ T ∧ IndividualResidual P B c := by
  rcases h with ⟨x, y, hB, hnotT⟩
  have hex : ∃ c, c ∈ T ∧ P x c ≠ P y c := by
    apply Classical.byContradiction
    intro hnone
    apply hnotT
    intro c hc
    apply Classical.byContradiction
    intro hneq
    exact hnone ⟨c, hc, hneq⟩
  rcases hex with ⟨c, hc, hneq⟩
  exact ⟨c, hc, ⟨x, y, hB, hneq⟩⟩

/-- Under protected-family coverage, extensional inadequacy cannot remain an
    opaque failure: it yields a concrete member residual from the protected
    family. No search heuristic or separator oracle is assumed. -/
theorem inadequacy_yields_protected_member_residual
    (B T : List C)
    (hsub : ∀ c, c ∈ B → c ∈ T)
    (hbad : ¬ (∀ x y : X,
      EquivalentOn P B x y ↔ EquivalentOn P T x y)) :
    ∃ c, c ∈ T ∧ IndividualResidual P B c := by
  have hglobal : GlobalResidual P B T := by
    apply Classical.byContradiction
    intro hno
    have hcomplete : ∀ x y : X,
        EquivalentOn P B x y ↔ EquivalentOn P T x y :=
      (complete_iff_no_counterexample P B T hsub).2 hno
    exact hbad hcomplete
  exact globalResidual_yields_member_residual P B T hglobal

/-- The member residual induces the separator evidence used by the developmental
    controller: two states are merged by the current interface and separated by
    one protected consequence. -/
theorem member_residual_yields_separator_evidence
    (B T : List C) (c : C)
    (hc : c ∈ T)
    (h : IndividualResidual P B c) :
    ∃ x y : X,
      EquivalentOn P B x y ∧
      ProtectedSeparator (fun t x => P x t) T x y := by
  rcases h with ⟨x, y, hB, hneq⟩
  exact ⟨x, y, hB, ⟨c, hc, hneq⟩⟩

/-- Finite protected completeness dichotomy. Under B ⊆ T, either the current
    interface is extensionally sufficient for every protected consequence, or
    a concrete protected separator exists. This closes the opaque-failure
    boundary for this explicitly covered finite regime. -/
theorem finite_protected_completeness
    (B T : List C)
    (hsub : ∀ c, c ∈ B → c ∈ T) :
    (∀ x y : X, EquivalentOn P B x y ↔ EquivalentOn P T x y) ∨
    (∃ x y : X,
      EquivalentOn P B x y ∧
      ProtectedSeparator (fun t x => P x t) T x y) := by
  classical
  by_cases hcomplete : ∀ x y : X,
      EquivalentOn P B x y ↔ EquivalentOn P T x y
  · exact Or.inl hcomplete
  · right
    rcases inadequacy_yields_protected_member_residual P B T hsub hcomplete with
      ⟨c, hc, hres⟩
    exact member_residual_yields_separator_evidence P B T c hc hres

end FiniteProtectedCompleteness

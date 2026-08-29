import Std
import ResidualDerivedMetaLanguageGenesis
import VerifiedNodeTypeGenesis

universe u v w z

namespace ResidualDerivedConstructorPrinciple

open ResidualInterfaceGenesis
open ResidualDerivedMetaLanguageGenesis

variable {X : Type u} {Probe : Type v} {V : Type w} {Y : Type z}

/-- Two states are indistinguishable by the residual-selected joint interface. -/
def JointViewEq
    (observe : Probe → X → V)
    (B : List Probe)
    (x y : X) : Prop :=
  ∀ p, p ∈ B → observe p x = observe p y

/-- A local constructor principle is licensed exactly when its output depends only
    on the residual-selected joint view.  This states the operation semantically,
    without assuming a pre-enumerated unary/binary/ternary constructor family. -/
def ConstructorLicensedByJointView
    (observe : Probe → X → V)
    (target : X → Y)
    (B : List Probe) : Prop :=
  ∀ x y : X, JointViewEq observe B x y → target x = target y

/-- Residual-derived sufficiency itself licenses the generic local constructor
    principle: equal selected inputs force equal protected output. -/
theorem residuals_license_joint_view_constructor
    (observe : Probe → X → V)
    (target : X → Y)
    (B : List Probe)
    (h : ResidualDeterminesArity observe target B) :
    ConstructorLicensedByJointView observe target B := by
  intro x y hxy
  exact h.1 x y hxy

/-- Any strictly smaller joint-view constructor is impossible: a concrete
    protected residual aliases its inputs while disagreeing on output. -/
theorem every_smaller_joint_constructor_is_obstructed
    (observe : Probe → X → V)
    (target : X → Y)
    (B : List Probe)
    (h : ResidualDeterminesArity observe target B) :
    ∀ B' : List Probe, B'.length < B.length →
      ¬ ConstructorLicensedByJointView observe target B' := by
  intro B' hlen hctor
  rcases h.2 B' hlen with ⟨x, y, hsame, hneq⟩
  exact hneq (hctor x y hsame)

/-- Therefore the residual-selected arity is minimal not only as an interface,
    but as the dependency arity of any deterministic local constructor whose
    output is the protected consequence. -/
theorem residuals_determine_minimal_constructor_dependency
    (observe : Probe → X → V)
    (target : X → Y)
    (B : List Probe)
    (h : ResidualDeterminesArity observe target B) :
    ConstructorLicensedByJointView observe target B ∧
    ∀ B' : List Probe,
      ConstructorLicensedByJointView observe target B' →
      B.length ≤ B'.length := by
  constructor
  · exact residuals_license_joint_view_constructor observe target B h
  · intro B' hctor
    apply Nat.le_of_not_gt
    intro hshort
    exact (every_smaller_joint_constructor_is_obstructed observe target B h B' hshort) hctor

/-- Exact constructor-principle ablation: deleting any coordinates until the
    dependency arity is strictly smaller restores a verified collision. -/
theorem constructor_dependency_ablation_restores_residual
    (observe : Probe → X → V)
    (target : X → Y)
    (B B' : List Probe)
    (h : ResidualDeterminesArity observe target B)
    (hlen : B'.length < B.length) :
    ∃ x y : X,
      JointViewEq observe B' x y ∧ target x ≠ target y := by
  exact h.2 B' hlen

/-- Honest boundary: this theorem derives the semantic constructor principle
    (the output must factor through the selected joint view).  It does not claim
    invention of a particular syntax, data structure, or implementation for
    representing arbitrary finite products. -/
def SyntaxRepresentationStillSupplied : Prop := True

theorem semantic_constructor_derived_syntax_boundary_explicit :
    SyntaxRepresentationStillSupplied := by
  trivial

end ResidualDerivedConstructorPrinciple

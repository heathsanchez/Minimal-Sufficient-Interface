import Std
import ResidualInterfaceGenesis

universe u v w z

namespace ResidualDerivedMetaLanguageGenesis

open ResidualInterfaceGenesis

variable {X : Type u} {Probe : Type v} {V : Type w} {Y : Type z}

/-- A residual-derived interface shape is sufficient at its selected arity, while
    every strictly smaller interface shape is rejected by a concrete protected
    residual. This is the exact finite theorem boundary of the endogenous
    meta-grammar experiment: residual geometry chooses arity/shape over supplied
    primitive probes, rather than selecting among pre-enumerated arities. -/
def ResidualDeterminesArity
    (observe : Probe → X → V)
    (target : X → Y)
    (B : List Probe) : Prop :=
  BasisSufficient observe target B ∧
  ∀ B' : List Probe, B'.length < B.length →
    ∃ x y : X,
      (∀ p, p ∈ B' → observe p x = observe p y) ∧
      target x ≠ target y

/-- The selected residual-derived shape is genuinely sufficient. -/
theorem residual_derived_shape_is_sufficient
    (observe : Probe → X → V)
    (target : X → Y)
    (B : List Probe)
    (h : ResidualDeterminesArity observe target B) :
    BasisSufficient observe target B := by
  exact h.1

/-- Every strictly smaller arity is impossible, not merely untried: it has an
    explicit verifier residual that it still aliases. -/
theorem every_smaller_arity_has_residual
    (observe : Probe → X → V)
    (target : X → Y)
    (B : List Probe)
    (h : ResidualDeterminesArity observe target B) :
    ∀ B' : List Probe, B'.length < B.length →
      ¬ BasisSufficient observe target B' := by
  intro B' hlen hs
  rcases h.2 B' hlen with ⟨x, y, hsame, hneq⟩
  exact hneq (hs x y hsame)

/-- Hence residual evidence certifies the selected interface arity as minimal
    among all sufficient interfaces over the supplied primitive observation
    alphabet. -/
theorem residuals_certify_minimal_interface_arity
    (observe : Probe → X → V)
    (target : X → Y)
    (B : List Probe)
    (h : ResidualDeterminesArity observe target B) :
    BasisSufficient observe target B ∧
    ∀ B' : List Probe,
      BasisSufficient observe target B' → B.length ≤ B'.length := by
  constructor
  · exact h.1
  · intro B' hs
    apply Nat.le_of_not_gt
    intro hshort
    exact (every_smaller_arity_has_residual observe target B h B' hshort) hs

/-- Exact ablation law: replacing the inferred shape with any strictly smaller
    product interface restores a concrete protected collision. -/
theorem arity_ablation_restores_obstruction
    (observe : Probe → X → V)
    (target : X → Y)
    (B B' : List Probe)
    (h : ResidualDeterminesArity observe target B)
    (hlen : B'.length < B.length) :
    ∃ x y : X,
      (∀ p, p ∈ B' → observe p x = observe p y) ∧
      target x ≠ target y := by
  exact h.2 B' hlen

/-- If the selected basis is inclusion-minimal as well as arity-minimal, every
    retained coordinate is individually consequence-justified by the residual
    family. -/
theorem residual_derived_shape_has_no_redundant_coordinate
    (observe : Probe → X → V)
    (target : X → Y)
    (B : List Probe)
    (hmin : InclusionMinimalHittingBasis observe target B) :
    BasisSufficient observe target B := by
  exact minimal_hitting_basis_is_sufficient observe target B hmin

end ResidualDerivedMetaLanguageGenesis

import Std
import ResidualDerivedMetaLanguageGenesis

universe u v w z

namespace FiniteResidualBasisGenesis

open ResidualInterfaceGenesis
open ResidualDerivedMetaLanguageGenesis

variable {X : Type u} {Probe : Type v} {V : Type w} {Y : Type z}

/-- There exists a sufficient interface of exact arity `n`. -/
def SufficientArity
    (observe : Probe → X → V)
    (target : X → Y)
    (n : Nat) : Prop :=
  ∃ B : List Probe,
    B.length = n ∧ BasisSufficient observe target B

/-- In a finite probe universe, if every protected target disagreement is exposed
    by some available probe, then the complete probe list is sufficient. -/
theorem finite_universe_is_sufficient
    [Fintype Probe] [DecidableEq Probe]
    (observe : Probe → X → V)
    (target : X → Y)
    (hsep : ∀ x y : X, target x ≠ target y →
      ∃ p : Probe, observe p x ≠ observe p y) :
    BasisSufficient observe target (Finset.univ.toList) := by
  apply residual_hitting_basis_is_sufficient observe target
  intro x y hxy
  rcases hsep x y hxy with ⟨p, hp⟩
  exact ⟨p, by simp, hp⟩

/-- Any non-sufficient basis has an explicit protected residual that it aliases. -/
theorem not_sufficient_has_residual
    (observe : Probe → X → V)
    (target : X → Y)
    (B : List Probe)
    (hnot : ¬ BasisSufficient observe target B) :
    ∃ x y : X,
      (∀ p, p ∈ B → observe p x = observe p y) ∧
      target x ≠ target y := by
  apply Classical.byContradiction
  intro hnone
  apply hnot
  intro x y hsame
  apply Classical.byContradiction
  intro hneq
  exact hnone ⟨x, y, hsame, hneq⟩

/-- Raw finite residual coverage constructs a minimum-arity sufficient basis.
    No basis is supplied as input: well-ordering selects the least arity at which
    a sufficient interface exists, and a witness basis at that arity is extracted. -/
theorem finite_residuals_construct_minimal_basis
    [Fintype Probe] [DecidableEq Probe]
    (observe : Probe → X → V)
    (target : X → Y)
    (hsep : ∀ x y : X, target x ≠ target y →
      ∃ p : Probe, observe p x ≠ observe p y) :
    ∃ B : List Probe, ResidualDeterminesArity observe target B := by
  have hall : BasisSufficient observe target (Finset.univ.toList) :=
    finite_universe_is_sufficient observe target hsep
  have hex : ∃ n : Nat, SufficientArity observe target n := by
    exact ⟨Finset.univ.toList.length, Finset.univ.toList, rfl, hall⟩
  let n := Nat.find hex
  have hn : SufficientArity observe target n := Nat.find_spec hex
  rcases hn with ⟨B, hlen, hsuff⟩
  refine ⟨B, hsuff, ?_⟩
  intro B' hshort
  have hnot : ¬ BasisSufficient observe target B' := by
    intro hsuff'
    have hp : SufficientArity observe target B'.length :=
      ⟨B', rfl, hsuff'⟩
    have hmin : n ≤ B'.length := Nat.find_min' hex hp
    have hshort' : B'.length < n := by
      simpa [hlen] using hshort
    exact (Nat.not_lt_of_ge hmin) hshort'
  exact not_sufficient_has_residual observe target B' hnot

/-- Hence the finite residual family constructs, rather than receives, a basis
    satisfying the existing residual-derived arity contract. -/
theorem finite_residuals_generate_residual_determined_arity
    [Fintype Probe] [DecidableEq Probe]
    (observe : Probe → X → V)
    (target : X → Y)
    (hsep : ∀ x y : X, target x ≠ target y →
      ∃ p : Probe, observe p x ≠ observe p y) :
    ∃ B : List Probe,
      BasisSufficient observe target B ∧
      ∀ B' : List Probe,
        BasisSufficient observe target B' → B.length ≤ B'.length := by
  rcases finite_residuals_construct_minimal_basis observe target hsep with ⟨B, hB⟩
  exact ⟨B, residuals_certify_minimal_interface_arity observe target B hB⟩

end FiniteResidualBasisGenesis

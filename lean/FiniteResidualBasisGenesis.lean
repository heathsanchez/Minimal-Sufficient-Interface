import Std
import ResidualDerivedMetaLanguageGenesis
import VerifiedConsequenceToCompiledSyntax

universe u v w z

namespace FiniteResidualBasisGenesis

open ResidualInterfaceGenesis
open ResidualDerivedMetaLanguageGenesis
open FactorizationSufficiency
open VerifiedConsequenceToCompiledSyntax

variable {X : Type u} {Probe : Type v} {V : Type w} {Y : Type z}

/-- There exists a sufficient interface of exact arity `n`. -/
def SufficientArity
    (observe : Probe → X → V)
    (target : X → Y)
    (n : Nat) : Prop :=
  ∃ B : List Probe,
    B.length = n ∧ BasisSufficient observe target B

/-- A bounded nonempty natural predicate has a least witness.  This Std-only
    helper replaces reliance on a stronger external finite-ordering library. -/
theorem exists_least_up_to
    (P : Nat → Prop)
    (N : Nat)
    (h : ∃ n : Nat, n ≤ N ∧ P n) :
    ∃ n : Nat, n ≤ N ∧ P n ∧ ∀ m : Nat, m < n → ¬ P m := by
  classical
  induction N with
  | zero =>
      rcases h with ⟨n, hn, hp⟩
      have hn0 : n = 0 := Nat.eq_zero_of_le_zero hn
      subst n
      refine ⟨0, Nat.le_refl 0, hp, ?_⟩
      intro m hm
      exact False.elim (Nat.not_lt_zero m hm)
  | succ N ih =>
      by_cases hprev : ∃ n : Nat, n ≤ N ∧ P n
      · rcases ih hprev with ⟨n, hn, hp, hmin⟩
        exact ⟨n, Nat.le_trans hn (Nat.le_succ N), hp, hmin⟩
      · rcases h with ⟨n, hn, hp⟩
        have hnotle : ¬ n ≤ N := by
          intro hle
          exact hprev ⟨n, hle, hp⟩
        have hgt : N < n := Nat.lt_of_not_ge hnotle
        have heq : n = Nat.succ N := Nat.le_antisymm hn hgt
        subst n
        refine ⟨Nat.succ N, Nat.le_refl _, hp, ?_⟩
        intro m hm hPm
        apply hprev
        exact ⟨m, Nat.le_of_lt_succ hm, hPm⟩

/-- In an explicitly enumerated finite probe universe, if every protected target
    disagreement is exposed by some available probe, the complete probe list is sufficient. -/
theorem finite_universe_is_sufficient
    (observe : Probe → X → V)
    (target : X → Y)
    (allProbes : List Probe)
    (hcomplete : ∀ p : Probe, p ∈ allProbes)
    (hsep : ∀ x y : X, target x ≠ target y →
      ∃ p : Probe, observe p x ≠ observe p y) :
    BasisSufficient observe target allProbes := by
  apply residual_hitting_basis_is_sufficient observe target
  intro x y hxy
  rcases hsep x y hxy with ⟨p, hp⟩
  exact ⟨p, hcomplete p, hp⟩

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
    No basis is supplied as input: bounded well-ordering selects the least arity
    at which a sufficient interface exists, and a witness basis is extracted. -/
theorem finite_residuals_construct_minimal_basis
    (observe : Probe → X → V)
    (target : X → Y)
    (allProbes : List Probe)
    (hcomplete : ∀ p : Probe, p ∈ allProbes)
    (hsep : ∀ x y : X, target x ≠ target y →
      ∃ p : Probe, observe p x ≠ observe p y) :
    ∃ B : List Probe, ResidualDeterminesArity observe target B := by
  have hall : BasisSufficient observe target allProbes :=
    finite_universe_is_sufficient observe target allProbes hcomplete hsep
  have hex : ∃ n : Nat, n ≤ allProbes.length ∧ SufficientArity observe target n := by
    exact ⟨allProbes.length, Nat.le_refl _, allProbes, rfl, hall⟩
  rcases exists_least_up_to (SufficientArity observe target) allProbes.length hex with
    ⟨n, hnBound, hn, hmin⟩
  rcases hn with ⟨B, hlen, hsuff⟩
  refine ⟨B, hsuff, ?_⟩
  intro B' hshort
  have hshort' : B'.length < n := by
    simpa [hlen] using hshort
  have hnot : ¬ BasisSufficient observe target B' := by
    intro hsuff'
    exact hmin B'.length hshort' ⟨B', rfl, hsuff'⟩
  exact not_sufficient_has_residual observe target B' hnot

/-- Hence the finite residual family constructs, rather than receives, a basis
    satisfying the existing residual-derived arity contract. -/
theorem finite_residuals_generate_residual_determined_arity
    (observe : Probe → X → V)
    (target : X → Y)
    (allProbes : List Probe)
    (hcomplete : ∀ p : Probe, p ∈ allProbes)
    (hsep : ∀ x y : X, target x ≠ target y →
      ∃ p : Probe, observe p x ≠ observe p y) :
    ∃ B : List Probe,
      BasisSufficient observe target B ∧
      ∀ B' : List Probe,
        BasisSufficient observe target B' → B.length ≤ B'.length := by
  rcases finite_residuals_construct_minimal_basis observe target allProbes hcomplete hsep with ⟨B, hB⟩
  exact ⟨B, residuals_certify_minimal_interface_arity observe target B hB⟩

/-- Finite protected residual coverage therefore generates a reachable executable
    representation through which the protected consequence factors.  The basis is
    existentially constructed from residual coverage; it is not supplied. -/
theorem finite_residuals_generate_factorizing_representation
    (observe : Probe → X → V)
    (target : X → Y)
    (allProbes : List Probe)
    (hcomplete : ∀ p : Probe, p ∈ allProbes)
    (hsep : ∀ x y : X, target x ≠ target y →
      ∃ p : Probe, observe p x ≠ observe p y) :
    ∃ B : List Probe,
      ResidualDeterminesArity observe target B ∧
      FactorsThrough (compiledRepresentation observe B) target := by
  rcases finite_residuals_construct_minimal_basis observe target allProbes hcomplete hsep with ⟨B, hB⟩
  exact ⟨B, hB, residuals_generate_factorizing_representation observe target B hB⟩

/-- End-to-end finite developmental bridge with no basis argument.  A concrete
    verified collapse/disagreement refutes the old representation; global finite
    residual coverage then constructs a minimum sufficient basis and a generated
    reachable representation that restores factorization. -/
theorem verified_failure_to_endogenous_generated_factorization
    {R : Type v}
    (q : X → R)
    (observe : Probe → X → V)
    (target : X → Y)
    (allProbes : List Probe)
    (hcomplete : ∀ p : Probe, p ∈ allProbes)
    {x y : X}
    (hcollapse : q x = q y)
    (hxy : target x ≠ target y)
    (hsep : ∀ a b : X, target a ≠ target b →
      ∃ p : Probe, observe p a ≠ observe p b) :
    (¬ FactorsThrough q target) ∧
      ∃ B : List Probe,
        ResidualDeterminesArity observe target B ∧
        FactorsThrough (compiledRepresentation observe B) target := by
  constructor
  · exact separator_certifies_nonfactorization q target hcollapse hxy
  · exact finite_residuals_generate_factorizing_representation
      observe target allProbes hcomplete hsep

end FiniteResidualBasisGenesis

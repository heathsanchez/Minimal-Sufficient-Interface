import PermutationBlindEvidenceRoleBoundary

universe u

namespace VerifierAsymmetryInducesRoles

open PermutationBlindEvidenceRoleBoundary

/-- A verifier contributes no semantic role labels.  It only answers whether an
    ordered evidence trace is accepted. -/
structure OrderedVerifier (α : Type u) where
  accepts : List α → Bool

/-- The smallest role decoder reads only the verifier verdict.  The names
    `forward` and `reverse` live in the output language, not in the evidence. -/
def roleFromVerdict : Bool → Orientation
  | true => Orientation.forward
  | false => Orientation.reverse

/-- One bit of order-sensitive verifier consequence is sufficient to distinguish
    the two swapped traces. -/
theorem asymmetric_verdict_induces_opposite_roles
    {α : Type u} (V : OrderedVerifier α) (a b : α)
    (hab : V.accepts [a, b] = true)
    (hba : V.accepts [b, a] = false) :
    roleFromVerdict (V.accepts [a, b]) = Orientation.forward ∧
    roleFromVerdict (V.accepts [b, a]) = Orientation.reverse := by
  simp [hab, hba, roleFromVerdict]

/-- The same asymmetric consequence also certifies that the verifier observation
    is not swap invariant. -/
theorem asymmetric_verdict_breaks_swap_symmetry
    {α : Type u} (V : OrderedVerifier α) (a b : α)
    (hab : V.accepts [a, b] = true)
    (hba : V.accepts [b, a] = false) :
    V.accepts [a, b] ≠ V.accepts [b, a] := by
  rw [hab, hba]
  decide

/-- Ablation removes precisely the order-sensitive information while retaining
    the same trace carrier and Boolean verifier codomain. -/
def eraseAsymmetry {α : Type u} (_V : OrderedVerifier α) : OrderedVerifier α where
  accepts := fun _ => false

/-- After asymmetry erasure, the two swapped traces are observationally
    identical. -/
theorem erasing_asymmetry_restores_swap_invariance
    {α : Type u} (V : OrderedVerifier α) (a b : α) :
    (eraseAsymmetry V).accepts [a, b] =
      (eraseAsymmetry V).accepts [b, a] := by
  rfl

/-- Therefore the ablated verifier cannot support any selector assigning
    opposite roles to the swapped traces.  This invokes the previously verified
    information-theoretic obstruction rather than merely observing that our
    particular decoder stops working. -/
theorem erasing_asymmetry_blocks_all_opposite_role_selection
    {α : Type u} (V : OrderedVerifier α) (a b : α) :
    ¬ ∃ choose : Bool → Orientation,
      choose ((eraseAsymmetry V).accepts [a, b]) = Orientation.forward ∧
      choose ((eraseAsymmetry V).accepts [b, a]) = Orientation.reverse := by
  exact swap_invariant_observation_cannot_select_opposite_roles
    (eraseAsymmetry V).accepts a b
    (erasing_asymmetry_restores_swap_invariance V a b)

/-- Necessity-and-sufficiency boundary for this two-trace setting:

    * swap-blind evidence cannot determine opposite roles;
    * a single verifier-visible acceptance asymmetry is sufficient;
    * erasing that asymmetry restores the impossibility result.

    This establishes the minimum *kind* of information required for directed
    role genesis here.  It does not claim that arbitrary role ontologies arise
    without an output vocabulary. -/
theorem one_bit_asymmetry_is_sufficient_and_its_erasure_is_causal
    {α : Type u} (V : OrderedVerifier α) (a b : α)
    (hab : V.accepts [a, b] = true)
    (hba : V.accepts [b, a] = false) :
    (V.accepts [a, b] ≠ V.accepts [b, a]) ∧
    (roleFromVerdict (V.accepts [a, b]) = Orientation.forward ∧
      roleFromVerdict (V.accepts [b, a]) = Orientation.reverse) ∧
    (¬ ∃ choose : Bool → Orientation,
      choose ((eraseAsymmetry V).accepts [a, b]) = Orientation.forward ∧
      choose ((eraseAsymmetry V).accepts [b, a]) = Orientation.reverse) := by
  exact ⟨asymmetric_verdict_breaks_swap_symmetry V a b hab hba,
    asymmetric_verdict_induces_opposite_roles V a b hab hba,
    erasing_asymmetry_blocks_all_opposite_role_selection V a b⟩

#check asymmetric_verdict_induces_opposite_roles
#check asymmetric_verdict_breaks_swap_symmetry
#check erasing_asymmetry_restores_swap_invariance
#check erasing_asymmetry_blocks_all_opposite_role_selection
#check one_bit_asymmetry_is_sufficient_and_its_erasure_is_causal

end VerifierAsymmetryInducesRoles

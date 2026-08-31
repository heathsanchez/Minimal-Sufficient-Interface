universe u v

namespace PermutationBlindEvidenceRoleBoundary

/-- The first genuinely typed distinction beyond bare signature size: which
    argument plays which role. -/
inductive Orientation where
  | forward
  | reverse
  deriving DecidableEq, Repr

/-- Any observation channel that identifies an ordered pair with its swap cannot
    support opposite role assignments for those two evidence traces. -/
theorem swap_invariant_observation_cannot_select_opposite_roles
    {α : Type u} {β : Type v}
    (observe : List α → β) (a b : α)
    (hswap : observe [a, b] = observe [b, a]) :
    ¬ ∃ choose : β → Orientation,
      choose (observe [a, b]) = Orientation.forward ∧
      choose (observe [b, a]) = Orientation.reverse := by
  rintro ⟨choose, hforward, hreverse⟩
  have hsamerole : choose (observe [a, b]) = choose (observe [b, a]) := by
    rw [hswap]
  have hfr : Orientation.forward = Orientation.reverse := by
    calc
      Orientation.forward = choose (observe [a, b]) := hforward.symm
      _ = choose (observe [b, a]) := hsamerole
      _ = Orientation.reverse := hreverse
  cases hfr

/-- Arity is permutation blind: swapping two evidence tokens preserves the
    signature size induced by list length. -/
theorem arity_observation_is_swap_invariant
    {α : Type u} (a b : α) :
    [a, b].length = [b, a].length := by
  rfl

/-- Consequently, arity/signature size alone cannot recover directed roles from
    two traces that differ only by swapping their arguments. -/
theorem arity_alone_cannot_select_orientation
    {α : Type u} (a b : α) :
    ¬ ∃ choose : Nat → Orientation,
      choose [a, b].length = Orientation.forward ∧
      choose [b, a].length = Orientation.reverse := by
  exact swap_invariant_observation_cannot_select_opposite_roles
    (fun xs : List α => xs.length) a b (arity_observation_is_swap_invariant a b)

/-- The obstruction is not list length specifically.  Every permutation-blind
    evidence summary has the same limitation.  Therefore a system that must
    distinguish source/target-like roles needs some additional verifier-visible
    asymmetry beyond cardinality alone. -/
theorem extra_asymmetry_is_necessary_for_opposite_roles
    {α : Type u} {β : Type v}
    (observe : List α → β)
    (hblind : ∀ a b : α, observe [a, b] = observe [b, a]) :
    ∀ a b : α,
      ¬ ∃ choose : β → Orientation,
        choose (observe [a, b]) = Orientation.forward ∧
        choose (observe [b, a]) = Orientation.reverse := by
  intro a b
  exact swap_invariant_observation_cannot_select_opposite_roles
    observe a b (hblind a b)

#check swap_invariant_observation_cannot_select_opposite_roles
#check arity_observation_is_swap_invariant
#check arity_alone_cannot_select_orientation
#check extra_asymmetry_is_necessary_for_opposite_roles

end PermutationBlindEvidenceRoleBoundary

import Std

namespace InfiniteBitOmegaFixedPoint

def bit (n k : Nat) : Bool := n.testBit k

def eqBelow (k x y : Nat) : Prop :=
  ∀ j, j < k → bit x j = bit y j

theorem residual_at_every_finite_stage (k : Nat) :
    eqBelow k 0 (2 ^ k) ∧ bit 0 k ≠ bit (2 ^ k) k := by
  constructor
  · intro j hj
    have hne : k ≠ j := (Nat.ne_of_lt hj).symm
    simp [bit, Nat.testBit_two_pow_of_ne hne]
  · simp [bit]

abbrev Language := Nat → Prop

def agrees (C : Language) (x y : Nat) : Prop :=
  ∀ j, C j → bit x j = bit y j

def verifiedResidual (C : Language) (k : Nat) : Prop :=
  ∃ x y, agrees C x y ∧ bit x k ≠ bit y k

def reachable (C : Language) (k : Nat) : Prop :=
  ∀ j, j < k → C j

def develop (C : Language) : Language :=
  fun k => C k ∨ (reachable C k ∧ verifiedResidual C k)

def finiteLanguage (k : Nat) : Language :=
  fun j => j < k

def omegaLanguage : Language :=
  fun _ => True

theorem finite_verified_residual (k : Nat) :
    verifiedResidual (finiteLanguage k) k := by
  refine ⟨0, 2 ^ k, ?_, (residual_at_every_finite_stage k).2⟩
  intro j hj
  exact (residual_at_every_finite_stage k).1 j hj

/-- If every lower index needed to reach `i` is already in the finite prefix
    below `k`, then `i` cannot lie strictly above `k`. -/
theorem reachable_finite_le {k i : Nat}
    (hreach : reachable (finiteLanguage k) i) : i ≤ k := by
  apply Nat.le_of_not_gt
  intro hki
  have hkk : finiteLanguage k k := hreach k hki
  exact (Nat.lt_irrefl k) hkk

theorem develop_finite_step (k : Nat) :
    develop (finiteLanguage k) = finiteLanguage (k + 1) := by
  funext i
  apply propext
  constructor
  · intro h
    rcases h with hi | ⟨hreach, _⟩
    · exact Nat.lt_succ_of_lt hi
    · exact Nat.lt_succ_iff.mpr (reachable_finite_le hreach)
  · intro hi
    have hik : i ≤ k := Nat.lt_succ_iff.mp hi
    rcases Nat.lt_or_eq_of_le hik with hiklt | hikeq
    · exact Or.inl hiklt
    · subst i
      exact Or.inr ⟨(fun j hj => hj), finite_verified_residual k⟩

theorem no_finite_developmental_fixed_point (k : Nat) :
    develop (finiteLanguage k) ≠ finiteLanguage k := by
  rw [develop_finite_step]
  intro h
  have hk := congrFun h k
  simp [finiteLanguage] at hk

theorem omega_is_limit_of_finite_chain (j : Nat) :
    omegaLanguage j ↔ ∃ k, finiteLanguage k j := by
  constructor
  · intro _
    exact ⟨j + 1, by simp [finiteLanguage]⟩
  · intro _
    trivial

theorem develop_omega_fixed :
    develop omegaLanguage = omegaLanguage := by
  funext k
  apply propext
  simp [develop, omegaLanguage]

theorem canonical_closure_at_omega :
    (∀ k, develop (finiteLanguage k) ≠ finiteLanguage k) ∧
    (∀ j, omegaLanguage j ↔ ∃ k, finiteLanguage k j) ∧
    develop omegaLanguage = omegaLanguage := by
  exact ⟨no_finite_developmental_fixed_point,
    omega_is_limit_of_finite_chain,
    develop_omega_fixed⟩

/-- The actual finite Kleene iteration of the developmental operator,
    starting from the empty retained language. -/
def iterate : Nat → Language
  | 0 => finiteLanguage 0
  | n + 1 => develop (iterate n)

/-- The n-th actual iterate is exactly the prefix retaining bits below n. -/
theorem iterate_eq_finiteLanguage (n : Nat) :
    iterate n = finiteLanguage n := by
  induction n with
  | zero => rfl
  | succ n ih =>
      rw [iterate, ih, develop_finite_step]
      rfl

/-- Pointwise supremum of all finite iterates. -/
def finiteIterateSup : Language :=
  fun j => ∃ n, iterate n j

/-- The supremum of the finite developmental chain is exactly the omega state. -/
theorem finite_iterate_sup_eq_omega :
    finiteIterateSup = omegaLanguage := by
  funext j
  apply propext
  constructor
  · intro _
    trivial
  · intro _
    refine ⟨j + 1, ?_⟩
    rw [iterate_eq_finiteLanguage]
    simp [finiteLanguage]

/-- Fixed-point predicate for the same developmental operator. -/
def IsFixed (C : Language) : Prop :=
  develop C = C

/-- No finite iterate is a fixed point. -/
theorem no_finite_iterate_is_fixed (n : Nat) :
    ¬ IsFixed (iterate n) := by
  rw [IsFixed, iterate_eq_finiteLanguage]
  exact no_finite_developmental_fixed_point n

/-- The supremum of all finite iterates is a fixed point. -/
theorem finite_iterate_sup_is_fixed :
    IsFixed finiteIterateSup := by
  rw [IsFixed, finite_iterate_sup_eq_omega]
  exact develop_omega_fixed

/-- Exact closure-at-omega criterion for this developmental system:
    every finite iterate is non-fixed, their supremum is the omega state,
    and that omega state is fixed by the very same operator. -/
def ClosureOrdinalExactlyOmega : Prop :=
  (∀ n, ¬ IsFixed (iterate n)) ∧
  finiteIterateSup = omegaLanguage ∧
  IsFixed finiteIterateSup

/-- The developmental closure ordinal of this explicit chain/operator is omega. -/
theorem closure_ordinal_exactly_omega : ClosureOrdinalExactlyOmega := by
  exact ⟨no_finite_iterate_is_fixed,
    finite_iterate_sup_eq_omega,
    finite_iterate_sup_is_fixed⟩

end InfiniteBitOmegaFixedPoint

#check InfiniteBitOmegaFixedPoint.finite_verified_residual
#check InfiniteBitOmegaFixedPoint.reachable_finite_le
#check InfiniteBitOmegaFixedPoint.develop_finite_step
#check InfiniteBitOmegaFixedPoint.no_finite_developmental_fixed_point
#check InfiniteBitOmegaFixedPoint.omega_is_limit_of_finite_chain
#check InfiniteBitOmegaFixedPoint.develop_omega_fixed
#check InfiniteBitOmegaFixedPoint.canonical_closure_at_omega
#check InfiniteBitOmegaFixedPoint.iterate_eq_finiteLanguage
#check InfiniteBitOmegaFixedPoint.finite_iterate_sup_eq_omega
#check InfiniteBitOmegaFixedPoint.no_finite_iterate_is_fixed
#check InfiniteBitOmegaFixedPoint.finite_iterate_sup_is_fixed
#check InfiniteBitOmegaFixedPoint.closure_ordinal_exactly_omega

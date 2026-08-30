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

theorem develop_finite_step (k : Nat) :
    develop (finiteLanguage k) = finiteLanguage (k + 1) := by
  funext i
  apply propext
  constructor
  · intro h
    rcases h with hi | ⟨hreach, _⟩
    · omega
    · have hik : i ≤ k := by
        by_contra hnot
        have hki : k < i := Nat.lt_of_not_ge hnot
        have hkk : k < k := hreach k hki
        exact (Nat.lt_irrefl k) hkk
      omega
  · intro hi
    by_cases hik : i < k
    · exact Or.inl hik
    · have hikEq : i = k := by omega
      subst i
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

end InfiniteBitOmegaFixedPoint

#check InfiniteBitOmegaFixedPoint.finite_verified_residual
#check InfiniteBitOmegaFixedPoint.develop_finite_step
#check InfiniteBitOmegaFixedPoint.no_finite_developmental_fixed_point
#check InfiniteBitOmegaFixedPoint.omega_is_limit_of_finite_chain
#check InfiniteBitOmegaFixedPoint.develop_omega_fixed
#check InfiniteBitOmegaFixedPoint.canonical_closure_at_omega

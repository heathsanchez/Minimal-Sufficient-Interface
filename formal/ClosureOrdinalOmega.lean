import Std

/-!
V16 closure-ordinal gate.

This file makes the developmental operator explicit. A developmental state is
an extensional set of retained consequence indices. `stagePrefix k` contains
exactly the consequences with indices below `k`. `develop` retains everything
already present and adds the first missing consequence: an index `k` may be
added exactly when every smaller index is already retained and `k` itself is
not.

Starting from the empty stage, every finite iterate is the next finite prefix.
No finite iterate is fixed. The pointwise union of all finite iterates is the
state retaining every natural-number consequence, and that omega state is a
fixed point. Thus this concrete developmental chain first stabilizes at its
omega limit.
-/

namespace ClosureOrdinalOmega

abbrev State := Nat → Prop

/-- The finite developmental state retaining exactly indices `< k`. -/
def stagePrefix (k : Nat) : State := fun j => j < k

/-- The omega-limit state retaining every consequence index. -/
def omegaState : State := fun _ => True

/-- Add the first missing consequence while retaining all existing ones. -/
def develop (S : State) : State := fun j =>
  S j ∨ ∃ k, (∀ i, i < k → S i) ∧ ¬ S k ∧ j = k

/-- Development sends the k-prefix to the (k+1)-prefix. -/
theorem develop_stagePrefix (k : Nat) :
    develop (stagePrefix k) = stagePrefix (k + 1) := by
  funext j
  apply propext
  constructor
  · intro h
    rcases h with hj | ⟨m, hprev, hmiss, hjm⟩
    · simp only [stagePrefix] at hj ⊢
      omega
    · subst j
      simp only [stagePrefix] at hprev hmiss ⊢
      have hnot : ¬ k < m := by
        intro hkm
        have hkk : k < k := hprev k hkm
        exact (Nat.lt_irrefl k) hkk
      omega
  · intro hj
    simp only [stagePrefix] at hj
    by_cases hold : j < k
    · exact Or.inl hold
    · have hjk : j = k := by omega
      subst j
      apply Or.inr
      refine ⟨k, ?_, ?_, rfl⟩
      · intro i hi
        exact hi
      · exact Nat.lt_irrefl k

/-- Consecutive finite prefixes are genuinely distinct. -/
theorem stagePrefix_strict (k : Nat) :
    stagePrefix k ≠ stagePrefix (k + 1) := by
  intro h
  have hk : stagePrefix k k = stagePrefix (k + 1) k := congrFun h k
  have hiff : stagePrefix k k ↔ stagePrefix (k + 1) k := iff_of_eq hk
  simpa [stagePrefix] using hiff

/-- Finite iteration of the developmental operator from the empty state. -/
def iterate : Nat → State
  | 0 => stagePrefix 0
  | n + 1 => develop (iterate n)

/-- The n-th finite iterate is exactly the n-prefix. -/
theorem iterate_eq_stagePrefix : ∀ n : Nat, iterate n = stagePrefix n
  | 0 => rfl
  | n + 1 => by
      rw [iterate, iterate_eq_stagePrefix n, develop_stagePrefix]

/-- Every finite iterate strictly develops again. -/
theorem no_finite_iterate_is_fixed (n : Nat) :
    develop (iterate n) ≠ iterate n := by
  rw [iterate_eq_stagePrefix, develop_stagePrefix]
  exact stagePrefix_strict n

/-- The omega state is fixed by development. -/
theorem omega_is_fixed : develop omegaState = omegaState := by
  funext j
  apply propext
  simp [develop, omegaState]

/-- Pointwise union of all finite developmental iterates. -/
def omegaUnion : State := fun j => ∃ n, iterate n j

/-- The union of all finite iterates is exactly the omega state. -/
theorem omega_union_eq : omegaUnion = omegaState := by
  funext j
  apply propext
  constructor
  · intro _
    trivial
  · intro _
    refine ⟨j + 1, ?_⟩
    rw [iterate_eq_stagePrefix]
    simp [stagePrefix]

/-- No finite iterate has already reached the omega state. -/
theorem finite_iterate_ne_omega (n : Nat) : iterate n ≠ omegaState := by
  intro h
  rw [iterate_eq_stagePrefix] at h
  have hn : stagePrefix n n = omegaState n := congrFun h n
  have hiff : stagePrefix n n ↔ omegaState n := iff_of_eq hn
  simpa [stagePrefix, omegaState] using hiff

/-- Exact closure-ordinal certificate for this V16 developmental chain:
    every finite stage is non-fixed, their union is the omega state, and the
    omega state is fixed. -/
theorem closure_ordinal_exactly_omega :
    (∀ n : Nat, develop (iterate n) ≠ iterate n) ∧
    omegaUnion = omegaState ∧
    develop omegaState = omegaState := by
  exact ⟨no_finite_iterate_is_fixed, omega_union_eq, omega_is_fixed⟩

end ClosureOrdinalOmega

#check ClosureOrdinalOmega.develop_stagePrefix
#check ClosureOrdinalOmega.iterate_eq_stagePrefix
#check ClosureOrdinalOmega.no_finite_iterate_is_fixed
#check ClosureOrdinalOmega.omega_union_eq
#check ClosureOrdinalOmega.omega_is_fixed
#check ClosureOrdinalOmega.closure_ordinal_exactly_omega

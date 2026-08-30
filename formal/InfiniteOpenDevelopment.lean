import Std

/-!
V16 formal gate: remove the finite-world assumption.

This file isolates the structural claim from the Python implementation.  The
world is `Nat`.  Consequence `c k` asks whether the current state is exactly
`k`.  At finite stage `k` the retained consequences are precisely those with
indices `< k`.

For every finite stage `k`, the two states `k` and `k+1` are observationally
identical under every retained consequence, while the newly reachable
consequence `c k` separates them.  Hence no finite prefix is terminal.

At the omega limit, agreement on every consequence implies actual equality, so
the limiting consequential identity is equality on `Nat`.
-/

namespace InfiniteOpenDevelopment

/-- The k-th Boolean-valued protected consequence, represented propositionally. -/
def consequence (k n : Nat) : Prop := n = k

/-- Consequential identity after retaining every consequence with index < k. -/
def eqBelow (k x y : Nat) : Prop :=
  ∀ j, j < k → (consequence j x ↔ consequence j y)

/-- At every finite developmental stage there is an exact residual witness.
    The pair `(k,k+1)` agrees on all retained consequences but the next
    consequence `k` separates it. -/
theorem residual_at_every_finite_stage (k : Nat) :
    eqBelow k k (k + 1) ∧
      ¬ (consequence k k ↔ consequence k (k + 1)) := by
  constructor
  · intro j hj
    simp only [consequence]
    constructor
    · intro hkj
      omega
    · intro hsuccj
      omega
  · simp [consequence]

/-- The next consequence has not already been retained at stage `k`. -/
theorem next_consequence_is_new (k : Nat) : ¬ k < k := by
  exact Nat.lt_irrefl k

/-- Therefore every finite retained prefix admits a new verified separator. -/
theorem no_finite_prefix_is_terminal (k : Nat) :
    ∃ x y, eqBelow k x y ∧
      ¬ (consequence k x ↔ consequence k y) := by
  exact ⟨k, k + 1, (residual_at_every_finite_stage k).1,
    (residual_at_every_finite_stage k).2⟩

/-- At the omega limit, agreement under all generated consequences is exactly
    equality.  Thus the infinite chain has a well-defined limiting identity. -/
theorem omega_limit_identity (x y : Nat) :
    (∀ j, consequence j x ↔ consequence j y) ↔ x = y := by
  constructor
  · intro h
    have hx := h x
    simp [consequence] at hx
    exact hx.symm
  · intro hxy
    subst y
    intro j
    rfl

/-- Every pair of distinct natural-number states is eventually separated by a
    generated consequence. -/
theorem eventual_separation {x y : Nat} (hxy : x ≠ y) :
    ∃ k, consequence k x ∧ ¬ consequence k y := by
  refine ⟨x, rfl, ?_⟩
  simpa [consequence] using (fun hyx : y = x => hxy hyx.symm)

end InfiniteOpenDevelopment

#check InfiniteOpenDevelopment.residual_at_every_finite_stage
#check InfiniteOpenDevelopment.no_finite_prefix_is_terminal
#check InfiniteOpenDevelopment.omega_limit_identity
#check InfiniteOpenDevelopment.eventual_separation

import Std

/-!
Exact Lean bridge for the Python V16 bit consequence family.

Python V16 defines
  bit(n,k) = (n >> k) & 1
on the infinite domain Nat.

Here the protected consequence is exactly Lean's `Nat.testBit n k`.
The theorem `bit_toNat_eq_python_arithmetic` connects that Bool-valued bit to
`n / 2^k % 2`, the arithmetic form of the Python right-shift-and-mask bit.

At every finite stage k, the pair (0, 2^k) agrees on all retained bits j < k
and differs at bit k. Hence no finite prefix of retained bit consequences is
terminal. At the omega limit, agreement at every bit is equality on Nat.
-/

namespace InfiniteBitOpenDevelopment

/-- Exact Boolean bit consequence corresponding to Python `(n >> k) & 1`. -/
def bit (n k : Nat) : Bool := n.testBit k

/-- Arithmetic bridge to the Python bit computation. -/
theorem bit_toNat_eq_python_arithmetic (n k : Nat) :
    (bit n k).toNat = n / 2 ^ k % 2 := by
  simpa [bit] using Nat.toNat_testBit n k

/-- Consequential identity after retaining bits 0,...,k-1. -/
def eqBelow (k x y : Nat) : Prop :=
  ∀ j, j < k → bit x j = bit y j

/-- Exact Python-V16 witness: at finite stage k, 0 and 2^k agree on every
    retained lower bit, while the newly reachable k-th bit separates them. -/
theorem residual_at_every_finite_stage (k : Nat) :
    eqBelow k 0 (2 ^ k) ∧ bit 0 k ≠ bit (2 ^ k) k := by
  constructor
  · intro j hj
    have hne : k ≠ j := (Nat.ne_of_lt hj).symm
    simp [bit, Nat.testBit_two_pow_of_ne hne]
  · simp [bit]

/-- Therefore no finite prefix of the exact bit language is terminal. -/
theorem no_finite_prefix_is_terminal (k : Nat) :
    ∃ x y, eqBelow k x y ∧ bit x k ≠ bit y k := by
  exact ⟨0, 2 ^ k, (residual_at_every_finite_stage k).1,
    (residual_at_every_finite_stage k).2⟩

/-- At the omega limit, agreement on every exact bit is equality on Nat. -/
theorem omega_limit_identity (x y : Nat) :
    (∀ j, bit x j = bit y j) ↔ x = y := by
  constructor
  · intro h
    exact Nat.eq_of_testBit_eq (fun j => h j)
  · intro hxy
    subst y
    intro j
    rfl

/-- Every distinct pair of naturals is separated by some exact bit. -/
theorem eventual_separation {x y : Nat} (hxy : x ≠ y) :
    ∃ k, bit x k ≠ bit y k := by
  simpa [bit] using Nat.exists_testBit_ne_of_ne hxy

end InfiniteBitOpenDevelopment

#check InfiniteBitOpenDevelopment.bit_toNat_eq_python_arithmetic
#check InfiniteBitOpenDevelopment.residual_at_every_finite_stage
#check InfiniteBitOpenDevelopment.no_finite_prefix_is_terminal
#check InfiniteBitOpenDevelopment.omega_limit_identity
#check InfiniteBitOpenDevelopment.eventual_separation

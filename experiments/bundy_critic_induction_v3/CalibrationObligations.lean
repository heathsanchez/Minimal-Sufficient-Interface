import Std
import FrozenSource

/-! Exact candidate obligations for V3. These are checked mathematical
consequences, not evidence that the generator autonomously discovered them. -/
namespace BundyInductionV3

theorem rev_acc_right (acc xs : List Nat) :
    revAccum acc xs = revPlain xs ++ acc := by
  induction xs generalizing acc with
  | nil => simp [revAccum, revPlain]
  | cons x xs ih =>
    simp only [revAccum, revPlain]
    rw [ih]
    simp [List.append_assoc]

theorem rev_acc_left_false :
    ¬ (∀ acc xs : List Nat, revAccum acc xs = acc ++ revPlain xs) := by
  intro h
  have bad := h [1] [2]
  have impossible : False := by
    have hne : revAccum [1] [2] ≠ [1] ++ revPlain [2] := by decide
    exact hne bad
  exact impossible.elim

theorem rev_plain_eq_acc (xs : List Nat) :
    revPlain xs = revAccum [] xs := by
  rw [rev_acc_right]
  simp

end BundyInductionV3

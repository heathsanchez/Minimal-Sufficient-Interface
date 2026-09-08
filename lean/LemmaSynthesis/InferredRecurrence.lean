import LemmaSynthesis.OpenDevelopment

namespace InferredRecurrence

/- Generic recurrence uniqueness. The selected source is not trusted merely
   because it agrees with finite probes. -/
theorem rec_unique (f : Nat → Nat) (b : Nat) (step : Nat → Nat)
    (h0 : f 0 = b)
    (hs : ∀ n, f (Nat.succ n) = step (f n)) :
    ∀ n, Nat.rec b (fun _ acc => step acc) n = f n := by
  intro n
  induction n with
  | zero =>
      exact h0.symm
  | succ n ih =>
      change step (Nat.rec b (fun _ acc => step acc) n) = f (Nat.succ n)
      rw [ih]
      exact (hs n).symm

def inferredMul (x y : Nat) : Nat :=
  Nat.rec 0 (fun _ acc => OpenDevelopment.generated0 x acc) y

theorem inferredMul_correct (x y : Nat) : inferredMul x y = x * y := by
  exact rec_unique (fun n => x * n) 0
    (fun a => OpenDevelopment.generated0 x a)
    (by simp)
    (by
      intro n
      simpa only [OpenDevelopment.generated0_correct, Nat.mul_succ]
        using (Nat.add_comm (x * n) x))
    y

def inferredPow (x y : Nat) : Nat :=
  Nat.rec 1 (fun _ acc => inferredMul x acc) y

theorem inferredPow_correct (x y : Nat) : inferredPow x y = x ^ y := by
  exact rec_unique (fun n => x ^ n) 1
    (fun a => inferredMul x a)
    (by simp)
    (by
      intro n
      simpa only [inferredMul_correct, Nat.pow_succ]
        using (Nat.mul_comm (x ^ n) x))
    y

/- Reuse the pinned all-Nat obstructions; do not turn probe exhaustion
   into an unrestricted impossibility claim. -/
theorem oldMul_inexpressible (p : OpenDevelopment.Program)
    (hp : p ∈ OpenDevelopment.candidates [.succ, .double]) :
    ¬ ∀ x y, OpenDevelopment.eval p x y = x * y := by
  exact OpenDevelopment.obstruction1 p hp

theorem oldPow_inexpressible (p : OpenDevelopment.Program)
    (hp : p ∈ OpenDevelopment.candidates [.succ, .double, .learned0]) :
    ¬ ∀ x y, OpenDevelopment.eval p x y = x ^ y := by
  exact OpenDevelopment.obstruction2 p hp

end InferredRecurrence

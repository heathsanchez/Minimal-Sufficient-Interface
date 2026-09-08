import LemmaSynthesis.OpenDevelopment

namespace BlindDevelopment
open OpenDevelopment

def recursor (b : Nat → Nat) (s : Nat → Nat → Nat) (x y : Nat) : Nat :=
  Nat.rec (b x) (fun _ a => s x a) y

theorem eval_eq_of_parts (p : Program) (b : Nat → Nat) (s : Nat → Nat → Nat)
    (hb : ∀ x, baseValue p.base x = b x)
    (hs : ∀ x a, stepValue p.step x a = s x a) :
    ∀ x y, eval p x y = recursor b s x y := by
  intro x y
  have hstep : (fun (_ : Nat) (a : Nat) => stepValue p.step x a) = (fun (_ : Nat) (a : Nat) => s x a) := by
    funext n a
    exact hs x a
  unfold eval recursor
  rw [hb x, hstep]

theorem mul_recursor (x y : Nat) :
    recursor (fun _ => 0) (fun x a => x + a) x y = x * y := by
  induction y with
  | zero => rfl
  | succ y ih =>
      change x + recursor (fun _ => 0) (fun x a => x + a) x y = x * Nat.succ y
      rw [ih]
      simp [Nat.mul_succ, Nat.add_comm]

theorem pow_recursor (x y : Nat) :
    recursor (fun _ => 1) (fun x a => x * a) x y = x ^ y := by
  induction y with
  | zero => rfl
  | succ y ih =>
      change x * recursor (fun _ => 1) (fun x a => x * a) x y = x ^ Nat.succ y
      rw [ih]
      simp [Nat.pow_succ, Nat.mul_comm]

theorem acquired_correct (x y : Nat) : eval (⟨.zero, .learned0⟩ : Program) x y = x * y := by
  have hb : ∀ x, baseValue (⟨.zero, .learned0⟩ : Program).base x = 0 := by
    intro x
    rfl
  have hs : ∀ x a, stepValue (⟨.zero, .learned0⟩ : Program).step x a = x + a := by
    intro x a
    exact generated0_correct x a
  exact (eval_eq_of_parts (⟨.zero, .learned0⟩ : Program) (fun _ => 0) (fun x a => x + a) hb hs x y).trans (mul_recursor x y)

theorem transferred_correct (x y : Nat) : eval (⟨.one, .learned1⟩ : Program) x y = x ^ y := by
  have hb : ∀ x, baseValue (⟨.one, .learned1⟩ : Program).base x = 1 := by
    intro x
    rfl
  have hs : ∀ x a, stepValue (⟨.one, .learned1⟩ : Program).step x a = x * a := by
    intro x a
    exact generated1_correct x a
  exact (eval_eq_of_parts (⟨.one, .learned1⟩ : Program) (fun _ => 1) (fun x a => x * a) hb hs x y).trans (pow_recursor x y)

def ablatedSteps : List Step := [.succ, .double, .learned0]

private theorem ablationTable :
    AllFailure (fun x y => x ^ y) (candidates ablatedSteps) := by
  exact ⟨⟨2, 4, by decide⟩, ⟨⟨2, 4, by decide⟩, ⟨⟨2, 4, by decide⟩, ⟨⟨2, 4, by decide⟩, ⟨⟨0, 1, by decide⟩, ⟨⟨2, 4, by decide⟩, ⟨⟨2, 4, by decide⟩, ⟨⟨2, 4, by decide⟩, ⟨⟨2, 4, by decide⟩, True.intro⟩⟩⟩⟩⟩⟩⟩⟩⟩

theorem ablation_obstruction (p : Program) (hp : p ∈ candidates ablatedSteps) :
    ¬ ∀ x y, eval p x y = x ^ y := by
  intro h
  obtain ⟨x, y, hne⟩ := allFailureSound _ _ ablationTable p hp
  exact hne (h x y)

theorem acquired_reachable :
    (⟨.zero, .learned0⟩ : Program) ∈ candidates ablatedSteps := by decide

theorem transferred_reachable :
    (⟨.one, .learned1⟩ : Program) ∈ candidates [.succ, .double, .learned0, .learned1] := by decide

end BlindDevelopment

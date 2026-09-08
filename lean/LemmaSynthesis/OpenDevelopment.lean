import Std

namespace OpenDevelopment

inductive Base where
  | zero | one | input
  deriving DecidableEq, Repr

inductive Step where
  | succ | double | learned0 | learned1 | learned2 | learned3
  deriving DecidableEq, Repr

structure Program where
  base : Base
  step : Step
  deriving DecidableEq, Repr

def baseValue : Base → Nat → Nat
  | .zero, _ => 0
  | .one, _ => 1
  | .input, x => x

def generated0 (x y : Nat) : Nat :=
  Nat.rec x (fun _ acc => Nat.succ acc) y

def generated1 (x y : Nat) : Nat :=
  Nat.rec 0 (fun _ acc => generated0 x acc) y

def generated2 (x y : Nat) : Nat :=
  Nat.rec 1 (fun _ acc => generated1 x acc) y

def generated3 (x y : Nat) : Nat :=
  Nat.rec 1 (fun _ acc => generated2 x acc) y

def stepValue : Step → Nat → Nat → Nat
  | .succ, _, acc => Nat.succ acc
  | .double, _, acc => 2 * acc
  | .learned0, x, acc => generated0 x acc
  | .learned1, x, acc => generated1 x acc
  | .learned2, x, acc => generated2 x acc
  | .learned3, x, acc => generated3 x acc

def eval (p : Program) (x y : Nat) : Nat :=
  Nat.rec (baseValue p.base x) (fun _ acc => stepValue p.step x acc) y

def candidates (steps : List Step) : List Program :=
  steps.flatMap (fun s => [⟨.zero, s⟩, ⟨.one, s⟩, ⟨.input, s⟩])

def tower (x y : Nat) : Nat :=
  Nat.rec 1 (fun _ acc => x ^ acc) y

def AllFailure (f : Nat → Nat → Nat) : List Program → Prop
  | [] => True
  | p :: ps => (∃ x y, eval p x y ≠ f x y) ∧ AllFailure f ps

theorem allFailureSound (f : Nat → Nat → Nat) (ps : List Program) :
    AllFailure f ps →
      ∀ p, p ∈ ps → ∃ x y, eval p x y ≠ f x y := by
  induction ps with
  | nil =>
      intro _ p hp
      cases hp
  | cons a rest ih =>
      intro h p hp
      have ha : ∃ x y, eval a x y ≠ f x y := h.1
      have ht : AllFailure f rest := h.2
      simp only [List.mem_cons] at hp
      rcases hp with rfl | hp
      · exact ha
      · exact ih ht p hp

theorem generated0_correct (x y : Nat) : generated0 x y = x + y := by
  induction y with
  | zero => rfl
  | succ y ih =>
      change Nat.succ (generated0 x y) = x + Nat.succ y
      simpa [ih]

theorem generated1_correct (x y : Nat) : generated1 x y = x * y := by
  induction y with
  | zero => rfl
  | succ y ih =>
      change generated0 x (generated1 x y) = x * Nat.succ y
      rw [generated0_correct, ih]
      simp [Nat.mul_succ, Nat.add_comm]

theorem generated2_correct (x y : Nat) : generated2 x y = x ^ y := by
  induction y with
  | zero => rfl
  | succ y ih =>
      change generated1 x (generated2 x y) = x ^ Nat.succ y
      rw [generated1_correct, ih]
      simp [Nat.pow_succ, Nat.mul_comm]

theorem generated3_correct (x y : Nat) : generated3 x y = tower x y := by
  induction y with
  | zero => rfl
  | succ y ih =>
      change generated2 x (generated3 x y) = tower x (Nat.succ y)
      rw [generated2_correct, ih]
      rfl

def oldSteps1 : List Step := [Step.succ, Step.double]

private theorem obstructionTable1 :
    AllFailure (fun x y => x * y) (candidates oldSteps1) := by
  exact ⟨⟨0, 1, by decide⟩, ⟨⟨0, 0, by decide⟩, ⟨⟨0, 1, by decide⟩, ⟨⟨1, 1, by decide⟩, ⟨⟨0, 0, by decide⟩, ⟨⟨1, 0, by decide⟩, True.intro⟩⟩⟩⟩⟩⟩

theorem obstruction1 (p : Program) (hp : p ∈ candidates oldSteps1) :
    ¬ ∀ x y, eval p x y = (fun x y => x * y) x y := by
  intro h
  obtain ⟨x, y, hne⟩ := allFailureSound _ _ obstructionTable1 p hp
  exact hne (h x y)

def oldSteps2 : List Step := [Step.succ, Step.double, Step.learned0]

private theorem obstructionTable2 :
    AllFailure (fun x y => x ^ y) (candidates oldSteps2) := by
  exact ⟨⟨0, 0, by decide⟩, ⟨⟨0, 1, by decide⟩, ⟨⟨0, 0, by decide⟩, ⟨⟨0, 0, by decide⟩, ⟨⟨0, 1, by decide⟩, ⟨⟨0, 0, by decide⟩, ⟨⟨0, 1, by decide⟩, ⟨⟨0, 0, by decide⟩, ⟨⟨0, 1, by decide⟩, True.intro⟩⟩⟩⟩⟩⟩⟩⟩⟩

theorem obstruction2 (p : Program) (hp : p ∈ candidates oldSteps2) :
    ¬ ∀ x y, eval p x y = (fun x y => x ^ y) x y := by
  intro h
  obtain ⟨x, y, hne⟩ := allFailureSound _ _ obstructionTable2 p hp
  exact hne (h x y)

def oldSteps3 : List Step := [Step.succ, Step.double, Step.learned0, Step.learned1]

private theorem obstructionTable3 :
    AllFailure (fun x y => tower x y) (candidates oldSteps3) := by
  exact ⟨⟨0, 0, by decide⟩, ⟨⟨0, 1, by decide⟩, ⟨⟨0, 0, by decide⟩, ⟨⟨0, 0, by decide⟩, ⟨⟨0, 1, by decide⟩, ⟨⟨0, 0, by decide⟩, ⟨⟨0, 1, by decide⟩, ⟨⟨0, 0, by decide⟩, ⟨⟨0, 1, by decide⟩, ⟨⟨0, 0, by decide⟩, ⟨⟨0, 2, by decide⟩, ⟨⟨0, 0, by decide⟩, True.intro⟩⟩⟩⟩⟩⟩⟩⟩⟩⟩⟩⟩

theorem obstruction3 (p : Program) (hp : p ∈ candidates oldSteps3) :
    ¬ ∀ x y, eval p x y = (fun x y => tower x y) x y := by
  intro h
  obtain ⟨x, y, hne⟩ := allFailureSound _ _ obstructionTable3 p hp
  exact hne (h x y)

theorem generated0_reachable :
    ⟨Base.input, Step.succ⟩ ∈ candidates [.succ, .double] := by decide

theorem generated1_reachable :
    ⟨Base.zero, Step.learned0⟩ ∈ candidates [.succ, .double, .learned0] := by decide

theorem generated2_reachable :
    ⟨Base.one, Step.learned1⟩ ∈ candidates [.succ, .double, .learned0, .learned1] := by decide

theorem generated3_reachable :
    ⟨Base.one, Step.learned2⟩ ∈ candidates [.succ, .double, .learned0, .learned1, .learned2] := by decide

end OpenDevelopment

import Std
import «Kernel»

/-- Three situations for the minimal local-silence counterexample. -/
inductive S where
  | a | b | c
  deriving DecidableEq, Repr

/-- Three protected probes. -/
inductive Q where
  | q0 | q1 | q2
  deriving DecidableEq, Repr

/-- q0 and q1 are silent; q2 distinguishes only c. -/
def outcome : S → Q → Bool
  | S.c, Q.q2 => true
  | _, _ => false

/-- Two bases induce the same observational relation. -/
def SameRelation (B D : List Q) : Prop :=
  ∀ x y, EquivalentOn outcome B x y ↔ EquivalentOn outcome D x y

/-- A locally silent probe can add no distinction at all. -/
theorem q0_is_silent : SameRelation [] [Q.q0] := by
  intro x y
  cases x <;> cases y <;> simp [SameRelation, EquivalentOn, outcome]

/-- Yet the full protected family can still distinguish states. -/
theorem local_silence_not_global_sufficiency :
    ¬ SameRelation [] [Q.q0, Q.q1, Q.q2] := by
  intro h
  have hc := h S.a S.c
  simp [EquivalentOn, outcome] at hc

/-- Even after the first silent probe, another untested probe can refine the interface. -/
theorem silence_then_separator :
    EquivalentOn outcome [Q.q0] S.a S.c ∧
    ¬ EquivalentOn outcome [Q.q0, Q.q2] S.a S.c := by
  constructor <;> simp [EquivalentOn, outcome]

/-- Concrete falsifier for the stronger claim that one silent test certifies completion. -/
theorem one_silent_test_does_not_certify_completion :
    SameRelation [] [Q.q0] ∧
    ¬ SameRelation [] [Q.q0, Q.q1, Q.q2] :=
  ⟨q0_is_silent, local_silence_not_global_sufficiency⟩

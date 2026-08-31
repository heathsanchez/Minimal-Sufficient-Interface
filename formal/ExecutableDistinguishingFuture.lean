import InequivalenceForcesDistinguishingFuture

namespace ExecutableDistinguishingFuture

/-- An executable candidate is identified only by its predictions on future tests. -/
abbrev Behavior (F : Type) := F → Bool

/-- Deterministically scan the available future basis for the first disagreement. -/
def firstDiff {F : Type} (p q : Behavior F) : List F → Option F
  | [] => none
  | f :: fs => if p f = q f then firstDiff p q fs else some f

/-- `firstDiff` never fabricates a question: every returned future came from the basis
    and actually separates the two behaviours. -/
theorem firstDiff_some_sound {F : Type} (p q : Behavior F) :
    ∀ {tests : List F} {f : F},
      firstDiff p q tests = some f →
      f ∈ tests ∧ p f ≠ q f := by
  intro tests
  induction tests with
  | nil =>
      intro f h
      simp [firstDiff] at h
  | cons a as ih =>
      intro f h
      by_cases heq : p a = q a
      · simp [firstDiff, heq] at h
        have hrest := ih h
        exact ⟨by simp [hrest.1], hrest.2⟩
      · simp [firstDiff, heq] at h
        subst f
        exact ⟨by simp, heq⟩

/-- Failure to find a separator is exactly agreement on every supplied future test. -/
theorem firstDiff_none_iff_agree_on_tests {F : Type} (p q : Behavior F) :
    ∀ tests : List F,
      firstDiff p q tests = none ↔
      ∀ f, f ∈ tests → p f = q f := by
  intro tests
  induction tests with
  | nil => simp [firstDiff]
  | cons a as ih =>
      by_cases heq : p a = q a
      · simp [firstDiff, heq, ih]
      · simp [firstDiff, heq]

/-- A future basis is complete when every admissible future occurs in it. -/
def CompleteBasis {F : Type} (tests : List F) : Prop :=
  ∀ f, f ∈ tests

/-- On a complete finite future basis, `none` is not search failure: it certifies
    full behavioural equivalence. -/
theorem firstDiff_none_iff_equivalent {F : Type}
    (tests : List F) (hcomplete : CompleteBasis tests)
    (p q : Behavior F) :
    firstDiff p q tests = none ↔ ∀ f, p f = q f := by
  rw [firstDiff_none_iff_agree_on_tests]
  constructor
  · intro h f
    exact h f (hcomplete f)
  · intro h f _
    exact h f

/-- Bare inequivalence is now enough to make executable search return a separator.
    No `SeparationWitness` and no classical choice are inputs. -/
theorem inequivalence_forces_executable_separator {F : Type}
    (tests : List F) (hcomplete : CompleteBasis tests)
    (p q : Behavior F)
    (hneq : ¬ ∀ f, p f = q f) :
    ∃ f, firstDiff p q tests = some f ∧ p f ≠ q f := by
  cases h : firstDiff p q tests with
  | none =>
      exfalso
      exact hneq ((firstDiff_none_iff_equivalent tests hcomplete p q).1 h)
  | some f =>
      exact ⟨f, h, (firstDiff_some_sound p q h).2⟩

/-- A Boolean verifier outcome on a generated separator keeps exactly one of two
    behaviourally different candidates. -/
theorem verifier_outcome_decides_separator {F : Type}
    (p q truth : Behavior F) (f : F)
    (hsep : p f ≠ q f) :
    ((p f = truth f) ∧ ¬ (q f = truth f)) ∨
    ((q f = truth f) ∧ ¬ (p f = truth f)) := by
  cases hp : p f <;> cases hq : q f <;> cases ht : truth f <;> simp_all

/-- The full executable Cycle-9 step: finite ambiguity itself produces the next
    deciding future, and the external verifier supplies only its truth value. -/
theorem executable_ambiguity_strictly_contracts_binary_version_space {F : Type}
    (tests : List F) (hcomplete : CompleteBasis tests)
    (p q truth : Behavior F)
    (hneq : ¬ ∀ f, p f = q f) :
    ∃ f,
      firstDiff p q tests = some f ∧
      (((p f = truth f) ∧ ¬ (q f = truth f)) ∨
       ((q f = truth f) ∧ ¬ (p f = truth f))) := by
  rcases inequivalence_forces_executable_separator tests hcomplete p q hneq with
    ⟨f, hfind, hsep⟩
  exact ⟨f, hfind, verifier_outcome_decides_separator p q truth f hsep⟩

namespace Witness

inductive Fut where | alpha | beta

def tests : List Fut := [.alpha, .beta]

def left : Behavior Fut
  | .alpha => true
  | .beta => false

def right : Behavior Fut
  | .alpha => false
  | .beta => true

def world : Behavior Fut
  | .alpha => true
  | .beta => false

theorem complete : CompleteBasis tests := by
  intro f
  cases f <;> simp [tests]

theorem inequivalent : ¬ ∀ f, left f = right f := by
  intro h
  have := h .alpha
  simp [left, right] at this

theorem finds_alpha : firstDiff left right tests = some .alpha := by
  rfl

theorem generated_query_keeps_left_and_rejects_right :
    (left .alpha = world .alpha) ∧ ¬ (right .alpha = world .alpha) := by
  decide

end Witness

#check firstDiff
#check firstDiff_some_sound
#check firstDiff_none_iff_agree_on_tests
#check firstDiff_none_iff_equivalent
#check inequivalence_forces_executable_separator
#check verifier_outcome_decides_separator
#check executable_ambiguity_strictly_contracts_binary_version_space
#check Witness.finds_alpha
#check Witness.generated_query_keeps_left_and_rejects_right

end ExecutableDistinguishingFuture

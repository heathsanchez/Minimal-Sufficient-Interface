import DevelopmentAsOperationalJoin

namespace AnonymousInteractionConvergenceKernel

open DevelopmentAsOperationalJoin

/-- Anonymous keys: no semantic role such as identity/composition/coherence is
    attached to these constructors.  They are only a finite witness carrier. -/
inductive Key where
  | k0
  | k1
  | k2
  deriving DecidableEq

abbrev Evidence := Key × Bool
abbrev Memory := Image Evidence

/-- A world exposes only three pieces of interaction structure:
    which calls are initially available, which retained responses enable further
    calls, and the response returned to each call.  The developmental kernel
    below is independent of the particular world. -/
structure InteractionWorld where
  base : Key → Prop
  unlock : Evidence → Key → Prop
  respond : Key → Bool

/-- A call is currently available either primitively or because some retained
    interaction consequence enables it. -/
def Available (W : InteractionWorld) (M : Memory) (q : Key) : Prop :=
  W.base q ∨ ∃ e, M e ∧ W.unlock e q

/-- The residual consists exactly of responses to currently available calls that
    selective memory has not retained yet. -/
def Required (W : InteractionWorld) (M : Memory) : Image Evidence :=
  fun e => ∃ q,
    Available W M q ∧
    ¬ M (q, W.respond q) ∧
    e = (q, W.respond q)

/-- Frozen developmental kernel.  It contains no names for developmental stages
    or repair kinds.  It only joins current selective memory with currently
    obtainable but missing interaction consequences. -/
def step (W : InteractionWorld) (M : Memory) : Memory :=
  develop (Required W) M

/-- Completely empty initial selective memory. -/
def emptyMemory : Memory := fun _ => False

theorem step_preserves (W : InteractionWorld) (M : Memory) :
    ImageLe M (step W M) := by
  simpa [step] using develop_preserves_current (Required W) M

/-- If a call is available and its response is not retained, one application of
    the frozen kernel necessarily retains that response. -/
theorem available_missing_is_added
    (W : InteractionWorld) (M : Memory) (q : Key)
    (hAvailable : Available W M q)
    (hMissing : ¬ M (q, W.respond q)) :
    step W M (q, W.respond q) := by
  change M (q, W.respond q) ∨ Required W M (q, W.respond q)
  exact Or.inr ⟨q, hAvailable, hMissing, rfl⟩

/-- A missing response to a call that is not yet available cannot be smuggled in
    by one generic step.  Later evidence must first make the call available. -/
theorem absent_unavailable_stays_absent
    (W : InteractionWorld) (M : Memory) (q : Key)
    (hMissing : ¬ M (q, W.respond q))
    (hUnavailable : ¬ Available W M q) :
    ¬ step W M (q, W.respond q) := by
  intro h
  change M (q, W.respond q) ∨ Required W M (q, W.respond q) at h
  rcases h with hOld | hReq
  · exact hMissing hOld
  · rcases hReq with ⟨q', hAvail', _, heq⟩
    have hq : q = q' := congrArg Prod.fst heq
    subst q'
    exact hUnavailable hAvail'

/-- If every possible world response is already retained, the coupled
    call/response memory process is at a fixed point. -/
theorem all_responses_retained_is_fixed
    (W : InteractionWorld) (M : Memory)
    (hall : ∀ q, M (q, W.respond q)) :
    step W M = M := by
  apply (develop_fixed_iff_residual_closed (Required W) M).2
  intro e hReq
  rcases hReq with ⟨q, _, hMissing, rfl⟩
  exact (hMissing (hall q)).elim

/-! ### Witness A: serially exposed interaction structure -/

def e0 : Evidence := (Key.k0, true)
def e1 : Evidence := (Key.k1, true)
def e2 : Evidence := (Key.k2, true)

/-- In this world only k0 is initially available.  Retaining its positive
    response enables k1; retaining k1's positive response then enables k2. -/
def serialWorld : InteractionWorld where
  base := fun q => q = Key.k0
  unlock := fun e q =>
    (e = e0 ∧ q = Key.k1) ∨
    (e = e1 ∧ q = Key.k2)
  respond := fun _ => true

def s0 : Memory := emptyMemory
def s1 : Memory := step serialWorld s0
def s2 : Memory := step serialWorld s1
def s3 : Memory := step serialWorld s2

theorem serial_k0_available_s0 : Available serialWorld s0 Key.k0 := by
  exact Or.inl rfl

theorem serial_e0_absent_s0 : ¬ s0 e0 := by
  simp [s0, emptyMemory]

theorem serial_e0_in_s1 : s1 e0 := by
  simpa [s1, e0, serialWorld] using
    available_missing_is_added serialWorld s0 Key.k0
      serial_k0_available_s0 serial_e0_absent_s0

theorem serial_k1_unavailable_s0 : ¬ Available serialWorld s0 Key.k1 := by
  simp [Available, serialWorld, s0, emptyMemory]

theorem serial_e1_absent_s0 : ¬ s0 e1 := by
  simp [s0, emptyMemory]

theorem serial_e1_absent_s1 : ¬ s1 e1 := by
  simpa [s1, e1, serialWorld] using
    absent_unavailable_stays_absent serialWorld s0 Key.k1
      serial_e1_absent_s0 serial_k1_unavailable_s0

theorem serial_k1_available_s1 : Available serialWorld s1 Key.k1 := by
  right
  refine ⟨e0, serial_e0_in_s1, ?_⟩
  exact Or.inl ⟨rfl, rfl⟩

theorem serial_e1_in_s2 : s2 e1 := by
  simpa [s2, e1, serialWorld] using
    available_missing_is_added serialWorld s1 Key.k1
      serial_k1_available_s1 serial_e1_absent_s1

theorem serial_e0_in_s2 : s2 e0 := by
  exact step_preserves serialWorld s1 e0 serial_e0_in_s1

theorem serial_e2_absent_s0 : ¬ s0 e2 := by
  simp [s0, emptyMemory]

theorem serial_k2_unavailable_s0 : ¬ Available serialWorld s0 Key.k2 := by
  simp [Available, serialWorld, s0, emptyMemory]

theorem serial_e2_absent_s1 : ¬ s1 e2 := by
  simpa [s1, e2, serialWorld] using
    absent_unavailable_stays_absent serialWorld s0 Key.k2
      serial_e2_absent_s0 serial_k2_unavailable_s0

theorem serial_k2_unavailable_s1 : ¬ Available serialWorld s1 Key.k2 := by
  intro h
  rcases h with hBase | ⟨e, he, hUnlock⟩
  · simp [serialWorld] at hBase
  · rcases hUnlock with hFirst | hSecond
    · have : Key.k2 = Key.k1 := hFirst.2
      simp at this
    · have heq : e = e1 := hSecond.1
      subst e
      exact serial_e1_absent_s1 he

theorem serial_e2_absent_s2 : ¬ s2 e2 := by
  simpa [s2, e2, serialWorld] using
    absent_unavailable_stays_absent serialWorld s1 Key.k2
      serial_e2_absent_s1 serial_k2_unavailable_s1

theorem serial_k2_available_s2 : Available serialWorld s2 Key.k2 := by
  right
  refine ⟨e1, serial_e1_in_s2, ?_⟩
  exact Or.inr ⟨rfl, rfl⟩

theorem serial_e2_in_s3 : s3 e2 := by
  simpa [s3, e2, serialWorld] using
    available_missing_is_added serialWorld s2 Key.k2
      serial_k2_available_s2 serial_e2_absent_s2

theorem serial_e0_in_s3 : s3 e0 := by
  exact step_preserves serialWorld s2 e0 serial_e0_in_s2

theorem serial_e1_in_s3 : s3 e1 := by
  exact step_preserves serialWorld s2 e1 serial_e1_in_s2

theorem serial_step0_strict : s1 ≠ s0 := by
  intro h
  have : s0 e0 := by simpa [h] using serial_e0_in_s1
  exact serial_e0_absent_s0 this

theorem serial_step1_strict : s2 ≠ s1 := by
  intro h
  have : s1 e1 := by simpa [h] using serial_e1_in_s2
  exact serial_e1_absent_s1 this

theorem serial_step2_strict : s3 ≠ s2 := by
  intro h
  have : s2 e2 := by simpa [h] using serial_e2_in_s3
  exact serial_e2_absent_s2 this

theorem serial_s3_fixed : step serialWorld s3 = s3 := by
  apply all_responses_retained_is_fixed
  intro q
  cases q with
  | k0 => simpa [e0, serialWorld] using serial_e0_in_s3
  | k1 => simpa [e1, serialWorld] using serial_e1_in_s3
  | k2 => simpa [e2, serialWorld] using serial_e2_in_s3

/-! ### Witness B: the same kernel over a different interaction geometry -/

/-- Here the first retained response enables two calls simultaneously rather
    than a serial chain.  Nothing in `step` changes. -/
def branchingWorld : InteractionWorld where
  base := fun q => q = Key.k0
  unlock := fun e q =>
    e = e0 ∧ (q = Key.k1 ∨ q = Key.k2)
  respond := fun _ => true

def b0 : Memory := emptyMemory
def b1 : Memory := step branchingWorld b0
def b2 : Memory := step branchingWorld b1

theorem branch_k0_available_b0 : Available branchingWorld b0 Key.k0 := by
  exact Or.inl rfl

theorem branch_e0_absent_b0 : ¬ b0 e0 := by
  simp [b0, emptyMemory]

theorem branch_e0_in_b1 : b1 e0 := by
  simpa [b1, e0, branchingWorld] using
    available_missing_is_added branchingWorld b0 Key.k0
      branch_k0_available_b0 branch_e0_absent_b0

theorem branch_k1_unavailable_b0 : ¬ Available branchingWorld b0 Key.k1 := by
  simp [Available, branchingWorld, b0, emptyMemory]

theorem branch_k2_unavailable_b0 : ¬ Available branchingWorld b0 Key.k2 := by
  simp [Available, branchingWorld, b0, emptyMemory]

theorem branch_e1_absent_b1 : ¬ b1 e1 := by
  have h0 : ¬ b0 e1 := by simp [b0, emptyMemory]
  simpa [b1, e1, branchingWorld] using
    absent_unavailable_stays_absent branchingWorld b0 Key.k1
      h0 branch_k1_unavailable_b0

theorem branch_e2_absent_b1 : ¬ b1 e2 := by
  have h0 : ¬ b0 e2 := by simp [b0, emptyMemory]
  simpa [b1, e2, branchingWorld] using
    absent_unavailable_stays_absent branchingWorld b0 Key.k2
      h0 branch_k2_unavailable_b0

theorem branch_k1_available_b1 : Available branchingWorld b1 Key.k1 := by
  right
  exact ⟨e0, branch_e0_in_b1, ⟨rfl, Or.inl rfl⟩⟩

theorem branch_k2_available_b1 : Available branchingWorld b1 Key.k2 := by
  right
  exact ⟨e0, branch_e0_in_b1, ⟨rfl, Or.inr rfl⟩⟩

theorem branch_e1_in_b2 : b2 e1 := by
  simpa [b2, e1, branchingWorld] using
    available_missing_is_added branchingWorld b1 Key.k1
      branch_k1_available_b1 branch_e1_absent_b1

theorem branch_e2_in_b2 : b2 e2 := by
  simpa [b2, e2, branchingWorld] using
    available_missing_is_added branchingWorld b1 Key.k2
      branch_k2_available_b1 branch_e2_absent_b1

theorem branch_e0_in_b2 : b2 e0 := by
  exact step_preserves branchingWorld b1 e0 branch_e0_in_b1

theorem branch_step0_strict : b1 ≠ b0 := by
  intro h
  have : b0 e0 := by simpa [h] using branch_e0_in_b1
  exact branch_e0_absent_b0 this

theorem branch_step1_strict : b2 ≠ b1 := by
  intro h
  have : b1 e1 := by simpa [h] using branch_e1_in_b2
  exact branch_e1_absent_b1 this

theorem branch_b2_fixed : step branchingWorld b2 = b2 := by
  apply all_responses_retained_is_fixed
  intro q
  cases q with
  | k0 => simpa [e0, branchingWorld] using branch_e0_in_b2
  | k1 => simpa [e1, branchingWorld] using branch_e1_in_b2
  | k2 => simpa [e2, branchingWorld] using branch_e2_in_b2

/-- Bedrock witness: a single semantic-kind-blind kernel operates on two distinct
    interaction geometries.  In the serial world later calls are literally
    unavailable until earlier consequences are retained, producing three strict
    developmental steps before a fixed point.  In the branching world the same
    kernel converges in two strict steps. -/
theorem same_frozen_kernel_develops_and_converges_across_worlds :
    (¬ Available serialWorld s0 Key.k1) ∧
    (¬ Available serialWorld s1 Key.k2) ∧
    Available serialWorld s1 Key.k1 ∧
    Available serialWorld s2 Key.k2 ∧
    s1 ≠ s0 ∧
    s2 ≠ s1 ∧
    s3 ≠ s2 ∧
    step serialWorld s3 = s3 ∧
    (¬ Available branchingWorld b0 Key.k1) ∧
    (¬ Available branchingWorld b0 Key.k2) ∧
    Available branchingWorld b1 Key.k1 ∧
    Available branchingWorld b1 Key.k2 ∧
    b1 ≠ b0 ∧
    b2 ≠ b1 ∧
    step branchingWorld b2 = b2 := by
  exact ⟨
    serial_k1_unavailable_s0,
    serial_k2_unavailable_s1,
    serial_k1_available_s1,
    serial_k2_available_s2,
    serial_step0_strict,
    serial_step1_strict,
    serial_step2_strict,
    serial_s3_fixed,
    branch_k1_unavailable_b0,
    branch_k2_unavailable_b0,
    branch_k1_available_b1,
    branch_k2_available_b1,
    branch_step0_strict,
    branch_step1_strict,
    branch_b2_fixed⟩

#check step_preserves
#check available_missing_is_added
#check absent_unavailable_stays_absent
#check all_responses_retained_is_fixed
#check serial_step0_strict
#check serial_step1_strict
#check serial_step2_strict
#check serial_s3_fixed
#check branch_step0_strict
#check branch_step1_strict
#check branch_b2_fixed
#check same_frozen_kernel_develops_and_converges_across_worlds

end AnonymousInteractionConvergenceKernel

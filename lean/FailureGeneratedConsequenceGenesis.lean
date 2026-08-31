import Std

namespace FailureGeneratedConsequenceGenesis

/- The raw bedrock contains only states and directed generators. There is no
   supplied family of candidate predicates and no name for the consequence
   that will be retained. -/
abbrev X := Fin 3

inductive G : X → X → Type where
  | e01 : G 0 1
  | e12 : G 1 2

inductive Path : X → X → Type where
  | refl (x : X) : Path x x
  | step {x y z : X} : G x y → Path y z → Path x z

/- Generic observation formation is fixed once: a runtime target induces the
   type of continuations into that target. This is not a candidate probe pool. -/
def consequenceFromTarget (target : X) : X → Type :=
  fun z => Path z target

/- A failure object contains endpoints plus a verifier-produced negative fact.
   It does not contain a predicate/probe identifier. -/
structure VerifiedFailure where
  blocked : X
  target : X
  impossible : ¬ Nonempty (Path blocked target)

/- Consequence genesis: the same frozen rule turns the failure's target into a
   new typed observation. -/
def generateConsequence (r : VerifiedFailure) : X → Type :=
  consequenceFromTarget r.target

def generatedTarget (r : VerifiedFailure) : generateConsequence r r.target :=
  Path.refl r.target

theorem failure_generates_separator (r : VerifiedFailure) :
    (¬ Nonempty (generateConsequence r r.blocked)) ∧
      Nonempty (generateConsequence r r.target) := by
  constructor
  · exact r.impossible
  · exact ⟨generatedTarget r⟩

/- Every generated path is monotone in the concrete directed world. -/
theorem path_monotone {x y : X} (p : Path x y) : x.val ≤ y.val := by
  induction p with
  | refl x => exact Nat.le_refl x.val
  | @step x y z g p ih =>
      cases g with
      | e01 => exact Nat.le_trans (by decide) ih
      | e12 => exact Nat.le_trans (by decide) ih

/- Two independently verified failures with different targets. -/
def fail20 : VerifiedFailure where
  blocked := 2
  target := 0
  impossible := by
    intro h
    exact h.elim (fun p => by
      have hp : (2 : Nat) ≤ 0 := path_monotone p
      omega)

def fail21 : VerifiedFailure where
  blocked := 2
  target := 1
  impossible := by
    intro h
    exact h.elim (fun p => by
      have hp : (2 : Nat) ≤ 1 := path_monotone p
      omega)

/- World sensitivity: the very same frozen generator yields different
   observational behaviour when the verified failure changes. At state 1,
   target-1 reachability is inhabited whereas target-0 reachability is empty.
   No candidate consequence identity is supplied to generateConsequence. -/
theorem same_generator_different_failures_generate_different_behaviour :
    Nonempty (generateConsequence fail21 1) ∧
    (¬ Nonempty (generateConsequence fail20 1)) := by
  change Nonempty (Path 1 1) ∧ ¬ Nonempty (Path 1 0)
  constructor
  · exact ⟨Path.refl 1⟩
  · intro h
    exact h.elim (fun p => by
      have hp : (1 : Nat) ≤ 0 := path_monotone p
      omega)

/- Ablation: endpoints alone, without the verifier's failure certificate, do
   not license a negative conclusion. -/
structure UnverifiedFailure where
  blocked : X
  target : X

def eraseVerification (r : VerifiedFailure) : UnverifiedFailure :=
  ⟨r.blocked, r.target⟩

/- Positive control: an arbitrary unverified pair can be reachable. -/
def path02 : Path 0 2 :=
  Path.step G.e01 (Path.step G.e12 (Path.refl 2))

theorem verification_erasure_does_not_license_universal_nonreachability :
    ¬ (∀ r : UnverifiedFailure, ¬ Nonempty (Path r.blocked r.target)) := by
  intro h
  exact h ⟨0, 2⟩ ⟨path02⟩

/- Capstone: verified failure itself supplies enough information for the frozen
   generic continuation rule to create a separating consequence, while the
   same universal negative inference is unsound after verification is erased. -/
theorem failure_generated_consequence_genesis_certificate :
    ((¬ Nonempty (generateConsequence fail20 fail20.blocked)) ∧
      Nonempty (generateConsequence fail20 fail20.target)) ∧
    (Nonempty (generateConsequence fail21 1) ∧
      ¬ Nonempty (generateConsequence fail20 1)) ∧
    (¬ (∀ r : UnverifiedFailure, ¬ Nonempty (Path r.blocked r.target))) := by
  exact ⟨failure_generates_separator fail20,
    same_generator_different_failures_generate_different_behaviour,
    verification_erasure_does_not_license_universal_nonreachability⟩

#check failure_generates_separator
#check same_generator_different_failures_generate_different_behaviour
#check verification_erasure_does_not_license_universal_nonreachability
#check failure_generated_consequence_genesis_certificate

end FailureGeneratedConsequenceGenesis

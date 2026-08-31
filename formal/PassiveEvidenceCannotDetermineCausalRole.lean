import Std

namespace PassiveEvidenceCannotDetermineCausalRole

/-- Anonymous two-position role vocabulary.  The theorem below does not attach
    source/target semantics to these positions. -/
inductive PairRole where
  | p0
  | p1
  deriving DecidableEq, Repr

/-- The frozen observed trace. -/
def observed : List Bool := [false, true]

/-- Two verifiers agree exactly on the passive observation but disagree on the
    counterfactual deletion behavior that determines causal necessity. -/
def verifierA : List Bool → Bool
  | [false, true] => true
  | [true] => false   -- deleting position 0 destroys acceptance
  | [false] => true
  | _ => false

def verifierB : List Bool → Bool
  | [false, true] => true
  | [true] => true
  | [false] => false  -- deleting position 1 destroys acceptance
  | _ => false

theorem passive_verdicts_are_identical :
    verifierA observed = true ∧ verifierB observed = true := by
  decide

/-- Delete one of the two anonymous positions. -/
def deleteRole : PairRole → List Bool
  | .p0 => [true]
  | .p1 => [false]

/-- A role is causally necessary when deleting that position flips an accepted
    trace to rejection. -/
def Necessary (V : List Bool → Bool) (p : PairRole) : Prop :=
  V (deleteRole p) = false

theorem verifierA_requires_p0 :
    Necessary verifierA .p0 ∧ ¬ Necessary verifierA .p1 := by
  constructor
  · rfl
  · intro h
    change verifierA [false] = false at h
    simp [verifierA] at h

theorem verifierB_requires_p1 :
    Necessary verifierB .p1 ∧ ¬ Necessary verifierB .p0 := by
  constructor
  · rfl
  · intro h
    change verifierB [true] = false at h
    simp [verifierB] at h

/-- Both worlds expose the same entire passive input available to a selector:
    the same trace and the same verifier verdict. -/
structure PassiveView where
  trace : List Bool
  verdict : Bool
  deriving DecidableEq

def passiveA : PassiveView := ⟨observed, verifierA observed⟩
def passiveB : PassiveView := ⟨observed, verifierB observed⟩

theorem passive_views_are_equal : passiveA = passiveB := by
  decide

/-- No deterministic selector that sees only the passive trace and its verdict
    can return the correct causal role in both verifier worlds.  The inputs are
    identical, while the required outputs are opposite. -/
theorem passive_evidence_cannot_determine_causal_role :
    ¬ ∃ choose : PassiveView → PairRole,
      choose passiveA = .p0 ∧ choose passiveB = .p1 := by
  rintro ⟨choose, hA, hB⟩
  have hsame : choose passiveA = choose passiveB := by
    rw [passive_views_are_equal]
  have hbad : PairRole.p0 = PairRole.p1 := hA.symm.trans (hsame.trans hB)
  cases hbad

/-- Once the fixed counterfactual deletion interface is admitted, the two
    worlds become distinguishable directly by verifier consequence. -/
def deletionSignature (V : List Bool → Bool) : Bool × Bool :=
  (V (deleteRole .p0), V (deleteRole .p1))

theorem active_intervention_separates_worlds :
    deletionSignature verifierA ≠ deletionSignature verifierB := by
  decide

/-- In each world the deletion signature identifies exactly one necessary
    anonymous position. -/
def causalRoleFromDeletionSignature : Bool × Bool → Option PairRole
  | (false, true) => some .p0
  | (true, false) => some .p1
  | _ => none

theorem intervention_recovers_opposite_causal_roles :
    causalRoleFromDeletionSignature (deletionSignature verifierA) = some .p0 ∧
    causalRoleFromDeletionSignature (deletionSignature verifierB) = some .p1 := by
  decide

/-- Boundary theorem.

    Passive verifier evidence is information-theoretically insufficient to
    identify causal residual roles: two verifier worlds can be observationally
    identical on all supplied passive evidence yet require opposite repairs.
    A counterfactual intervention that queries consequences under deletion
    separates them and recovers the correct role.

    This does NOT say deletion is the unique or universal intervention grammar.
    It says some counterfactual information beyond the passive observation is
    necessary for causal target identification in this exact finite witness. -/
theorem counterfactual_information_is_necessary_for_causal_selection :
    passiveA = passiveB ∧
    Necessary verifierA .p0 ∧ ¬ Necessary verifierA .p1 ∧
    Necessary verifierB .p1 ∧ ¬ Necessary verifierB .p0 ∧
    (¬ ∃ choose : PassiveView → PairRole,
      choose passiveA = .p0 ∧ choose passiveB = .p1) ∧
    deletionSignature verifierA ≠ deletionSignature verifierB := by
  exact ⟨passive_views_are_equal,
    verifierA_requires_p0.1,
    verifierA_requires_p0.2,
    verifierB_requires_p1.1,
    verifierB_requires_p1.2,
    passive_evidence_cannot_determine_causal_role,
    active_intervention_separates_worlds⟩

#check passive_verdicts_are_identical
#check verifierA_requires_p0
#check verifierB_requires_p1
#check passive_views_are_equal
#check passive_evidence_cannot_determine_causal_role
#check active_intervention_separates_worlds
#check intervention_recovers_opposite_causal_roles
#check counterfactual_information_is_necessary_for_causal_selection

end PassiveEvidenceCannotDetermineCausalRole

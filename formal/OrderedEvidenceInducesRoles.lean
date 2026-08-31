import VerifierEvidenceInducesObligationSignature
import PermutationBlindEvidenceRoleBoundary

universe u v

namespace OrderedEvidenceInducesRoles

open GenericResidualCompletion
open ResidualGeneratesNextObligation
open ConsequenceCompilesVariableArityLanguage
open VerifierEvidenceInducesObligationSignature
open PermutationBlindEvidenceRoleBoundary

/-- A two-token verifier trace carries no source/target tags.  Its only asymmetry
    is the order in which the two realized tokens occur. -/
def orderedPairEvidence
    {S : CapabilityState.{u,v}}
    (left right : RealizedToken S)
    (C : TokenTuple S → Bool)
    (haccept : C [left, right] = true) : CertifiedEvidence S C where
  args := [left, right]
  accepted := haccept

/-- The role vocabulary is not an externally supplied enum.  It is exactly the
    position type induced by the accepted evidence trace. -/
abbrev EvidenceRole
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    (e : CertifiedEvidence S C) := EvidenceSignature e

/-- First and second roles are the two evidence-induced positions. -/
def firstRole
    {S : CapabilityState.{u,v}}
    (left right : RealizedToken S)
    (C : TokenTuple S → Bool)
    (haccept : C [left, right] = true) :
    EvidenceRole (orderedPairEvidence left right C haccept) :=
  ⟨0, by simp [EvidenceRole, EvidenceSignature, orderedPairEvidence]⟩

def secondRole
    {S : CapabilityState.{u,v}}
    (left right : RealizedToken S)
    (C : TokenTuple S → Bool)
    (haccept : C [left, right] = true) :
    EvidenceRole (orderedPairEvidence left right C haccept) :=
  ⟨1, by simp [EvidenceRole, EvidenceSignature, orderedPairEvidence]⟩

/-- Roles are genuinely distinct because the trace has two distinct positions,
    independently of whether the underlying tokens themselves are equal. -/
theorem induced_roles_are_distinct
    {S : CapabilityState.{u,v}}
    (left right : RealizedToken S)
    (C : TokenTuple S → Bool)
    (haccept : C [left, right] = true) :
    firstRole left right C haccept ≠ secondRole left right C haccept := by
  intro h
  have hv := congrArg Fin.val h
  simp [firstRole, secondRole] at hv

/-- Reading the ordered trace at the first induced role returns the first token. -/
theorem first_role_recovers_first_token
    {S : CapabilityState.{u,v}}
    (left right : RealizedToken S)
    (C : TokenTuple S → Bool)
    (haccept : C [left, right] = true) :
    (orderedPairEvidence left right C haccept).args.get
      (firstRole left right C haccept) = left := by
  rfl

/-- Reading the ordered trace at the second induced role returns the second token. -/
theorem second_role_recovers_second_token
    {S : CapabilityState.{u,v}}
    (left right : RealizedToken S)
    (C : TokenTuple S → Bool)
    (haccept : C [left, right] = true) :
    (orderedPairEvidence left right C haccept).args.get
      (secondRole left right C haccept) = right := by
  rfl

/-- Swapping only verifier evidence order swaps which token occupies each role.
    The role-forming mechanism itself is unchanged. -/
theorem swapping_evidence_swaps_role_occupants
    {S : CapabilityState.{u,v}}
    (left right : RealizedToken S)
    (C : TokenTuple S → Bool)
    (hforward : C [left, right] = true)
    (hreverse : C [right, left] = true) :
    (orderedPairEvidence left right C hforward).args.get
      (firstRole left right C hforward) = left ∧
    (orderedPairEvidence right left C hreverse).args.get
      (firstRole right left C hreverse) = right ∧
    (orderedPairEvidence left right C hforward).args.get
      (secondRole left right C hforward) = right ∧
    (orderedPairEvidence right left C hreverse).args.get
      (secondRole right left C hreverse) = left := by
  exact ⟨rfl, rfl, rfl, rfl⟩

/-- Arity alone still cannot choose opposite directed roles for the swapped
    traces.  Thus ordered position is a strict information gain over signature
    size, closing exactly the previously certified permutation-blind boundary. -/
theorem order_is_strictly_more_informative_than_arity
    {α : Type u} (a b : α) :
    (¬ ∃ choose : Nat → Orientation,
      choose [a, b].length = Orientation.forward ∧
      choose [b, a].length = Orientation.reverse) := by
  exact arity_alone_cannot_select_orientation a b

/-- A role obligation is generated from an evidence-induced position, not from a
    supplied source/target constructor. -/
def roleState
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    (e : CertifiedEvidence S C) : CapabilityState where
  Obligation := EvidenceRole e
  Realize := fun _ => Empty

/-- Any evidence-induced role can be returned as a fresh structured residual. -/
def roleResidual
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    (e : CertifiedEvidence S C) (p : EvidenceRole e) :
    VerifiedResidual (roleState e) where
  target := p
  unrealized := by
    intro h
    rcases h with ⟨h⟩
    exact Empty.elim h

/-- The same semantic-kind-blind completion repairs a role whose type was
    induced solely from verifier evidence position. -/
theorem generic_completion_repairs_evidence_induced_role
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    (e : CertifiedEvidence S C) (p : EvidenceRole e) :
    Nonempty
      ((complete (roleState e) (generatedDemand (roleResidual e p))).Realize p) := by
  exact failure_forces_target_realization (roleResidual e p)

/-- End-to-end boundary closure.  Permutation-blind/arity-only evidence cannot
    select opposite roles, while retaining the verifier-visible ordering induces
    two distinct role positions, swaps their occupants under evidence reversal,
    and yields fresh role obligations repairable by the unchanged generic
    completion operator.

    This closes the role-asymmetry obstruction without supplying source/target
    labels.  It still relies on ordered finite traces as the evidence
    meta-grammar, so no unrestricted ontology-invention claim is made. -/
theorem ordered_verifier_evidence_induces_role_structure
    {S : CapabilityState.{u,v}}
    (left right : RealizedToken S)
    (C : TokenTuple S → Bool)
    (hforward : C [left, right] = true)
    (hreverse : C [right, left] = true) :
    firstRole left right C hforward ≠ secondRole left right C hforward ∧
    (orderedPairEvidence right left C hreverse).args.get
      (firstRole right left C hreverse) = right ∧
    Nonempty
      ((complete
        (roleState (orderedPairEvidence left right C hforward))
        (generatedDemand
          (roleResidual
            (orderedPairEvidence left right C hforward)
            (firstRole left right C hforward)))).Realize
        (firstRole left right C hforward)) := by
  refine ⟨induced_roles_are_distinct left right C hforward, rfl, ?_⟩
  exact generic_completion_repairs_evidence_induced_role
    (orderedPairEvidence left right C hforward)
    (firstRole left right C hforward)

#check induced_roles_are_distinct
#check first_role_recovers_first_token
#check second_role_recovers_second_token
#check swapping_evidence_swaps_role_occupants
#check order_is_strictly_more_informative_than_arity
#check roleResidual
#check generic_completion_repairs_evidence_induced_role
#check ordered_verifier_evidence_induces_role_structure

end OrderedEvidenceInducesRoles

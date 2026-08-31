import OrderedEvidenceInducesRoles
import ConsequenceDeterminesSelection

universe u v

namespace ConsequenceSelectsEvidenceInducedRole

open GenericResidualCompletion
open ConsequenceDeterminesSelection
open ConsequenceCompilesVariableArityLanguage
open VerifierEvidenceInducesObligationSignature
open OrderedEvidenceInducesRoles

/-- A verifier consequence is evaluated only on the role type already induced
    from evidence positions.  It does not carry a distinguished role name. -/
def UniqueRoleConsequence
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    (e : CertifiedEvidence S C)
    (q : EvidenceRole e → Bool) : Prop :=
  ∃! p : EvidenceRole e, q p = true

/-- The target role is extracted from the unique verifier consequence rather
    than supplied as an argument to the residual constructor. -/
noncomputable def selectedRole
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    {e : CertifiedEvidence S C}
    (q : EvidenceRole e → Bool)
    (h : UniqueRoleConsequence e q) : EvidenceRole e :=
  Classical.choose h

 theorem selected_role_satisfies_consequence
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    {e : CertifiedEvidence S C}
    (q : EvidenceRole e → Bool)
    (h : UniqueRoleConsequence e q) :
    q (selectedRole q h) = true := by
  exact (Classical.choose_spec h).1

 theorem selected_role_is_unique
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    {e : CertifiedEvidence S C}
    (q : EvidenceRole e → Bool)
    (h : UniqueRoleConsequence e q)
    (p : EvidenceRole e)
    (hp : q p = true) :
    p = selectedRole q h := by
  exact (Classical.choose_spec h).2 p hp

/-- The residual target is now entirely consequence-selected inside the
    evidence-induced role ontology. -/
noncomputable def residualFromRoleConsequence
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    (e : CertifiedEvidence S C)
    (q : EvidenceRole e → Bool)
    (h : UniqueRoleConsequence e q) :
    VerifiedResidual (roleState e) :=
  roleResidual e (selectedRole q h)

/-- The semantic-kind-blind completion repairs the consequence-selected role. -/
theorem generic_completion_repairs_consequence_selected_role
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    (e : CertifiedEvidence S C)
    (q : EvidenceRole e → Bool)
    (h : UniqueRoleConsequence e q) :
    Nonempty
      ((complete (roleState e)
        (generatedDemand (residualFromRoleConsequence e q h))).Realize
        (selectedRole q h)) := by
  exact failure_forces_target_realization (residualFromRoleConsequence e q h)

/-- Erasing consequence destroys the possibility of a uniquely selected role;
    therefore this target-selection channel cannot operate after ablation. -/
theorem erased_consequence_has_no_unique_role
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    (e : CertifiedEvidence S C) :
    ¬ UniqueRoleConsequence e (fun _ => false) := by
  rintro ⟨p, hp, _⟩
  simp at hp

/-- On a concrete accepted two-token trace, the evidence itself supplies the
    role ontology, while a verifier consequence uniquely singles out one of
    those anonymous positions.  No `source`, `target`, `first`, or `second`
    constructor is carried into the generic completion state. -/
theorem consequence_selects_target_inside_evidence_induced_ontology
    {S : CapabilityState.{u,v}}
    (left right : RealizedToken S)
    (C : TokenTuple S → Bool)
    (haccept : C [left, right] = true)
    (q : EvidenceRole (orderedPairEvidence left right C haccept) → Bool)
    (huniq : UniqueRoleConsequence
      (orderedPairEvidence left right C haccept) q) :
    q (selectedRole q huniq) = true ∧
    Nonempty
      ((complete
        (roleState (orderedPairEvidence left right C haccept))
        (generatedDemand
          (residualFromRoleConsequence
            (orderedPairEvidence left right C haccept) q huniq))).Realize
        (selectedRole q huniq)) := by
  exact ⟨selected_role_satisfies_consequence q huniq,
    generic_completion_repairs_consequence_selected_role
      (orderedPairEvidence left right C haccept) q huniq⟩

/-- End-to-end target-selection theorem: evidence induces the candidate role
    type, consequence selects a unique anonymous member of that type, the
    selected member becomes a certified unrealized residual, and the unchanged
    free completion realizes exactly that target.  If consequence is erased,
    no target can be uniquely selected.

    Remaining scaffold: the finite ordered-trace meta-grammar and the role
    consequence predicate are still supplied. -/
theorem verifier_consequence_selects_evidence_induced_residual
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    (e : CertifiedEvidence S C)
    (q : EvidenceRole e → Bool)
    (huniq : UniqueRoleConsequence e q) :
    q (selectedRole q huniq) = true ∧
    Nonempty
      ((complete (roleState e)
        (generatedDemand (residualFromRoleConsequence e q huniq))).Realize
        (selectedRole q huniq)) ∧
    (¬ UniqueRoleConsequence e (fun _ => false)) := by
  exact ⟨selected_role_satisfies_consequence q huniq,
    generic_completion_repairs_consequence_selected_role e q huniq,
    erased_consequence_has_no_unique_role e⟩

#check selected_role_satisfies_consequence
#check selected_role_is_unique
#check residualFromRoleConsequence
#check generic_completion_repairs_consequence_selected_role
#check erased_consequence_has_no_unique_role
#check consequence_selects_target_inside_evidence_induced_ontology
#check verifier_consequence_selects_evidence_induced_residual

end ConsequenceSelectsEvidenceInducedRole

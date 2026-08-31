import OrderedEvidenceInducesRoles

universe u v

namespace VerifierDeletionSelectsEvidenceRole

open GenericResidualCompletion
open ConsequenceCompilesVariableArityLanguage
open VerifierEvidenceInducesObligationSignature
open OrderedEvidenceInducesRoles

/-- Canonical leave-one-position-out intervention on an evidence trace.  No
    distinguished role label is supplied: the position itself determines which
    token is removed. -/
def deleteAt {α : Type u} (xs : List α) (p : Fin xs.length) : List α :=
  xs.take p.val ++ xs.drop (p.val + 1)

/-- A position is causally necessary for an accepted verifier trace when deleting
    exactly that evidence position flips the verifier to rejection. -/
def CausallyNecessary
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    (e : CertifiedEvidence S C) (p : EvidenceRole e) : Prop :=
  C (deleteAt e.args p) = false

/-- The verifier trace has a unique causally necessary role.  This is a property
    of the original verifier and its accepted evidence, not a separately supplied
    target predicate. -/
def UniqueCausalRole
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    (e : CertifiedEvidence S C) : Prop :=
  ∃! p : EvidenceRole e, CausallyNecessary e p

/-- When deletion causality identifies exactly one evidence position, the target
    role is extracted from that certificate. -/
noncomputable def selectedCausalRole
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    {e : CertifiedEvidence S C} (h : UniqueCausalRole e) : EvidenceRole e :=
  Classical.choose h

 theorem selected_role_is_causally_necessary
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    {e : CertifiedEvidence S C} (h : UniqueCausalRole e) :
    CausallyNecessary e (selectedCausalRole h) := by
  exact (Classical.choose_spec h).1

 theorem causal_role_is_unique
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    {e : CertifiedEvidence S C} (h : UniqueCausalRole e)
    (p : EvidenceRole e) (hp : CausallyNecessary e p) :
    p = selectedCausalRole h := by
  exact (Classical.choose_spec h).2 p hp

/-- The residual target is generated directly from verifier deletion causality. -/
noncomputable def residualFromDeletionCausality
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    (e : CertifiedEvidence S C) (h : UniqueCausalRole e) :
    VerifiedResidual (roleState e) :=
  roleResidual e (selectedCausalRole h)

/-- The same semantic-kind-blind free completion realizes the causally selected
    role; it is not told anything about evidence, deletion, or roles. -/
theorem generic_completion_repairs_causally_selected_role
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    (e : CertifiedEvidence S C) (h : UniqueCausalRole e) :
    Nonempty
      ((complete (roleState e)
        (generatedDemand (residualFromDeletionCausality e h))).Realize
        (selectedCausalRole h)) := by
  exact failure_forces_target_realization (residualFromDeletionCausality e h)

/-- An intervention-insensitive verifier accepts every perturbed trace. -/
def insensitiveVerifier {S : CapabilityState.{u,v}} : TokenTuple S → Bool :=
  fun _ => true

/-- If verifier response to deletion is erased, no evidence position is causally
    necessary, so the target-selection mechanism has no residual to emit. -/
theorem insensitive_verifier_has_no_unique_causal_role
    {S : CapabilityState.{u,v}}
    (args : TokenTuple S) :
    ¬ ∃! p : Fin args.length,
      insensitiveVerifier (S := S) (deleteAt args p) = false := by
  rintro ⟨p, hp, _⟩
  simp [insensitiveVerifier] at hp

/-- Concrete two-token witness: if the verifier accepts the pair, rejects after
    deleting the first position, and still accepts after deleting the second,
    then the first anonymous evidence position is uniquely causally necessary. -/
theorem first_position_is_selected_from_verifier_behavior
    {S : CapabilityState.{u,v}}
    (left right : RealizedToken S)
    (C : TokenTuple S → Bool)
    (hpair : C [left, right] = true)
    (hdeleteFirst : C [right] = false)
    (hdeleteSecond : C [left] = true) :
    UniqueCausalRole (orderedPairEvidence left right C hpair) := by
  refine ⟨firstRole left right C hpair, ?_, ?_⟩
  · simpa [CausallyNecessary, orderedPairEvidence, deleteAt, firstRole]
      using hdeleteFirst
  · intro p hp
    apply Fin.ext
    have hp0or1 : p.val = 0 ∨ p.val = 1 := by
      omega
    rcases hp0or1 with hp0 | hp1
    · exact hp0
    · exfalso
      have hrejected : C [left] = false := by
        simpa [CausallyNecessary, orderedPairEvidence, deleteAt, hp1] using hp
      rw [hdeleteSecond] at hrejected
      contradiction

/-- End-to-end causal residual genesis.  The accepted verifier trace induces its
    anonymous role type; a fixed leave-one-out intervention derives which role is
    necessary from verifier behavior; that role becomes the residual target; and
    the unchanged generic completion repairs it.  Making the verifier insensitive
    to the intervention removes the target-selection signal.

    Remaining scaffold: finite ordered-list evidence and the delete-one
    intervention operator are still part of the meta-grammar. -/
theorem verifier_deletion_causality_selects_evidence_induced_residual
    {S : CapabilityState.{u,v}}
    (left right : RealizedToken S)
    (C : TokenTuple S → Bool)
    (hpair : C [left, right] = true)
    (hdeleteFirst : C [right] = false)
    (hdeleteSecond : C [left] = true) :
    ∃ h : UniqueCausalRole (orderedPairEvidence left right C hpair),
      CausallyNecessary
        (orderedPairEvidence left right C hpair)
        (selectedCausalRole h) ∧
      Nonempty
        ((complete
          (roleState (orderedPairEvidence left right C hpair))
          (generatedDemand
            (residualFromDeletionCausality
              (orderedPairEvidence left right C hpair) h))).Realize
          (selectedCausalRole h)) := by
  let h := first_position_is_selected_from_verifier_behavior
    left right C hpair hdeleteFirst hdeleteSecond
  exact ⟨h,
    selected_role_is_causally_necessary h,
    generic_completion_repairs_causally_selected_role
      (orderedPairEvidence left right C hpair) h⟩

#check deleteAt
#check selected_role_is_causally_necessary
#check causal_role_is_unique
#check residualFromDeletionCausality
#check generic_completion_repairs_causally_selected_role
#check insensitive_verifier_has_no_unique_causal_role
#check first_position_is_selected_from_verifier_behavior
#check verifier_deletion_causality_selects_evidence_induced_residual

end VerifierDeletionSelectsEvidenceRole

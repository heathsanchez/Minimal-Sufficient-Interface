import ConsequenceCompilesVariableArityLanguage

universe u v

namespace VerifierEvidenceInducesObligationSignature

open GenericResidualCompletion
open ResidualGeneratesNextObligation
open ConsequenceCompilesVariableArityLanguage

/-- A certified verifier datum is not tagged with an arity.  It is the actual
    finite evidence trace together with the verifier's acceptance certificate. -/
structure CertifiedEvidence
    (S : CapabilityState.{u,v}) (C : TokenTuple S → Bool) where
  args : TokenTuple S
  accepted : C args = true

/-- The obligation signature is induced by the shape of the certified evidence
    itself.  No natural-number arity is supplied to this definition. -/
def EvidenceSignature
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    (e : CertifiedEvidence S C) : Type :=
  Fin e.args.length

/-- The evidence itself is the generated obligation. -/
abbrev EvidenceObligation
    (S : CapabilityState.{u,v}) (C : TokenTuple S → Bool) :=
  CertifiedEvidence S C

/-- Fresh evidence-generated obligations begin unrealized. -/
def generatedState
    (S : CapabilityState.{u,v}) (C : TokenTuple S → Bool) : CapabilityState where
  Obligation := EvidenceObligation S C
  Realize := fun _ => Empty

/-- Every accepted raw evidence trace becomes an obligation without first
    choosing an arity or a generator from a pool. -/
def obligationFromEvidence
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    (e : CertifiedEvidence S C) :
    (generatedState S C).Obligation := e

/-- A newly induced evidence obligation is a verifier-certified residual. -/
def residualFromEvidence
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    (e : CertifiedEvidence S C) :
    VerifiedResidual (generatedState S C) where
  target := obligationFromEvidence e
  unrealized := by
    intro h
    rcases h with ⟨h⟩
    exact Empty.elim h

/-- The unchanged semantic-kind-blind completion repairs the obligation whose
    signature was induced by evidence shape. -/
theorem same_generic_operator_repairs_evidence_induced_residual
    {S : CapabilityState.{u,v}} {C : TokenTuple S → Bool}
    (e : CertifiedEvidence S C) :
    Nonempty
      ((complete (generatedState S C)
        (generatedDemand (residualFromEvidence e))).Realize
        (residualFromEvidence e).target) := by
  exact failure_forces_target_realization (residualFromEvidence e)

/-- An erased verifier cannot certify any evidence trace, so no obligation
    signature can be induced through this channel. -/
theorem erased_verifier_certifies_no_evidence
    {S : CapabilityState.{u,v}} :
    ¬ Nonempty (CertifiedEvidence S (erasedConsequence (S := S))) := by
  intro h
  rcases h with ⟨e⟩
  have hacc := e.accepted
  simp [erasedConsequence] at hacc

/-- Before lower repair there is no certified evidence trace containing a
    realized token for the missing target, because that token cannot exist. -/
theorem target_bearing_evidence_unavailable_before_repair
    {S : CapabilityState.{u,v}} (r : VerifiedResidual S)
    (C : TokenTuple S → Bool) :
    ¬ ∃ e : CertifiedEvidence S C,
      ∃ t ∈ e.args, t.obligation = r.target := by
  rintro ⟨e, t, ht, htarget⟩
  exact target_token_unavailable_before_repair r ⟨t, htarget⟩

/-- After lower repair, any verifier that accepts a trace containing the newly
    realized target can certify that exact trace.  The signature is then induced
    from that trace rather than selected independently. -/
def certifiedPostRepairEvidence
    {S : CapabilityState.{u,v}} (r : VerifiedResidual S)
    (context : TokenTuple (complete S (generatedDemand r)))
    (C : TokenTuple (complete S (generatedDemand r)) → Bool)
    (haccept : C (generatedTargetToken r :: context) = true) :
    CertifiedEvidence (complete S (generatedDemand r)) C where
  args := generatedTargetToken r :: context
  accepted := haccept

/-- The signature induced by post-repair evidence is definitionally indexed by
    the evidence length: one position for the generated target plus exactly the
    positions present in the verifier context.  There is no arity selector. -/
theorem post_repair_signature_shape
    {S : CapabilityState.{u,v}} (r : VerifiedResidual S)
    (context : TokenTuple (complete S (generatedDemand r)))
    (C : TokenTuple (complete S (generatedDemand r)) → Bool)
    (haccept : C (generatedTargetToken r :: context) = true) :
    EvidenceSignature (certifiedPostRepairEvidence r context C haccept) =
      Fin (context.length + 1) := by
  simp [EvidenceSignature, certifiedPostRepairEvidence, Nat.add_comm]

/-- End-to-end deciding theorem: a lower residual makes a previously impossible
    target-bearing evidence trace constructible; the verifier certifies the raw
    trace; the trace itself induces the next obligation signature; that fresh
    obligation is repaired by the same generic completion; and verifier erasure
    eliminates the entire evidence-induced obligation channel.

    This removes the explicit arity parameter from obligation formation.  The
    finite-list evidence meta-grammar remains supplied, so this is not a claim of
    unrestricted ontology invention. -/
theorem verifier_evidence_induces_next_obligation_signature
    {S : CapabilityState.{u,v}} (r : VerifiedResidual S)
    (context : TokenTuple (complete S (generatedDemand r)))
    (C : TokenTuple (complete S (generatedDemand r)) → Bool)
    (haccept : C (generatedTargetToken r :: context) = true) :
    (¬ ∃ e : CertifiedEvidence S (fun _ => true),
      ∃ t ∈ e.args, t.obligation = r.target) ∧
    Nonempty
      ((complete
        (generatedState (complete S (generatedDemand r)) C)
        (generatedDemand
          (residualFromEvidence
            (certifiedPostRepairEvidence r context C haccept)))).Realize
        (residualFromEvidence
          (certifiedPostRepairEvidence r context C haccept)).target) ∧
    (EvidenceSignature (certifiedPostRepairEvidence r context C haccept) =
      Fin (context.length + 1)) ∧
    (¬ Nonempty
      (CertifiedEvidence (complete S (generatedDemand r))
        (erasedConsequence (S := complete S (generatedDemand r))))) := by
  refine ⟨target_bearing_evidence_unavailable_before_repair r (fun _ => true), ?_, ?_, ?_⟩
  · exact same_generic_operator_repairs_evidence_induced_residual
      (certifiedPostRepairEvidence r context C haccept)
  · exact post_repair_signature_shape r context C haccept
  · exact erased_verifier_certifies_no_evidence

#check EvidenceSignature
#check residualFromEvidence
#check erased_verifier_certifies_no_evidence
#check target_bearing_evidence_unavailable_before_repair
#check post_repair_signature_shape
#check verifier_evidence_induces_next_obligation_signature

end VerifierEvidenceInducesObligationSignature

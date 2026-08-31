import GenericResidualCompletion
import VerifierInducesCarrierFreeContextQuotient

namespace VerifierInducedOntologyFeedsGenericCompletion

open GenericResidualCompletion
open VerifierInducesCarrierFreeContextQuotient

/-- Current realizability is determined only by verifier consequence on the
    induced context-role quotient. Accepted roles already have a witness;
    rejected roles do not. -/
def ExistingRealize {X : Type u} (V : X → Bool) (observed : X)
    (r : ContextRole V observed) : Type :=
  match roleVerdict V observed r with
  | true => Unit
  | false => Empty

/-- The capability state's obligation ontology is itself verifier-induced. -/
def inducedCapabilityState {X : Type u} (V : X → Bool) (observed : X) :
    CapabilityState where
  Obligation := ContextRole V observed
  Realize := ExistingRealize V observed

/-- A rejected counterfactual context canonically determines a structured
    residual target: its verifier-induced equivalence class. No semantic role
    tag or repair kind is supplied. -/
def residualOfRejectedContext {X : Type u}
    (V : X → Bool) (observed : X) (f : Intervention X)
    (hfail : V (f observed) = false) :
    VerifiedResidual (inducedCapabilityState V observed) where
  target := roleOf V observed f
  unrealized := by
    intro h
    rcases h with ⟨w⟩
    have hv : roleVerdict V observed (roleOf V observed f) = false := by
      simpa [hfail] using quotient_recovers_verifier_consequence V observed f
    change ExistingRealize V observed (roleOf V observed f) at w
    simp [ExistingRealize, hv] at w
    exact nomatch w

/-- The residual target is literally the quotient class induced by the failing
    verifier consequence. -/
theorem target_is_verifier_induced_role {X : Type u}
    (V : X → Bool) (observed : X) (f : Intervention X)
    (hfail : V (f observed) = false) :
    (residualOfRejectedContext V observed f hfail).target =
      roleOf V observed f := by
  rfl

/-- The same generic free-completion operator now repairs an obligation whose
    ontology and target were both induced by verifier consequence. -/
theorem rejected_context_forces_least_generic_completion {X : Type u}
    (V : X → Bool) (observed : X) (f : Intervention X)
    (hfail : V (f observed) = false) :
    let r := residualOfRejectedContext V observed f hfail
    (¬ Nonempty ((inducedCapabilityState V observed).Realize r.target)) ∧
    Nonempty
      ((complete (inducedCapabilityState V observed) (generatedDemand r)).Realize
        r.target) ∧
    (¬ Nonempty
      ((complete (inducedCapabilityState V observed)
        (erasedDemand (inducedCapabilityState V observed))).Realize r.target)) := by
  intro r
  exact verified_failure_generates_least_required_structure r

/-- Distinct verifier effects necessarily produce distinct generated residual
    targets. This is target selection by consequence rather than by a supplied
    target label. -/
theorem distinct_verifier_effects_induce_distinct_targets {X : Type u}
    (V : X → Bool) (observed : X) (f g : Intervention X)
    (hf : V (f observed) = false)
    (hg : V (g observed) = true) :
    (residualOfRejectedContext V observed f hf).target ≠ roleOf V observed g := by
  intro h
  have heq := (role_eq_iff_verifier_indistinguishable V observed f g).1 h
  rw [hf, hg] at heq
  contradiction

/-- Concrete end-to-end witness. The carrier-free `flip` context is rejected by
    the raw verifier, its quotient class becomes the residual target, and the
    generic completion freely realizes exactly that target. -/
theorem verifier_consequence_to_ontology_to_least_repair :
    let V := witnessVerifier
    let x := witnessObserved
    let f := VerifierInducesCarrierFreeContextQuotient.flip
    let r := residualOfRejectedContext V x f (by decide)
    r.target = roleOf V x f ∧
    (¬ Nonempty ((inducedCapabilityState V x).Realize r.target)) ∧
    Nonempty
      ((complete (inducedCapabilityState V x) (generatedDemand r)).Realize
        r.target) ∧
    (¬ Nonempty
      ((complete (inducedCapabilityState V x)
        (erasedDemand (inducedCapabilityState V x))).Realize r.target)) := by
  dsimp
  let f := VerifierInducesCarrierFreeContextQuotient.flip
  let r := residualOfRejectedContext witnessVerifier witnessObserved f (by decide)
  have hcore := rejected_context_forces_least_generic_completion
    witnessVerifier witnessObserved f (by decide)
  exact ⟨rfl, hcore.1, hcore.2.1, hcore.2.2⟩

#check target_is_verifier_induced_role
#check rejected_context_forces_least_generic_completion
#check distinct_verifier_effects_induce_distinct_targets
#check verifier_consequence_to_ontology_to_least_repair

end VerifierInducedOntologyFeedsGenericCompletion

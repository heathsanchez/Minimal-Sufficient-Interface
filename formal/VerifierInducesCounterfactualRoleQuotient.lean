import Std

namespace VerifierInducesCounterfactualRoleQuotient

/-- The evidence carrier remains a finite list in this experiment. -/
abbrev Evidence (α : Type u) := List α

/-- No finite intervention menu is supplied: every endomorphism of the evidence
    carrier is an admissible counterfactual context. -/
abbrev Intervention (α : Type u) := Evidence α → Evidence α

/-- Two counterfactual contexts have the same causal role exactly when the
    verifier cannot distinguish their consequences on the observed evidence. -/
def EffectEquivalent (V : Evidence α → Bool) (observed : Evidence α)
    (f g : Intervention α) : Prop :=
  V (f observed) = V (g observed)

def effectSetoid (V : Evidence α → Bool) (observed : Evidence α) :
    Setoid (Intervention α) where
  r := EffectEquivalent V observed
  iseqv := ⟨
    by intro f; rfl,
    by intro f g h; exact h.symm,
    by intro f g h hfg hgh; exact hfg.trans hgh⟩

/-- The causal-role vocabulary is not supplied as source/target or p0/p1.
    It is the quotient forced by verifier-indistinguishability. -/
abbrev CausalRole (V : Evidence α → Bool) (observed : Evidence α) :=
  Quotient (effectSetoid V observed)

def roleOf (V : Evidence α → Bool) (observed : Evidence α)
    (f : Intervention α) : CausalRole V observed :=
  Quotient.mk _ f

theorem role_eq_iff_verifier_indistinguishable
    (V : Evidence α → Bool) (observed : Evidence α)
    (f g : Intervention α) :
    roleOf V observed f = roleOf V observed g ↔
      V (f observed) = V (g observed) := by
  constructor
  · intro h
    exact Quotient.exact h
  · intro h
    exact Quotient.sound h

/-- Any representation sufficient to reconstruct verifier consequence must keep
    apart every intervention pair that the verifier distinguishes. -/
def SufficientEncoding (V : Evidence α → Bool) (observed : Evidence α)
    {γ : Type v} (encode : Intervention α → γ) : Prop :=
  ∃ decode : γ → Bool, ∀ f, decode (encode f) = V (f observed)

theorem every_sufficient_encoding_preserves_verifier_distinctions
    (V : Evidence α → Bool) (observed : Evidence α)
    {γ : Type v} (encode : Intervention α → γ)
    (hsuff : SufficientEncoding V observed encode)
    (f g : Intervention α)
    (hdiff : V (f observed) ≠ V (g observed)) :
    encode f ≠ encode g := by
  rintro hsame
  obtain ⟨decode, hdecode⟩ := hsuff
  apply hdiff
  calc
    V (f observed) = decode (encode f) := (hdecode f).symm
    _ = decode (encode g) := by rw [hsame]
    _ = V (g observed) := hdecode g

/-- Verifier consequence descends to the induced role quotient, so the quotient
    itself is a sufficient interface for this consequence. -/
def roleVerdict (V : Evidence α → Bool) (observed : Evidence α) :
    CausalRole V observed → Bool :=
  Quotient.lift
    (fun f => V (f observed))
    (by
      intro f g h
      exact h)

theorem quotient_recovers_verifier_consequence
    (V : Evidence α → Bool) (observed : Evidence α)
    (f : Intervention α) :
    roleVerdict V observed (roleOf V observed f) = V (f observed) := by
  rfl

/-- If verifier consequence is erased, every counterfactual context collapses
    into one role. -/
def erasedVerifier : Evidence α → Bool := fun _ => false

theorem consequence_ablation_collapses_all_counterfactual_roles
    (observed : Evidence α) (f g : Intervention α) :
    roleOf erasedVerifier observed f = roleOf erasedVerifier observed g := by
  apply Quotient.sound
  rfl

/-- A concrete witness showing that no named deletion role is required.  The
    verifier itself distinguishes two arbitrary endomorphisms of the evidence. -/
def witnessEvidence : Evidence Bool := [false, true]

def witnessVerifier : Evidence Bool → Bool
  | [false, true] => true
  | [true] => false
  | _ => true

def keep : Intervention Bool := fun xs => xs

def tailContext : Intervention Bool
  | [] => []
  | _ :: xs => xs

theorem witness_contexts_are_verifier_distinguishable :
    witnessVerifier (keep witnessEvidence) ≠
      witnessVerifier (tailContext witnessEvidence) := by
  decide

theorem witness_contexts_form_distinct_induced_roles :
    roleOf witnessVerifier witnessEvidence keep ≠
      roleOf witnessVerifier witnessEvidence tailContext := by
  intro h
  have heq := (role_eq_iff_verifier_indistinguishable
    witnessVerifier witnessEvidence keep tailContext).1 h
  exact witness_contexts_are_verifier_distinguishable heq

/-- Main boundary theorem: the verifier consequence itself induces the minimal
    counterfactual role quotient over the full endomorphism space.  There is no
    supplied finite deletion/intervention candidate pool and no supplied role
    vocabulary.  The remaining scaffold is the evidence carrier and its full
    endomorphism meta-space. -/
theorem verifier_induces_counterfactual_role_ontology :
    witnessVerifier (keep witnessEvidence) ≠
        witnessVerifier (tailContext witnessEvidence) ∧
    roleOf witnessVerifier witnessEvidence keep ≠
        roleOf witnessVerifier witnessEvidence tailContext ∧
    roleOf erasedVerifier witnessEvidence keep =
        roleOf erasedVerifier witnessEvidence tailContext := by
  exact ⟨witness_contexts_are_verifier_distinguishable,
    witness_contexts_form_distinct_induced_roles,
    consequence_ablation_collapses_all_counterfactual_roles witnessEvidence keep tailContext⟩

#check role_eq_iff_verifier_indistinguishable
#check every_sufficient_encoding_preserves_verifier_distinctions
#check quotient_recovers_verifier_consequence
#check consequence_ablation_collapses_all_counterfactual_roles
#check witness_contexts_form_distinct_induced_roles
#check verifier_induces_counterfactual_role_ontology

end VerifierInducesCounterfactualRoleQuotient

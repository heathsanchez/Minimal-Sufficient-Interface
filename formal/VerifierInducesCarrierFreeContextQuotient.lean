import Std

namespace VerifierInducesCarrierFreeContextQuotient

/-- No sequence, arity, constructor, or list grammar is assumed. -/
abbrev Intervention (X : Type u) := X → X

/-- Counterfactual contexts are identified exactly when the verifier gives the
    same consequence after applying them to the observed state. -/
def EffectEquivalent (V : X → Bool) (observed : X)
    (f g : Intervention X) : Prop :=
  V (f observed) = V (g observed)

def effectSetoid (V : X → Bool) (observed : X) : Setoid (Intervention X) where
  r := EffectEquivalent V observed
  iseqv := ⟨
    by intro f; rfl,
    by intro f g h; exact h.symm,
    by intro f g h hfg hgh; exact hfg.trans hgh⟩

/-- The induced context-role ontology over an arbitrary raw carrier. -/
abbrev ContextRole (V : X → Bool) (observed : X) :=
  Quotient (effectSetoid V observed)

def roleOf (V : X → Bool) (observed : X) (f : Intervention X) :
    ContextRole V observed :=
  Quotient.mk _ f

theorem role_eq_iff_verifier_indistinguishable
    (V : X → Bool) (observed : X) (f g : Intervention X) :
    roleOf V observed f = roleOf V observed g ↔
      V (f observed) = V (g observed) := by
  constructor
  · intro h
    exact Quotient.exact h
  · intro h
    exact Quotient.sound h

/-- Any interface sufficient to recover verifier consequence must preserve every
    distinction present in the induced quotient. -/
def SufficientEncoding (V : X → Bool) (observed : X)
    {Y : Type v} (encode : Intervention X → Y) : Prop :=
  ∃ decode : Y → Bool, ∀ f, decode (encode f) = V (f observed)

theorem every_sufficient_encoding_preserves_verifier_distinctions
    (V : X → Bool) (observed : X)
    {Y : Type v} (encode : Intervention X → Y)
    (hsuff : SufficientEncoding V observed encode)
    (f g : Intervention X)
    (hdiff : V (f observed) ≠ V (g observed)) :
    encode f ≠ encode g := by
  rintro hsame
  obtain ⟨decode, hdecode⟩ := hsuff
  apply hdiff
  calc
    V (f observed) = decode (encode f) := (hdecode f).symm
    _ = decode (encode g) := by rw [hsame]
    _ = V (g observed) := hdecode g

/-- Verifier consequence factors through the induced quotient. -/
def roleVerdict (V : X → Bool) (observed : X) : ContextRole V observed → Bool :=
  Quotient.lift
    (fun f => V (f observed))
    (by intro f g h; exact h)

theorem quotient_recovers_verifier_consequence
    (V : X → Bool) (observed : X) (f : Intervention X) :
    roleVerdict V observed (roleOf V observed f) = V (f observed) := by
  rfl

/-- Erasing verifier consequence collapses the entire induced role ontology. -/
def erasedVerifier : X → Bool := fun _ => false

theorem consequence_ablation_collapses_all_roles
    (observed : X) (f g : Intervention X) :
    roleOf erasedVerifier observed f = roleOf erasedVerifier observed g := by
  exact Quotient.sound rfl

/-- A witness with no list structure at all. -/
def witnessObserved : Bool := true

def witnessVerifier : Bool → Bool := id

def keep : Intervention Bool := id

def flip : Intervention Bool := not

theorem witness_contexts_are_verifier_distinguishable :
    witnessVerifier (keep witnessObserved) ≠
      witnessVerifier (flip witnessObserved) := by
  decide

theorem witness_contexts_form_distinct_roles :
    roleOf witnessVerifier witnessObserved keep ≠
      roleOf witnessVerifier witnessObserved flip := by
  intro h
  have heq := (role_eq_iff_verifier_indistinguishable
    witnessVerifier witnessObserved keep flip).1 h
  exact witness_contexts_are_verifier_distinguishable heq

/-- Main theorem: sequence/list grammar is unnecessary for consequence-induced
    context-role formation.  A raw carrier, an observed state, verifier
    consequence, and the carrier's transformation space suffice.  The remaining
    scaffold is therefore the carrier and its endomorphism universe itself. -/
theorem verifier_induces_roles_without_evidence_grammar :
    witnessVerifier (keep witnessObserved) ≠
        witnessVerifier (flip witnessObserved) ∧
    roleOf witnessVerifier witnessObserved keep ≠
        roleOf witnessVerifier witnessObserved flip ∧
    roleOf erasedVerifier witnessObserved keep =
        roleOf erasedVerifier witnessObserved flip := by
  exact ⟨witness_contexts_are_verifier_distinguishable,
    witness_contexts_form_distinct_roles,
    consequence_ablation_collapses_all_roles witnessObserved keep flip⟩

#check role_eq_iff_verifier_indistinguishable
#check every_sufficient_encoding_preserves_verifier_distinctions
#check quotient_recovers_verifier_consequence
#check consequence_ablation_collapses_all_roles
#check verifier_induces_roles_without_evidence_grammar

end VerifierInducesCarrierFreeContextQuotient

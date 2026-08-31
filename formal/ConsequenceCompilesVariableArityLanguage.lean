import ConsequenceCompilesObligationGenerator

universe u v

namespace ConsequenceCompilesVariableArityLanguage

open GenericResidualCompletion
open ResidualGeneratesNextObligation

/-- A variable-arity syntax seed: an obligation candidate is any finite list of
    currently realized tokens.  Unlike the previous binary compiler, arity is
    data rather than part of the meta-signature. -/
abbrev TokenTuple (S : CapabilityState.{u,v}) := List (RealizedToken S)

/-- Verifier consequence directly defines which finite tuples form obligations.
    There is no fixed arity in the compiler. -/
structure VariableGenerator (S : CapabilityState.{u,v}) where
  forms : TokenTuple S → Prop

/-- Compile a Bool-valued verifier consequence into a variable-arity obligation
    language. -/
def compileVariableGenerator
    {S : CapabilityState.{u,v}}
    (C : TokenTuple S → Bool) : VariableGenerator S where
  forms := fun args => C args = true

/-- A generated obligation carries exactly the verifier-accepted finite tuple. -/
structure GeneratedObligation
    (S : CapabilityState.{u,v}) (G : VariableGenerator S) where
  args : TokenTuple S
  admissible : G.forms args

/-- Newly generated obligations begin unrealized. -/
def generatedState
    (S : CapabilityState.{u,v}) (G : VariableGenerator S) : CapabilityState where
  Obligation := GeneratedObligation S G
  Realize := fun _ => Empty

/-- Erasing verifier consequence produces an empty obligation language. -/
def erasedConsequence {S : CapabilityState.{u,v}} : TokenTuple S → Bool :=
  fun _ => false

 theorem erased_consequence_generates_no_obligations
    {S : CapabilityState.{u,v}} :
    ¬ Nonempty (GeneratedObligation S
      (compileVariableGenerator (erasedConsequence (S := S)))) := by
  intro h
  rcases h with ⟨o⟩
  have hadmissible := o.admissible
  simp [compileVariableGenerator, erasedConsequence] at hadmissible

/-- Before repair, no realized token can name the certified missing target. -/
theorem target_token_unavailable_before_repair
    {S : CapabilityState.{u,v}} (r : VerifiedResidual S) :
    ¬ ∃ t : RealizedToken S, t.obligation = r.target := by
  rintro ⟨t, ht⟩
  have hw : S.Realize r.target := ht ▸ t.witness
  exact r.unrealized ⟨hw⟩

/-- Lower repair makes the missing target available as a token. -/
def generatedTargetTuple
    {S : CapabilityState.{u,v}} (r : VerifiedResidual S) :
    TokenTuple (complete S (generatedDemand r)) :=
  [generatedTargetToken r]

/-- Retained witnesses can extend that tuple without changing the compiler. -/
def generatedTernaryTuple
    {S : CapabilityState.{u,v}} (r : VerifiedResidual S)
    {a b : S.Obligation} (ha : S.Realize a) (hb : S.Realize b) :
    TokenTuple (complete S (generatedDemand r)) :=
  [generatedTargetToken r, retainedToken ha, retainedToken hb]

/-- Arity is now observable by consequence rather than fixed by the compiler. -/
def arityConsequence
    {S : CapabilityState.{u,v}} (n : Nat) : TokenTuple S → Bool :=
  fun args => decide (args.length = n)

 theorem unary_consequence_accepts_unary_generated_tuple
    {S : CapabilityState.{u,v}} (r : VerifiedResidual S) :
    arityConsequence (S := complete S (generatedDemand r)) 1
      (generatedTargetTuple r) = true := by
  simp [arityConsequence, generatedTargetTuple]

 theorem ternary_consequence_accepts_ternary_generated_tuple
    {S : CapabilityState.{u,v}} (r : VerifiedResidual S)
    {a b : S.Obligation} (ha : S.Realize a) (hb : S.Realize b) :
    arityConsequence (S := complete S (generatedDemand r)) 3
      (generatedTernaryTuple r ha hb) = true := by
  simp [arityConsequence, generatedTernaryTuple]

/-- Changing only verifier consequence changes the accepted arity while the
    compilation mechanism is literally unchanged. -/
theorem changing_consequence_changes_accepted_arity
    {S : CapabilityState.{u,v}} (r : VerifiedResidual S)
    {a b : S.Obligation} (ha : S.Realize a) (hb : S.Realize b) :
    (compileVariableGenerator
      (arityConsequence (S := complete S (generatedDemand r)) 1)).forms
        (generatedTargetTuple r) ∧
    ¬ (compileVariableGenerator
      (arityConsequence (S := complete S (generatedDemand r)) 3)).forms
        (generatedTargetTuple r) ∧
    (compileVariableGenerator
      (arityConsequence (S := complete S (generatedDemand r)) 3)).forms
        (generatedTernaryTuple r ha hb) := by
  simp [compileVariableGenerator, arityConsequence,
    generatedTargetTuple, generatedTernaryTuple]

/-- Any verifier-accepted finite tuple directly becomes a generated obligation. -/
def consequenceGeneratedObligation
    {S : CapabilityState.{u,v}}
    (C : TokenTuple S → Bool) (args : TokenTuple S)
    (haccept : C args = true) :
    GeneratedObligation S (compileVariableGenerator C) where
  args := args
  admissible := haccept

/-- Generated variable-arity obligations can themselves be returned as
    structured verifier residuals. -/
def consequenceGeneratedResidual
    {S : CapabilityState.{u,v}}
    (C : TokenTuple S → Bool) (args : TokenTuple S)
    (haccept : C args = true) :
    VerifiedResidual (generatedState S (compileVariableGenerator C)) where
  target := consequenceGeneratedObligation C args haccept
  unrealized := by
    intro h
    rcases h with ⟨h⟩
    exact Empty.elim h

/-- The unchanged semantic-kind-blind completion repairs a variable-arity
    consequence-generated residual. -/
theorem same_generic_operator_repairs_variable_arity_residual
    {S : CapabilityState.{u,v}}
    (C : TokenTuple S → Bool) (args : TokenTuple S)
    (haccept : C args = true) :
    Nonempty
      ((complete
        (generatedState S (compileVariableGenerator C))
        (generatedDemand (consequenceGeneratedResidual C args haccept))).Realize
        (consequenceGeneratedResidual C args haccept).target) := by
  exact failure_forces_target_realization
    (consequenceGeneratedResidual C args haccept)

/-- End-to-end deciding theorem: repair creates a token that was impossible
    before failure; the same variable-arity compiler admits a verifier-selected
    arity-three tuple; that tuple becomes a fresh residual; generic completion
    repairs it; and erasing consequence collapses the generated language.

    This removes fixed binary arity.  It still supplies the finite-list
    meta-signature itself, so it is not unrestricted ontology invention. -/
theorem consequence_compiles_variable_arity_obligation_language
    {S : CapabilityState.{u,v}} (r : VerifiedResidual S)
    {a b : S.Obligation} (ha : S.Realize a) (hb : S.Realize b) :
    (¬ ∃ t : RealizedToken S, t.obligation = r.target) ∧
    arityConsequence (S := complete S (generatedDemand r)) 3
      (generatedTernaryTuple r ha hb) = true ∧
    Nonempty
      ((complete
        (generatedState (complete S (generatedDemand r))
          (compileVariableGenerator
            (arityConsequence (S := complete S (generatedDemand r)) 3)))
        (generatedDemand
          (consequenceGeneratedResidual
            (arityConsequence (S := complete S (generatedDemand r)) 3)
            (generatedTernaryTuple r ha hb)
            (ternary_consequence_accepts_ternary_generated_tuple r ha hb)))).Realize
        (consequenceGeneratedResidual
          (arityConsequence (S := complete S (generatedDemand r)) 3)
          (generatedTernaryTuple r ha hb)
          (ternary_consequence_accepts_ternary_generated_tuple r ha hb)).target) ∧
    (¬ Nonempty
      (GeneratedObligation
        (complete S (generatedDemand r))
        (compileVariableGenerator
          (erasedConsequence (S := complete S (generatedDemand r)))))) := by
  refine ⟨target_token_unavailable_before_repair r,
    ternary_consequence_accepts_ternary_generated_tuple r ha hb, ?_,
    erased_consequence_generates_no_obligations⟩
  exact same_generic_operator_repairs_variable_arity_residual
    (arityConsequence (S := complete S (generatedDemand r)) 3)
    (generatedTernaryTuple r ha hb)
    (ternary_consequence_accepts_ternary_generated_tuple r ha hb)

#check compileVariableGenerator
#check target_token_unavailable_before_repair
#check unary_consequence_accepts_unary_generated_tuple
#check ternary_consequence_accepts_ternary_generated_tuple
#check changing_consequence_changes_accepted_arity
#check same_generic_operator_repairs_variable_arity_residual
#check consequence_compiles_variable_arity_obligation_language

end ConsequenceCompilesVariableArityLanguage

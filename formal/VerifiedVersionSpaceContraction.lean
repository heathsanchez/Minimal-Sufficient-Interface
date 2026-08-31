import FiniteExecutableDistinguishingFuture

namespace VerifiedVersionSpaceContraction

open VerifierDoesNotDeterminePointwiseRequirement
open BehavioralRepairVersionSpace
open FiniteExecutableDistinguishingFuture

/-- A version space is deliberately intensional: it is just the currently
    admissible set of repairs. No preferred representative is built in. -/
abbrev VersionSpace (I : Type) := Repair I → Prop

/-- Filtering by one externally verified future outcome. -/
def FilterAt
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (V : VersionSpace I) (f : F) (outcome : Bool) : VersionSpace I :=
  fun R => V R ∧ B.predict R f = outcome

/-- Strict contraction means every survivor was previously admissible and at
    least one previously admissible repair is eliminated. -/
def StrictContraction {I : Type}
    (W V : VersionSpace I) : Prop :=
  (∀ R, W R → V R) ∧ (∃ R, V R ∧ ¬ W R)

/-- Filtering can never invent a candidate. -/
theorem filter_is_subspace
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (V : VersionSpace I) (f : F) (outcome : Bool) :
    ∀ R, FilterAt B V f outcome R → V R := by
  intro R h
  exact h.1

/-- If a computed question separates two currently admissible repairs, every
    possible verifier outcome eliminates at least one of them. -/
theorem computed_separator_strictly_contracts
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (V : VersionSpace I)
    {R₁ R₂ : Repair I} {f : F}
    (hR₁ : V R₁) (hR₂ : V R₂)
    (hfind : firstDistinguishingFuture B R₁ R₂ = some f)
    (outcome : Bool) :
    StrictContraction (FilterAt B V f outcome) V := by
  constructor
  · exact filter_is_subspace B V f outcome
  · rcases executable_question_decides_pair B hfind outcome with hleft | hright
    · exact ⟨R₂, hR₂, by
        intro hs
        exact hleft.2 hs.2⟩
    · exact ⟨R₁, hR₁, by
        intro hs
        exact hright.2 hs.2⟩

/-- Semantic behavioural ambiguity inside an arbitrary version space therefore
    generates an executable question whose verified outcome strictly contracts
    that version space. No repair winner is supplied. -/
theorem unresolved_pair_generates_strict_version_space_progress
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (V : VersionSpace I)
    {R₁ R₂ : Repair I}
    (hR₁ : V R₁) (hR₂ : V R₂)
    (hneq : ¬ RepairEquivalent futureOf R₁ R₂) :
    ∃ f,
      firstDistinguishingFuture B R₁ R₂ = some f ∧
      ∀ outcome : Bool,
        StrictContraction (FilterAt B V f outcome) V := by
  rcases executable_search_finds_separator B hneq with ⟨f, hfind, _⟩
  exact ⟨f, hfind, by
    intro outcome
    exact computed_separator_strictly_contracts B V hR₁ hR₂ hfind outcome⟩

/-- If two repairs make the same Boolean prediction at the asked future, the
    observation cannot separate that pair. This isolates the causal role of the
    generated distinguishing question rather than generic filtering. -/
theorem nondistinguishing_question_cannot_split_pair
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (f : F) (outcome : Bool) {R₁ R₂ : Repair I}
    (heq : B.predict R₁ f = B.predict R₂ f) :
    (B.predict R₁ f = outcome ↔ B.predict R₂ f = outcome) := by
  rw [heq]

namespace Witness

open BehavioralRepairVersionSpace.DivergentWitness
open FiniteExecutableDistinguishingFuture.Witness

/-- The version space contains both cycle-6 minimal repairs and nothing is
    preselected as the answer. -/
def V : VersionSpace Idx := fun R => R = leftRepair ∨ R = rightRepair

theorem left_in : V leftRepair := Or.inl rfl
theorem right_in : V rightRepair := Or.inr rfl

/-- The executable alpha question plus either verifier outcome strictly
    contracts the two-repair version space. -/
theorem alpha_outcome_strictly_contracts (outcome : Bool) :
    StrictContraction (FilterAt basis V .alpha outcome) V := by
  exact computed_separator_strictly_contracts
    basis V left_in right_in computes_alpha outcome

end Witness

/-- Cycle-10 conclusion: unresolved behavioural diversity is not merely
    diagnosable. With a finite certified future interface, it causes executable,
    verifier-governed strict progress of the whole admissible repair space. The
    remaining selector is now sharply isolated: a non-equivalent pair must still
    be exhibited from a multi-class version space. -/
theorem verified_ambiguity_forces_strict_progress
    {I F : Type} {futureOf : I → F}
    (B : CertifiedFiniteFutureInterface I F futureOf)
    (V : VersionSpace I)
    {R₁ R₂ : Repair I}
    (hR₁ : V R₁) (hR₂ : V R₂)
    (hneq : ¬ RepairEquivalent futureOf R₁ R₂) :
    ∃ f,
      firstDistinguishingFuture B R₁ R₂ = some f ∧
      ∀ outcome : Bool,
        StrictContraction (FilterAt B V f outcome) V := by
  exact unresolved_pair_generates_strict_version_space_progress
    B V hR₁ hR₂ hneq

#check VersionSpace
#check FilterAt
#check StrictContraction
#check filter_is_subspace
#check computed_separator_strictly_contracts
#check unresolved_pair_generates_strict_version_space_progress
#check nondistinguishing_question_cannot_split_pair
#check Witness.alpha_outcome_strictly_contracts
#check verified_ambiguity_forces_strict_progress

end VerifiedVersionSpaceContraction

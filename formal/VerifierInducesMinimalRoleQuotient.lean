universe u v

namespace VerifierInducesMinimalRoleQuotient

/-- The verifier is the only operational observation.  No role labels or role
    constructors are supplied. -/
def verifierSetoid {α : Type u} (V : List α → Bool) : Setoid (List α) where
  r := fun x y => V x = V y
  iseqv := by
    constructor
    · intro x
      rfl
    · intro x y h
      exact h.symm
    · intro x y z hxy hyz
      exact hxy.trans hyz

/-- The induced role space is the quotient of evidence traces by verifier
    indistinguishability. -/
abbrev RoleSpace {α : Type u} (V : List α → Bool) :=
  Quotient (verifierSetoid V)

/-- Every raw trace has its induced operational role. -/
def roleOf {α : Type u} (V : List α → Bool) (trace : List α) : RoleSpace V :=
  Quotient.mk (verifierSetoid V) trace

/-- Verifier consequence factors canonically through the role quotient. -/
def verdictOnRole {α : Type u} (V : List α → Bool) : RoleSpace V → Bool :=
  Quotient.lift V (by
    intro x y h
    exact h)

@[simp] theorem verdictOnRole_roleOf
    {α : Type u} (V : List α → Bool) (trace : List α) :
    verdictOnRole V (roleOf V trace) = V trace := by
  rfl

/-- Verifier-distinguishable traces necessarily induce distinct roles. -/
theorem distinguishable_traces_have_distinct_roles
    {α : Type u} (V : List α → Bool) (x y : List α)
    (h : V x ≠ V y) :
    roleOf V x ≠ roleOf V y := by
  intro hrole
  have hv := congrArg (verdictOnRole V) hrole
  simp at hv
  exact h hv

/-- Conversely, verifier-indistinguishable traces collapse to one role. -/
theorem indistinguishable_traces_have_same_role
    {α : Type u} (V : List α → Bool) (x y : List α)
    (h : V x = V y) :
    roleOf V x = roleOf V y := by
  exact Quotient.sound h

/-- Exact characterization: role equality is precisely verifier
    indistinguishability. -/
theorem same_role_iff_same_verdict
    {α : Type u} (V : List α → Bool) (x y : List α) :
    roleOf V x = roleOf V y ↔ V x = V y := by
  constructor
  · intro hrole
    have hv := congrArg (verdictOnRole V) hrole
    simpa using hv
  · exact indistinguishable_traces_have_same_role V x y

/-- A single order-sensitive verifier distinction creates two genuinely distinct
    role classes without supplying an Orientation datatype. -/
theorem asymmetric_swapped_traces_generate_distinct_roles
    {α : Type u} (V : List α → Bool) (a b : α)
    (hab : V [a, b] = true)
    (hba : V [b, a] = false) :
    roleOf V [a, b] ≠ roleOf V [b, a] := by
  apply distinguishable_traces_have_distinct_roles V [a, b] [b, a]
  rw [hab, hba]
  decide

/-- Causal ablation: a verifier that erases all distinctions collapses every
    trace into the same role class. -/
def erasedVerifier {α : Type u} : List α → Bool := fun _ => false

/-- Under complete verifier erasure even swapped traces become the same role. -/
theorem erasing_verifier_collapses_swapped_roles
    {α : Type u} (a b : α) :
    roleOf (erasedVerifier : List α → Bool) [a, b] =
      roleOf erasedVerifier [b, a] := by
  exact indistinguishable_traces_have_same_role erasedVerifier [a, b] [b, a] rfl

/-- Any representation from which the verifier verdict can be recovered must
    distinguish every pair of traces that the verifier distinguishes.  Thus the
    verifier quotient captures exactly the distinctions that no sufficient
    interface is allowed to forget. -/
theorem every_sufficient_encoding_preserves_verifier_distinctions
    {α : Type u} {β : Type v}
    (V : List α → Bool)
    (encode : List α → β) (decode : β → Bool)
    (hsufficient : ∀ trace, decode (encode trace) = V trace)
    (x y : List α) (hxy : V x ≠ V y) :
    encode x ≠ encode y := by
  intro henc
  apply hxy
  calc
    V x = decode (encode x) := (hsufficient x).symm
    _ = decode (encode y) := congrArg decode henc
    _ = V y := hsufficient y

/-- The quotient itself is sufficient: no verifier-relevant information is lost. -/
theorem quotient_is_sufficient_for_verifier
    {α : Type u} (V : List α → Bool) :
    ∀ trace, verdictOnRole V (roleOf V trace) = V trace := by
  intro trace
  rfl

/-- End-to-end minimal-interface theorem.  Verifier consequence induces its own
    role ontology as the coarsest operational equality needed to preserve that
    consequence: different verdicts force different roles, equal verdicts are
    identified, every sufficient representation must retain verifier
    distinctions, and erasing consequence collapses those roles again.

    The list-of-tokens evidence carrier is still supplied.  What is no longer
    supplied is a role vocabulary, source/target enum, or role partition. -/
theorem verifier_induces_minimal_role_quotient
    {α : Type u} (V : List α → Bool) (a b : α)
    (hab : V [a, b] = true)
    (hba : V [b, a] = false) :
    (roleOf V [a, b] ≠ roleOf V [b, a]) ∧
    (verdictOnRole V (roleOf V [a, b]) = true) ∧
    (verdictOnRole V (roleOf V [b, a]) = false) ∧
    (roleOf (erasedVerifier : List α → Bool) [a, b] =
      roleOf erasedVerifier [b, a]) := by
  refine ⟨asymmetric_swapped_traces_generate_distinct_roles V a b hab hba, ?_, ?_,
    erasing_verifier_collapses_swapped_roles a b⟩
  · simpa [hab]
  · simpa [hba]

#check same_role_iff_same_verdict
#check asymmetric_swapped_traces_generate_distinct_roles
#check erasing_verifier_collapses_swapped_roles
#check every_sufficient_encoding_preserves_verifier_distinctions
#check quotient_is_sufficient_for_verifier
#check verifier_induces_minimal_role_quotient

end VerifierInducesMinimalRoleQuotient

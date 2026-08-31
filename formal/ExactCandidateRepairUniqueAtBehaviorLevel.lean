import UncoveredProfileForcesFreeCandidateExtension

namespace ExactCandidateRepairUniqueAtBehaviorLevel

open UncoveredProfileForcesFreeCandidateExtension

universe u v w z

/-- An abstract exact repair need not use `Sum H Unit` or any particular syntax.
    It must preserve all old candidates, realize the required profile, and expose
    no operational profile except an old one or the required one. -/
structure ExactRepair {H : Type u} {C : Type v}
    (V : H → C → Bool) (target : C → Bool) (K : Type w) where
  eval : K → C → Bool
  embedOld : H → K
  witness : K
  preserve : ∀ h, eval (embedOld h) = V h
  realizes : eval witness = target
  noExtra : ∀ k, Realized V (eval k) ∨ eval k = target

/-- Every exact repair has precisely the old operational image plus the demanded
    profile, independent of its raw syntax or carrier representation. -/
theorem exact_repair_realized_iff {H : Type u} {C : Type v} {K : Type w}
    {V : H → C → Bool} {target : C → Bool}
    (R : ExactRepair V target K) (p : C → Bool) :
    Realized R.eval p ↔ Realized V p ∨ p = target := by
  constructor
  · rintro ⟨k, hk⟩
    rcases R.noExtra k with hold | htarget
    · rcases hold with ⟨h, hh⟩
      exact Or.inl ⟨h, hh.trans hk⟩
    · exact Or.inr (hk.symm.trans htarget)
  · intro h
    rcases h with hold | htarget
    · rcases hold with ⟨h, hh⟩
      exact ⟨R.embedOld h, (R.preserve h).trans hh⟩
    · exact ⟨R.witness, R.realizes.trans htarget.symm⟩

/-- Therefore any abstract exact repair is behaviorally equivalent to the free
    one-witness construction.  The `Sum H Unit` presentation is not a scientific
    commitment: only the consequence-selected operational image is invariant. -/
theorem free_extension_is_behaviorally_canonical
    {H : Type u} {C : Type v} {K : Type w}
    {V : H → C → Bool} {target : C → Bool}
    (R : ExactRepair V target K) :
    ∀ p : C → Bool,
      Realized R.eval p ↔ Realized (extendVerifier V target) p := by
  intro p
  rw [exact_repair_realized_iff R p,
      realized_after_extension_iff V target p]

/-- Two entirely different exact repair carriers are observationally identical
    to the verifier once old behavior and the single demanded profile are fixed. -/
theorem all_exact_repairs_behaviorally_equivalent
    {H : Type u} {C : Type v} {K₁ : Type w} {K₂ : Type z}
    {V : H → C → Bool} {target : C → Bool}
    (R₁ : ExactRepair V target K₁) (R₂ : ExactRepair V target K₂) :
    ∀ p : C → Bool,
      Realized R₁.eval p ↔ Realized R₂.eval p := by
  intro p
  rw [exact_repair_realized_iff R₁ p,
      exact_repair_realized_iff R₂ p]

/-- The free one-witness extension itself satisfies the abstract exact-repair
    interface. -/
def freeRepair {H : Type u} {C : Type v}
    (V : H → C → Bool) (target : C → Bool) :
    ExactRepair V target (Extend H) where
  eval := extendVerifier V target
  embedOld := Sum.inl
  witness := newWitness
  preserve := by intro h; rfl
  realizes := rfl
  noExtra := by
    intro k
    cases k with
    | inl h => exact Or.inl ⟨h, rfl⟩
    | inr unit =>
        cases unit
        exact Or.inr rfl

/-- Main result: once consequence requires exactly one new operational profile,
    minimal exact repair determines the candidate extension only up to verifier
    behavior.  Any hidden syntactic choice is underdetermined and unnecessary. -/
theorem minimal_candidate_repair_unique_at_behavior_level
    {H : Type u} {C : Type v} {K : Type w}
    {V : H → C → Bool} {target : C → Bool}
    (R : ExactRepair V target K) :
    (∀ p : C → Bool,
      Realized R.eval p ↔ Realized (extendVerifier V target) p) ∧
    (∀ p : C → Bool,
      Realized R.eval p ↔ Realized (freeRepair V target).eval p) := by
  constructor
  · exact free_extension_is_behaviorally_canonical R
  · intro p
    exact all_exact_repairs_behaviorally_equivalent R (freeRepair V target) p

#check exact_repair_realized_iff
#check free_extension_is_behaviorally_canonical
#check all_exact_repairs_behaviorally_equivalent
#check freeRepair
#check minimal_candidate_repair_unique_at_behavior_level

end ExactCandidateRepairUniqueAtBehaviorLevel

import UncoveredProfileForcesFreeCandidateExtension

namespace FreeCandidateExtensionIsLeastBehavioralRepair

open UncoveredProfileForcesFreeCandidateExtension

universe u v w z

/-- Behavioral inclusion between two candidate carriers sharing a verifier
    context family.  Only realized verifier profiles matter. -/
def ImageLe {C : Type v} {K₁ : Type w} {K₂ : Type z}
    (W₁ : K₁ → C → Bool) (W₂ : K₂ → C → Bool) : Prop :=
  ∀ p : C → Bool, Realized W₁ p → Realized W₂ p

/-- A repair is deliberately weak: it need only retain every old operational
    profile and realize the demanded profile.  There is no `noExtra` premise. -/
structure BehavioralRepair {H : Type u} {C : Type v}
    (V : H → C → Bool) (target : C → Bool) (K : Type w) where
  eval : K → C → Bool
  preservesOld : ImageLe V eval
  realizesTarget : Realized eval target

/-- The free one-witness carrier extension is a behavioral repair. -/
def freeRepair {H : Type u} {C : Type v}
    (V : H → C → Bool) (target : C → Bool) :
    BehavioralRepair V target (Extend H) where
  eval := extendVerifier V target
  preservesOld := by
    intro p hp
    rcases hp with ⟨h, hh⟩
    exact ⟨Sum.inl h, hh⟩
  realizesTarget := ⟨newWitness, rfl⟩

/-- Core leastness theorem.  Every operational profile exposed by the free
    extension must occur in *every* repair that preserves the old image and
    realizes the target.  No exactness/no-extra condition is assumed. -/
theorem free_extension_least
    {H : Type u} {C : Type v} {K : Type w}
    (V : H → C → Bool) (target : C → Bool)
    (R : BehavioralRepair V target K) :
    ImageLe (extendVerifier V target) R.eval := by
  intro p hp
  have hshape : Realized V p ∨ p = target :=
    (realized_after_extension_iff V target p).mp hp
  rcases hshape with hold | htarget
  · exact R.preservesOld p hold
  · rcases R.realizesTarget with ⟨k, hk⟩
    exact ⟨k, hk.trans htarget.symm⟩

/-- A least repair is defined only by the behavioral preorder, not by its raw
    syntax or a separately supplied no-extra axiom. -/
def IsLeastRepair {H : Type u} {C : Type v} {K : Type w}
    {V : H → C → Bool} {target : C → Bool}
    (R : BehavioralRepair V target K) : Prop :=
  ∀ {K' : Type u}, (S : BehavioralRepair V target K') → ImageLe R.eval S.eval

/-- Universe-polymorphic version of leastness used to compare arbitrary repair
    carriers without constraining their syntax universe. -/
def IsLeastRepairU {H : Type u} {C : Type v} {K : Type w}
    {V : H → C → Bool} {target : C → Bool}
    (R : BehavioralRepair V target K) : Prop :=
  ∀ {K' : Type z}, (S : BehavioralRepair V target K') → ImageLe R.eval S.eval

/-- The free extension is least against an arbitrary competitor carrier. -/
theorem free_extension_least_against
    {H : Type u} {C : Type v} {K : Type w}
    (V : H → C → Bool) (target : C → Bool)
    (R : BehavioralRepair V target K) :
    ∀ p, Realized (freeRepair V target).eval p → Realized R.eval p := by
  exact free_extension_least V target R

/-- If some other repair is itself behaviorally least, then it and the free
    extension have exactly the same operational image.  Thus "no unrelated
    behavior" is a consequence of leastness, not an input axiom. -/
theorem any_least_repair_behaviorally_equals_free
    {H : Type u} {C : Type v} {K : Type w}
    (V : H → C → Bool) (target : C → Bool)
    (R : BehavioralRepair V target K)
    (hRleast : ImageLe R.eval (freeRepair V target).eval) :
    ∀ p : C → Bool,
      Realized R.eval p ↔ Realized (freeRepair V target).eval p := by
  intro p
  constructor
  · exact hRleast p
  · exact free_extension_least V target R p

/-- In particular, every least repair has exactly the old image plus the one
    demanded profile. -/
theorem least_repair_has_no_unrelated_behavior
    {H : Type u} {C : Type v} {K : Type w}
    (V : H → C → Bool) (target : C → Bool)
    (R : BehavioralRepair V target K)
    (hRleast : ImageLe R.eval (freeRepair V target).eval) :
    ∀ p : C → Bool,
      Realized R.eval p ↔ Realized V p ∨ p = target := by
  intro p
  calc
    Realized R.eval p ↔ Realized (freeRepair V target).eval p :=
      any_least_repair_behaviorally_equals_free V target R hRleast p
    _ ↔ Realized V p ∨ p = target := by
      change Realized (extendVerifier V target) p ↔ Realized V p ∨ p = target
      exact realized_after_extension_iff V target p

/-- Main result: under the natural operational preorder, the free candidate
    extension is the least repair satisfying only preservation and target
    realization.  Therefore the exactness/no-extra law does not have to be
    supplied separately; it follows for any least repair.

    Remaining scaffold: verifier context family and the behavioral inclusion
    preorder itself. -/
theorem minimality_forces_exact_behavioral_candidate_genesis
    {H : Type u} {C : Type v} {K : Type w}
    (V : H → C → Bool) (target : C → Bool)
    (R : BehavioralRepair V target K)
    (hRleast : ImageLe R.eval (freeRepair V target).eval) :
    ImageLe (freeRepair V target).eval R.eval ∧
    (∀ p : C → Bool,
      Realized R.eval p ↔ Realized V p ∨ p = target) := by
  exact ⟨
    free_extension_least V target R,
    least_repair_has_no_unrelated_behavior V target R hRleast⟩

#check freeRepair
#check free_extension_least
#check free_extension_least_against
#check any_least_repair_behaviorally_equals_free
#check least_repair_has_no_unrelated_behavior
#check minimality_forces_exact_behavioral_candidate_genesis

end FreeCandidateExtensionIsLeastBehavioralRepair

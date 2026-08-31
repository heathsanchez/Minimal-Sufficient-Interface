import Std

namespace CanonicalFailureConsequence

universe u v

variable {Ω : Type u}
variable (G : Ω → Ω → Type v)

inductive Path : Ω → Ω → Type (max u v) where
  | refl (x : Ω) : Path x x
  | step {x y z : Ω} : G x y → Path y z → Path x z

namespace Path

def comp {x y z : Ω} : Path G x y → Path G y z → Path G x z
  | .refl _, q => q
  | .step g p, q => .step g (comp p q)

end Path

structure TargetObservation (target : Ω) where
  carrier : Ω → Type (max u v)
  atTarget : carrier target
  pull {x y : Ω} : Path G x y → carrier y → carrier x

def representable (target : Ω) : TargetObservation G target where
  carrier := fun z => Path G z target
  atTarget := Path.refl target
  pull := fun p q => Path.comp G p q

def liftToObservation {target : Ω} (O : TargetObservation G target) {z : Ω} :
    Path G z target → O.carrier z :=
  fun p => O.pull p O.atTarget

theorem representable_maps_to_every_target_observation
    {target : Ω} (O : TargetObservation G target) (z : Ω) :
    Nonempty (Path G z target → O.carrier z) := by
  exact ⟨liftToObservation G O⟩

structure VerifiedFailure where
  blocked : Ω
  target : Ω
  impossible : ¬ Nonempty (Path G blocked target)

def canonicalConsequence (r : VerifiedFailure G) : TargetObservation G r.target :=
  representable G r.target

theorem canonical_consequence_separates_failure (r : VerifiedFailure G) :
    (¬ Nonempty ((canonicalConsequence G r).carrier r.blocked)) ∧
      Nonempty ((canonicalConsequence G r).carrier r.target) := by
  constructor
  · exact r.impossible
  · exact ⟨(canonicalConsequence G r).atTarget⟩

theorem failure_consequence_is_free
    (r : VerifiedFailure G)
    (O : TargetObservation G r.target)
    (z : Ω) :
    Nonempty ((canonicalConsequence G r).carrier z → O.carrier z) := by
  exact ⟨liftToObservation G O⟩

structure ClosedObservation where
  carrier : Ω → Type (max u v)
  pull {x y : Ω} : Path G x y → carrier y → carrier x

def emptyClosedObservation : ClosedObservation G where
  carrier := fun _ => PEmpty
  pull := fun _ e => nomatch e

theorem target_witness_is_necessary_for_universal_generation (target : Ω) :
    ¬ Nonempty ((Path G target target) →
      (emptyClosedObservation G).carrier target) := by
  intro h
  exact h.elim (fun f => f (Path.refl target))

theorem canonical_failure_consequence_certificate
    (r : VerifiedFailure G) :
    ((¬ Nonempty ((canonicalConsequence G r).carrier r.blocked)) ∧
      Nonempty ((canonicalConsequence G r).carrier r.target)) ∧
    (∀ (O : TargetObservation G r.target) (z : Ω),
      Nonempty ((canonicalConsequence G r).carrier z → O.carrier z)) := by
  constructor
  · exact canonical_consequence_separates_failure G r
  · intro O z
    exact failure_consequence_is_free G r O z

#check representable_maps_to_every_target_observation
#check canonical_consequence_separates_failure
#check failure_consequence_is_free
#check target_witness_is_necessary_for_universal_generation
#check canonical_failure_consequence_certificate

end CanonicalFailureConsequence

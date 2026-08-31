import Std

namespace ReflexivityNotForcedByDirectedFailure

universe u v

structure RawDirectedSubstrate where
  Obj : Type u
  Hom : Obj → Obj → Type v

structure DirectedAsymmetry (S : RawDirectedSubstrate) where
  left : S.Obj
  right : S.Obj
  forward : Nonempty (S.Hom left right)
  noBack : ¬ Nonempty (S.Hom right left)

/-- A two-point raw directed substrate with exactly one nonempty edge `false → true`.
    No reflexive transport exists at either point. -/
def twoPoint : RawDirectedSubstrate where
  Obj := Bool
  Hom := fun x y => if x = false ∧ y = true then Unit else Empty

private theorem hom_false_true : Nonempty (twoPoint.Hom false true) := by
  simp [twoPoint]

private theorem no_hom_true_false : ¬ Nonempty (twoPoint.Hom true false) := by
  simp [twoPoint]

private theorem no_hom_false_false : ¬ Nonempty (twoPoint.Hom false false) := by
  simp [twoPoint]

private theorem no_hom_true_true : ¬ Nonempty (twoPoint.Hom true true) := by
  simp [twoPoint]

/-- Directed interaction plus failed reverse transport can exist without any self-transport. -/
theorem asymmetry_without_reflexivity :
    (∃ r : DirectedAsymmetry twoPoint, True) ∧
    (¬ Nonempty (twoPoint.Hom false false)) ∧
    (¬ Nonempty (twoPoint.Hom true true)) := by
  refine ⟨?_, no_hom_false_false, no_hom_true_true⟩
  refine ⟨{
    left := false
    right := true
    forward := hom_false_true
    noBack := no_hom_true_false
  }, trivial⟩

/-- Therefore the proposition “every raw directed asymmetry forces source reflexivity” is false. -/
theorem source_reflexivity_not_forced :
    ¬ (∀ (S : RawDirectedSubstrate) (r : DirectedAsymmetry S), Nonempty (S.Hom r.left r.left)) := by
  intro h
  let r : DirectedAsymmetry twoPoint := {
    left := false
    right := true
    forward := hom_false_true
    noBack := no_hom_true_false
  }
  exact no_hom_false_false (h twoPoint r)

/-- Likewise, raw directed asymmetry does not force target reflexivity. -/
theorem target_reflexivity_not_forced :
    ¬ (∀ (S : RawDirectedSubstrate) (r : DirectedAsymmetry S), Nonempty (S.Hom r.right r.right)) := by
  intro h
  let r : DirectedAsymmetry twoPoint := {
    left := false
    right := true
    forward := hom_false_true
    noBack := no_hom_true_false
  }
  exact no_hom_true_true (h twoPoint r)

/-- The full generic reflexivity law cannot be derived from raw directed structure alone. -/
theorem global_reflexivity_not_forced :
    ¬ (∀ (S : RawDirectedSubstrate), (∃ r : DirectedAsymmetry S, True) → ∀ x : S.Obj, Nonempty (S.Hom x x)) := by
  intro h
  have hasAsym : ∃ r : DirectedAsymmetry twoPoint, True := by
    refine ⟨{
      left := false
      right := true
      forward := hom_false_true
      noBack := no_hom_true_false
    }, trivial⟩
  exact no_hom_false_false (h twoPoint hasAsym false)

#check asymmetry_without_reflexivity
#check source_reflexivity_not_forced
#check target_reflexivity_not_forced
#check global_reflexivity_not_forced

end ReflexivityNotForcedByDirectedFailure

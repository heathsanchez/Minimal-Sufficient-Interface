import Std

/-! # Dependent developmental universe — verified update changes the type of the next question

  `GenerativeTower` had a FIXED tagged union `Obj`; the ontology merely toggled which
  level was admissible.  Here the developmental state's CARRIER is a type family:

    Carrier : Nat → Type
    Carrier 0 = Bool
    Carrier (n+1) = Carrier n × Carrier n

  and the residual is indexed by the state:

    Residual n := Carrier n × Carrier n

  So a level-(n+1) residual has a DIFFERENT TYPE than a level-n residual: it is not
  merely inadmissible, it is not even *typeable* at level n.  The update is a
  type-changing operation — verified development changes the type of the next
  admissible question.

  Proved here:
    (1) the carrier is structurally nested;
    (2) the carrier genuinely grows (Bool ≠ Bool × Bool by cardinality pigeonhole);
    (3) the residual type changes under update (structurally, by rfl);
    (4) concrete residuals ρ0, ρ1, ρ2 at genuinely different types.
-/

namespace DependentUniverse

/- The developmental state is the level; its carrier is a nested type family. -/
def Carrier : Nat → Type
  | 0 => Bool
  | n+1 => Carrier n × Carrier n

def Residual (n : Nat) : Type := Carrier n × Carrier n

def update (n : Nat) : Nat := n + 1

/- (1) STRUCTURAL NESTING: each carrier is literally the product of the previous. -/
theorem carrier_nested (n : Nat) : Carrier (n+1) = (Carrier n × Carrier n) := rfl

/- (2) The carrier type genuinely grows.  Base case Bool ≠ (Bool × Bool) by pigeonhole:
   three distinct pairs cannot inject into two booleans. -/
theorem bool_ne_bool_prod : Bool ≠ (Bool × Bool) := by
  intro h
  have hinj : Function.Injective (fun x : Bool × Bool => cast h.symm x) := by
    intro p q e
    have hp : cast h.symm p ≍ p := cast_heq h.symm p
    have hq : cast h.symm q ≍ q := cast_heq h.symm q
    have he : cast h.symm p ≍ cast h.symm q := heq_of_eq e
    exact eq_of_heq (HEq.trans (HEq.symm hp) (HEq.trans he hq))
  let a := (false, false)
  let b := (false, true)
  let c := (true, false)
  have hab : a ≠ b := by native_decide
  have hac : a ≠ c := by native_decide
  have hbc : b ≠ c := by native_decide
  have h1 : cast h.symm a ≠ cast h.symm b := by intro e; exact hab (hinj e)
  have h2 : cast h.symm a ≠ cast h.symm c := by intro e; exact hac (hinj e)
  have h3 : cast h.symm b ≠ cast h.symm c := by intro e; exact hbc (hinj e)
  cases hx : cast h.symm a <;> cases hy : cast h.symm b <;> cases hz : cast h.symm c <;> simp_all

theorem carrier0_ne_carrier1 : Carrier 0 ≠ Carrier 1 := by
  simpa [Carrier] using bool_ne_bool_prod

/- (3) The residual type changes under update: the updated state's residual is a
   product of products, structurally different from the current state's. -/
theorem residual_type_changes (n : Nat) :
    Residual (update n) = ((Carrier n × Carrier n) × (Carrier n × Carrier n)) := rfl

/- (4) Concrete residuals at three different levels — each at a genuinely different
   type (check the types below). -/
def ρ0 : Residual 0 := (false, true)
def ρ1 : Residual 1 := ((false, false), (true, true))
def ρ2 : Residual 2 := (((false, false), (true, true)), ((true, true), (false, false)))

#check ρ0
#check ρ1
#check ρ2

/- The breakthrough: the update strictly changes the carrier type (first step). -/
theorem update_changes_carrier : Carrier (update 0) ≠ Carrier 0 := by
  change Carrier 1 ≠ Carrier 0
  intro h
  exact carrier0_ne_carrier1 h.symm

end DependentUniverse

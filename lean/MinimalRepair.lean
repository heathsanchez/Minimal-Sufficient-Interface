import Std
import Kernel

universe u

namespace MinimalRepair

open MeetKernel

variable {L : Type u} (K : MeetKernel L)

/-- A meet update refines its right-hand verified constraint. -/
theorem meet_refines_right (a b : L) : K.Le (K.meet a b) b := by
  unfold MeetKernel.Le
  calc
    K.meet (K.meet a b) b = K.meet a (K.meet b b) := K.assoc a b b
    _ = K.meet a b := by rw [K.idem b]

/-- Any state refining both inputs also refines their meet. Together with
    `update_refines` and `meet_refines_right`, this is the universal property
    of the MSI update. -/
theorem refines_meet {x a b : L}
    (hxa : K.Le x a) (hxb : K.Le x b) : K.Le x (K.meet a b) := by
  unfold MeetKernel.Le at hxa hxb ⊢
  calc
    K.meet x (K.meet a b) = K.meet (K.meet x a) b := (K.assoc x a b).symm
    _ = K.meet x b := by rw [hxa]
    _ = x := hxb

/-- `a ∧ b` is the unique least-change refinement of `a` that also satisfies
    the verified constraint `b`: it refines both, and every competing common
    refinement is at least as fine.

    Recall that `K.Le x y` means `x` is a refinement of `y`. Thus this is the
    greatest lower bound in the induced order, equivalently the coarsest state
    among all states that satisfy both requirements. -/
theorem minimal_justified_repair (a b : L) :
    K.Le (K.meet a b) a ∧
    K.Le (K.meet a b) b ∧
    ∀ x, K.Le x a → K.Le x b → K.Le x (K.meet a b) := by
  refine ⟨K.update_refines a b, meet_refines_right K a b, ?_⟩
  intro x hxa hxb
  exact refines_meet K hxa hxb

/-- Any two states satisfying the universal property of the common refinement
    are equal. This supplies uniqueness without choosing coordinates or a
    concrete representation of the refinement lattice. -/
theorem unique_common_refinement {a b m n : L}
    (hma : K.Le m a) (hmb : K.Le m b)
    (hmGreatest : ∀ x, K.Le x a → K.Le x b → K.Le x m)
    (hna : K.Le n a) (hnb : K.Le n b)
    (hnGreatest : ∀ x, K.Le x a → K.Le x b → K.Le x n) :
    m = n := by
  have hmn : K.Le m n := hnGreatest m hma hmb
  have hnm : K.Le n m := hmGreatest n hna hnb
  exact K.le_antisymm hmn hnm

/-- The concrete MSI update itself is therefore the unique object with the
    least-change repair universal property. -/
theorem meet_unique_minimal_repair {a b m : L}
    (hma : K.Le m a) (hmb : K.Le m b)
    (hmGreatest : ∀ x, K.Le x a → K.Le x b → K.Le x m) :
    m = K.meet a b := by
  apply K.le_antisymm
  · exact refines_meet K hma hmb
  · exact hmGreatest (K.meet a b) (K.update_refines a b) (meet_refines_right K a b)

end MinimalRepair

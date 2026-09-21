import Std
import DevelopmentalCategory

universe u v w z

namespace DevelopmentalLyapunov

open TypedBehaviouralCongruence
open DevelopmentalCategory

variable (C : SmallCategory)
variable (A : Action C)
variable (Obs : C.Obj → Type z)
variable (observe : ∀ X, A.State X → Obs X)

/-- Full contextual behavioural equivalence always implies stage-relative
    behavioural equivalence, because a stage exposes only a subset of all
    ambient continuations. -/
theorem full_implies_stage
    (S : Stage C) {X : C.Obj} {x y : A.State X}
    (h : BehEq C A Obs observe X x y) :
    BehEqAt C A Obs observe S X x y := by
  intro Y f hf
  exact h Y f

/-- The unresolved consequential pairs inside a declared finite carrier U:
    pairs still merged by the current stage but separable by some ambient
    protected continuation. -/
noncomputable def unresolvedPairs
    (S : Stage C) (X : C.Obj) (U : Finset (A.State X)) :
    Finset (A.State X × A.State X) := by
  classical
  exact (U.product U).filter (fun p =>
    BehEqAt C A Obs observe S X p.1 p.2 ∧
      ¬ BehEq C A Obs observe X p.1 p.2)

/-- Developmental Lyapunov potential: the number of ordered state pairs in U
    that the current interface still merges although the full protected future
    can distinguish them. -/
noncomputable def potential
    (S : Stage C) (X : C.Obj) (U : Finset (A.State X)) : Nat :=
  (unresolvedPairs C A Obs observe S X U).card

/-- Extending the accessible continuation family can only remove unresolved
    consequential pairs. -/
theorem unresolvedPairs_mono
    {S T : Stage C} (hST : Extends C S T)
    (X : C.Obj) (U : Finset (A.State X)) :
    unresolvedPairs C A Obs observe T X U ⊆
      unresolvedPairs C A Obs observe S X U := by
  classical
  intro p hp
  simp [unresolvedPairs] at hp ⊢
  exact ⟨hp.1, extension_refines C A Obs observe hST X p.1 p.2 hp.2.1, hp.2.2⟩

/-- Lyapunov monotonicity: lawful capability growth never increases the number
    of still-hidden consequential distinctions. -/
theorem potential_nonincreasing
    {S T : Stage C} (hST : Extends C S T)
    (X : C.Obj) (U : Finset (A.State X)) :
    potential C A Obs observe T X U ≤ potential C A Obs observe S X U := by
  classical
  exact Finset.card_le_card (unresolvedPairs_mono C A Obs observe hST X U)

/-- If an extension actually splits one old behavioural class along a pair
    inside U that is separable in the full ambient future, the potential drops
    strictly. -/
theorem potential_strict_decrease
    {S T : Stage C} (hST : Extends C S T)
    (X : C.Obj) (U : Finset (A.State X))
    {x y : A.State X}
    (hx : x ∈ U) (hy : y ∈ U)
    (hold : BehEqAt C A Obs observe S X x y)
    (hfull : ¬ BehEq C A Obs observe X x y)
    (hsplit : ¬ BehEqAt C A Obs observe T X x y) :
    potential C A Obs observe T X U < potential C A Obs observe S X U := by
  classical
  apply Finset.card_lt_card
  have hsub :
      unresolvedPairs C A Obs observe T X U ⊆
        unresolvedPairs C A Obs observe S X U :=
    unresolvedPairs_mono C A Obs observe hST X U
  have hmemS :
      (x, y) ∈ unresolvedPairs C A Obs observe S X U := by
    simp [unresolvedPairs, hx, hy, hold, hfull]
  have hnotT :
      (x, y) ∉ unresolvedPairs C A Obs observe T X U := by
    simp [unresolvedPairs, hsplit]
  have hne :
      unresolvedPairs C A Obs observe T X U ≠
        unresolvedPairs C A Obs observe S X U := by
    intro heq
    apply hnotT
    rw [heq]
    exact hmemS
  exact Finset.ssubset_iff_subset_ne.mpr ⟨hsub, hne⟩

/-- A newly accessible protected separator supplies exactly the strict descent
    witness needed by the Lyapunov theorem. -/
theorem new_separator_strictly_decreases
    {S T : Stage C} (hST : Extends C S T)
    {X Y : C.Obj} (U : Finset (A.State X))
    {x y : A.State X} (hx : x ∈ U) (hy : y ∈ U)
    (f : C.Hom X Y)
    (hold : BehEqAt C A Obs observe S X x y)
    (hnew : T.allow f)
    (hsep : observe Y (A.map f x) ≠ observe Y (A.map f y)) :
    potential C A Obs observe T X U < potential C A Obs observe S X U := by
  have hfull : ¬ BehEq C A Obs observe X x y := by
    intro h
    exact hsep (h Y f)
  have hsplit : ¬ BehEqAt C A Obs observe T X x y := by
    intro h
    exact hsep (h Y f hnew)
  exact potential_strict_decrease C A Obs observe hST X U hx hy hold hfull hsplit

/-- Zero potential is exactly completion on the declared carrier U: every pair
    from U currently merged by the stage is already fully behaviourally
    equivalent. -/
theorem potential_eq_zero_iff_complete_on
    (S : Stage C) (X : C.Obj) (U : Finset (A.State X)) :
    potential C A Obs observe S X U = 0 ↔
      ∀ x ∈ U, ∀ y ∈ U,
        BehEqAt C A Obs observe S X x y →
          BehEq C A Obs observe X x y := by
  classical
  constructor
  · intro hzero x hx y hy hstage
    by_cases hfull : BehEq C A Obs observe X x y
    · exact hfull
    · have hmem :
          (x, y) ∈ unresolvedPairs C A Obs observe S X U := by
        simp [unresolvedPairs, hx, hy, hstage, hfull]
      have hempty :
          unresolvedPairs C A Obs observe S X U = ∅ := by
        exact Finset.card_eq_zero.mp hzero
      rw [hempty] at hmem
      simp at hmem
  · intro hcomplete
    apply Finset.card_eq_zero.mpr
    apply Finset.eq_empty_iff_forall_not_mem.mpr
    intro p hp
    have hp' := hp
    simp [unresolvedPairs] at hp'
    exact hp'.2.2 (hcomplete p.1 hp'.1.1 p.2 hp'.1.2 hp'.2.1)

/-- If U contains every state at X, zero potential means exact agreement
    between current and full behavioural identity at X. -/
theorem potential_eq_zero_iff_exact
    (S : Stage C) (X : C.Obj) (U : Finset (A.State X))
    (hcover : ∀ x : A.State X, x ∈ U) :
    potential C A Obs observe S X U = 0 ↔
      ∀ x y : A.State X,
        (BehEqAt C A Obs observe S X x y ↔
          BehEq C A Obs observe X x y) := by
  constructor
  · intro hzero x y
    constructor
    · intro hstage
      exact (potential_eq_zero_iff_complete_on C A Obs observe S X U).mp
        hzero x (hcover x) y (hcover y) hstage
    · exact full_implies_stage C A Obs observe S
  · intro hexact
    apply (potential_eq_zero_iff_complete_on C A Obs observe S X U).mpr
    intro x hx y hy hstage
    exact (hexact x y).mp hstage

/-- The strict developmental relation induced by the potential. -/
def StrictDevelopment
    (X : C.Obj) (U : Finset (A.State X)) (T S : Stage C) : Prop :=
  potential C A Obs observe T X U < potential C A Obs observe S X U

/-- Strict developmental descent is well-founded on every declared finite
    carrier: no infinite sequence of certified strict decreases exists. -/
theorem strictDevelopment_wellFounded
    (X : C.Obj) (U : Finset (A.State X)) :
    WellFounded (StrictDevelopment C A Obs observe X U) := by
  unfold StrictDevelopment
  exact measure_wf (fun S : Stage C => potential C A Obs observe S X U)

end DevelopmentalLyapunov

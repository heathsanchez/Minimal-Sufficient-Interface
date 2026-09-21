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

/-- The unresolved consequential pairs at one object and developmental stage:
    pairs still merged by the current stage but separable by some ambient
    protected continuation.  This is the finite "hidden residual" set. -/
noncomputable def unresolvedPairs
    (S : Stage C) (X : C.Obj) [Fintype (A.State X)] :
    Finset (A.State X × A.State X) := by
  classical
  exact Finset.univ.filter (fun p =>
    BehEqAt C A Obs observe S X p.1 p.2 ∧
      ¬ BehEq C A Obs observe X p.1 p.2)

/-- Developmental Lyapunov potential: the number of ordered state pairs that
    the current interface still merges although the full protected future can
    distinguish them.

    It is representation-free at the semantic level: it counts only the
    current and ambient behavioural relations, not syntax or proof history. -/
noncomputable def potential
    (S : Stage C) (X : C.Obj) [Fintype (A.State X)] : Nat :=
  (unresolvedPairs C A Obs observe S X).card

/-- Extending the accessible continuation family can only remove unresolved
    consequential pairs. -/
theorem unresolvedPairs_mono
    {S T : Stage C} (hST : Extends C S T)
    (X : C.Obj) [Fintype (A.State X)] :
    unresolvedPairs C A Obs observe T X ⊆
      unresolvedPairs C A Obs observe S X := by
  classical
  intro p hp
  simp [unresolvedPairs] at hp ⊢
  exact ⟨extension_refines C A Obs observe hST X p.1 p.2 hp.1, hp.2⟩

/-- Lyapunov monotonicity: lawful capability growth never increases the number
    of still-hidden consequential distinctions. -/
theorem potential_nonincreasing
    {S T : Stage C} (hST : Extends C S T)
    (X : C.Obj) [Fintype (A.State X)] :
    potential C A Obs observe T X ≤ potential C A Obs observe S X := by
  classical
  exact Finset.card_le_card (unresolvedPairs_mono C A Obs observe hST X)

/-- If an extension actually splits one old behavioural class along a pair
    that is separable in the full ambient future, the Lyapunov potential drops
    strictly. -/
theorem potential_strict_decrease
    {S T : Stage C} (hST : Extends C S T)
    (X : C.Obj) [Fintype (A.State X)]
    {x y : A.State X}
    (hold : BehEqAt C A Obs observe S X x y)
    (hfull : ¬ BehEq C A Obs observe X x y)
    (hsplit : ¬ BehEqAt C A Obs observe T X x y) :
    potential C A Obs observe T X < potential C A Obs observe S X := by
  classical
  apply Finset.card_lt_card
  have hsub :
      unresolvedPairs C A Obs observe T X ⊆
        unresolvedPairs C A Obs observe S X :=
    unresolvedPairs_mono C A Obs observe hST X
  have hmemS :
      (x, y) ∈ unresolvedPairs C A Obs observe S X := by
    simp [unresolvedPairs, hold, hfull]
  have hnotT :
      (x, y) ∉ unresolvedPairs C A Obs observe T X := by
    simp [unresolvedPairs, hsplit]
  exact Finset.ssubset_iff_subset_ne.mpr ⟨hsub, by
    intro heq
    have : (x, y) ∈ unresolvedPairs C A Obs observe T X := by
      rw [heq]
      exact hmemS
    exact hnotT this⟩

/-- A newly accessible protected separator supplies exactly the strict descent
    witness needed by the Lyapunov theorem. -/
theorem new_separator_strictly_decreases
    {S T : Stage C} (hST : Extends C S T)
    {X Y : C.Obj} [Fintype (A.State X)]
    {x y : A.State X} (f : C.Hom X Y)
    (hold : BehEqAt C A Obs observe S X x y)
    (hnew : T.allow f)
    (hsep : observe Y (A.map f x) ≠ observe Y (A.map f y)) :
    potential C A Obs observe T X < potential C A Obs observe S X := by
  have hfull : ¬ BehEq C A Obs observe X x y := by
    intro h
    exact hsep (h Y f)
  have hsplit : ¬ BehEqAt C A Obs observe T X x y := by
    intro h
    exact hsep (h Y f hnew)
  exact potential_strict_decrease C A Obs observe hST X hold hfull hsplit

/-- Zero potential is exactly completion at this object: every pair currently
    merged by the stage is already fully behaviourally equivalent. -/
theorem potential_eq_zero_iff_complete
    (S : Stage C) (X : C.Obj) [Fintype (A.State X)] :
    potential C A Obs observe S X = 0 ↔
      ∀ x y : A.State X,
        BehEqAt C A Obs observe S X x y →
          BehEq C A Obs observe X x y := by
  classical
  constructor
  · intro hzero x y hstage
    by_contra hfull
    have hmem :
        (x, y) ∈ unresolvedPairs C A Obs observe S X := by
      simp [unresolvedPairs, hstage, hfull]
    have hempty :
        unresolvedPairs C A Obs observe S X = ∅ := by
      apply Finset.card_eq_zero.mp
      exact hzero
    rw [hempty] at hmem
    simp at hmem
  · intro hcomplete
    apply Finset.card_eq_zero.mpr
    apply Finset.eq_empty_iff_forall_not_mem.mpr
    intro p hp
    have hp' := hp
    simp [unresolvedPairs] at hp'
    exact hp'.2 (hcomplete p.1 p.2 hp'.1)

/-- Zero potential therefore means exact agreement between current and full
    behavioural identity at the object. -/
theorem potential_eq_zero_iff_exact
    (S : Stage C) (X : C.Obj) [Fintype (A.State X)] :
    potential C A Obs observe S X = 0 ↔
      ∀ x y : A.State X,
        (BehEqAt C A Obs observe S X x y ↔
          BehEq C A Obs observe X x y) := by
  constructor
  · intro hzero x y
    constructor
    · exact (potential_eq_zero_iff_complete C A Obs observe S X).mp hzero x y
    · exact full_implies_stage C A Obs observe S
  · intro hexact
    apply (potential_eq_zero_iff_complete C A Obs observe S X).mpr
    intro x y hstage
    exact (hexact x y).mp hstage

/-- The strict developmental relation induced by the potential. -/
def StrictDevelopment
    (X : C.Obj) [Fintype (A.State X)] (T S : Stage C) : Prop :=
  potential C A Obs observe T X < potential C A Obs observe S X

/-- Strict developmental descent is well-founded on every finite state object:
    no infinite sequence of certified strict decreases exists. -/
theorem strictDevelopment_wellFounded
    (X : C.Obj) [Fintype (A.State X)] :
    WellFounded (StrictDevelopment C A Obs observe X) := by
  unfold StrictDevelopment
  exact measure_wf (potential C A Obs observe · X)

end DevelopmentalLyapunov

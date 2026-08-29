import Std
import IdentityCompositionConsequence

universe u v

namespace ResourceIndexedConsequence

variable {C : Type u}

/-- A language is represented abstractly by the least cost at which each
    consequence can be realized. -/
structure CostModel (C : Type u) where
  cost : C → Nat

/-- Consequences reachable within budget `B`. -/
def ReachableAt (L : CostModel C) (B : Nat) (c : C) : Prop :=
  L.cost c ≤ B

/-- Promotion/reorganization makes a consequence strictly cheaper. -/
def CheaperIn (L L' : CostModel C) (c : C) : Prop :=
  L'.cost c < L.cost c

/-- If a reorganization moves a consequence from above the budget to at or
    below it, bounded capability strictly gains that consequence. -/
theorem crosses_budget_becomes_reachable
    (L L' : CostModel C) (B : Nat) (c : C)
    (hcold : B < L.cost c)
    (hwarm : L'.cost c ≤ B) :
    ¬ ReachableAt L B c ∧ ReachableAt L' B c := by
  constructor
  · intro h
    exact Nat.not_lt_of_ge h hcold
  · exact hwarm

/-- Any strict cost improvement creates some budget horizon at which the
    consequence changes from unreachable to reachable. -/
theorem cheaper_creates_phase_horizon
    (L L' : CostModel C) (c : C)
    (h : CheaperIn L L' c) :
    ∃ B, ¬ ReachableAt L B c ∧ ReachableAt L' B c := by
  refine ⟨L'.cost c, ?_⟩
  exact crosses_budget_becomes_reachable L L' (L'.cost c) c h (Nat.le_refl _)

/-- Semantic conservativity needs no separate proposition here: `L` and `L'`
    are cost assignments on the same consequence `c`. Promotion changes only
    its resource coordinate. -/
theorem conservative_promotion_can_change_bounded_frontier
    (L L' : CostModel C) (c : C)
    (h : CheaperIn L L' c) :
    ∃ B, ¬ ReachableAt L B c ∧ ReachableAt L' B c := by
  exact cheaper_creates_phase_horizon L L' c h

open IdentityCompositionConsequence

variable {M : Type u} {X : Type v}

/-- A resource grading on the same executable calculus.  Composition has
    additive cost, so resource reachability and compositional reachability are
    coupled without changing denotation. -/
structure CompositionalCostModel (K : Calculus M X) where
  cost : M → Nat
  comp_cost : ∀ f g, cost (K.comp f g) = cost f + cost g

/-- A transformation is executable inside the resource horizon. -/
def TransformReachableAt {K : Calculus M X}
    (L : CompositionalCostModel K) (B : Nat) (f : M) : Prop :=
  L.cost f ≤ B

/-- Composition consumes at most the sum of the two certified budgets. -/
theorem composition_reachable_at_sum
    (K : Calculus M X) (L : CompositionalCostModel K)
    (f g : M) (Bf Bg : Nat)
    (hf : TransformReachableAt L Bf f)
    (hg : TransformReachableAt L Bg g) :
    TransformReachableAt L (Bf + Bg) (K.comp f g) := by
  rw [TransformReachableAt, L.comp_cost]
  exact Nat.add_le_add hf hg

/-- If promotion makes one ancestor cheaper while preserving the cost of the
    other component, every one-step composite using that ancestor becomes
    strictly cheaper too.  The transformation and its action are unchanged;
    only its resource coordinate changes. -/
theorem cheaper_ancestor_makes_composite_cheaper
    (K : Calculus M X)
    (L L' : CompositionalCostModel K)
    (seed tail : M)
    (hseed : L'.cost seed < L.cost seed)
    (htail : L'.cost tail = L.cost tail) :
    L'.cost (K.comp seed tail) < L.cost (K.comp seed tail) := by
  rw [L'.comp_cost, L.comp_cost, htail]
  exact Nat.add_lt_add_right hseed (L.cost tail)

/-- Resource-indexed developmental compounding: a conservative promotion of an
    ancestor can create a new bounded phase horizon for a downstream composite.
    No new denotation, observation, or category law is assumed. -/
theorem promoted_ancestor_creates_descendant_phase_horizon
    (K : Calculus M X)
    (L L' : CompositionalCostModel K)
    (seed tail : M)
    (hseed : L'.cost seed < L.cost seed)
    (htail : L'.cost tail = L.cost tail) :
    ∃ B,
      ¬ TransformReachableAt L B (K.comp seed tail) ∧
      TransformReachableAt L' B (K.comp seed tail) := by
  let cold : CostModel M := ⟨L.cost⟩
  let warm : CostModel M := ⟨L'.cost⟩
  have hcomp : CheaperIn cold warm (K.comp seed tail) := by
    exact cheaper_ancestor_makes_composite_cheaper K L L' seed tail hseed htail
  rcases cheaper_creates_phase_horizon cold warm (K.comp seed tail) hcomp with
    ⟨B, hcold, hwarm⟩
  exact ⟨B, hcold, hwarm⟩

end ResourceIndexedConsequence

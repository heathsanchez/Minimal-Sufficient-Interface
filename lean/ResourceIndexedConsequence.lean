import Std

universe u

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

/-- Semantic conservativity at infinity can coexist with a strict bounded
    phase change: the theorem deliberately assumes only cost compression, not
    creation of a new denotation. -/
theorem conservative_promotion_can_change_bounded_frontier
    (L L' : CostModel C) (c : C)
    (sameDenotation : True)
    (h : CheaperIn L L' c) :
    ∃ B, ¬ ReachableAt L B c ∧ ReachableAt L' B c := by
  exact cheaper_creates_phase_horizon L L' c h

end ResourceIndexedConsequence

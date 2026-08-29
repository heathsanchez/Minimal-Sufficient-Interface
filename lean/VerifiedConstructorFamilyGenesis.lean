import Std

universe u v w z

namespace VerifiedConstructorFamilyGenesis

variable {X : Type u} {Family : Type v} {View : Type w} {Y : Type z}

/-- A constructor family is sufficient when equality of the view it exposes forces
    equality of the protected consequence. -/
def FamilySufficient (view : Family → X → View) (target : X → Y) (f : Family) : Prop :=
  ∀ x y : X, view f x = view f y → target x = target y

/-- A verifier-generated residual rejects a constructor family when that family's
    view merges a pair whose protected consequences disagree. -/
def ResidualRejects (view : Family → X → View) (target : X → Y) (f : Family) : Prop :=
  ∃ x y : X, view f x = view f y ∧ target x ≠ target y

/-- Failure of family sufficiency is exactly witnessed by a protected residual. -/
theorem not_sufficient_iff_residual_rejects
    (view : Family → X → View) (target : X → Y) (f : Family) :
    ¬ FamilySufficient view target f ↔ ResidualRejects view target f := by
  constructor
  · intro hnot
    apply Classical.byContradiction
    intro hnone
    apply hnot
    intro x y hview
    apply Classical.byContradiction
    intro htarget
    exact hnone ⟨x, y, hview, htarget⟩
  · intro hreject hs
    rcases hreject with ⟨x, y, hview, htarget⟩
    exact htarget (hs x y hview)

/-- A residual-selected winner is sufficient, while every strictly cheaper family
    in the supplied executable portfolio has an explicit verifier residual. -/
def ResidualSelectedWinner
    (rank : Family → Nat)
    (view : Family → X → View)
    (target : X → Y)
    (winner : Family) : Prop :=
  FamilySufficient view target winner ∧
  ∀ f : Family, rank f < rank winner → ResidualRejects view target f

/-- Residual selection really does certify least adequate structural complexity:
    every cheaper family is insufficient. -/
theorem winner_is_least_sufficient_in_rank
    (rank : Family → Nat)
    (view : Family → X → View)
    (target : X → Y)
    (winner : Family)
    (hw : ResidualSelectedWinner rank view target winner) :
    FamilySufficient view target winner ∧
    ∀ f : Family, rank f < rank winner → ¬ FamilySufficient view target f := by
  constructor
  · exact hw.1
  · intro f hcheap
    exact (not_sufficient_iff_residual_rejects view target f).2 (hw.2 f hcheap)

/-- Exact lower-family ablation: replacing a selected winner by any cheaper family
    restores a concrete protected collision. -/
theorem cheaper_family_ablation_restores_residual
    (rank : Family → Nat)
    (view : Family → X → View)
    (target : X → Y)
    (winner old : Family)
    (hw : ResidualSelectedWinner rank view target winner)
    (hold : rank old < rank winner) :
    ∃ x y : X, view old x = view old y ∧ target x ≠ target y := by
  exact hw.2 old hold

/-- If two worlds make different families the first residually adequate choices,
    the selected constructor kind is consequence-dependent rather than fixed by rank
    alone. -/
theorem different_verified_winners_require_different_residual_profiles
    (rank : Family → Nat)
    (view₁ view₂ : Family → X → View)
    (target₁ target₂ : X → Y)
    (f₁ f₂ : Family)
    (h₁ : ResidualSelectedWinner rank view₁ target₁ f₁)
    (h₂ : ResidualSelectedWinner rank view₂ target₂ f₂)
    (hrank : rank f₁ < rank f₂) :
    FamilySufficient view₁ target₁ f₁ ∧ ResidualRejects view₂ target₂ f₁ := by
  exact ⟨h₁.1, h₂.2 f₁ hrank⟩

/-- The exact theorem boundary: residuals can force the least adequate family within
    a supplied ranked portfolio. They do not, by themselves, construct families
    outside that portfolio. -/
theorem supplied_portfolio_family_is_residually_forced
    (rank : Family → Nat)
    (view : Family → X → View)
    (target : X → Y)
    (winner : Family)
    (hw : ResidualSelectedWinner rank view target winner) :
    FamilySufficient view target winner := by
  exact hw.1

end VerifiedConstructorFamilyGenesis

import Std

universe u v w

namespace FactorizationSufficiency

variable {X : Type u} {R : Type v} {Y : Type w}

/-- A consequence is constant on every fibre of a representation. -/
def RespectsFibres (q : X → R) (c : X → Y) : Prop :=
  ∀ x y, q x = q y → c x = c y

/-- A consequence factors through a representation when it can be computed
    entirely from the represented state. -/
def FactorsThrough (q : X → R) (c : X → Y) : Prop :=
  ∃ cbar : R → Y, ∀ x, cbar (q x) = c x

/-- Every actual factorization respects the representation fibres. -/
theorem factorsThrough_respectsFibres (q : X → R) (c : X → Y)
    (h : FactorsThrough q c) : RespectsFibres q c := by
  rcases h with ⟨cbar, hcbar⟩
  intro x y hq
  calc
    c x = cbar (q x) := (hcbar x).symm
    _ = cbar (q y) := congrArg cbar hq
    _ = c y := hcbar y

/-- For a surjective representation, fibre-respect is also sufficient for
    factorization. This is the exact bridge between kernel inclusion and
    executable sufficiency. -/
theorem respectsFibres_factorsThrough_of_surjective
    (q : X → R) (c : X → Y)
    (hq : Function.Surjective q)
    (h : RespectsFibres q c) : FactorsThrough q c := by
  classical
  choose rep hrep using hq
  refine ⟨fun r => c (rep r), ?_⟩
  intro x
  exact h (rep (q x)) x (hrep (q x))

/-- Exact factorization criterion for surjective representations. -/
theorem factorsThrough_iff_respectsFibres
    (q : X → R) (c : X → Y)
    (hq : Function.Surjective q) :
    FactorsThrough q c ↔ RespectsFibres q c := by
  constructor
  · exact factorsThrough_respectsFibres q c
  · exact respectsFibres_factorsThrough_of_surjective q c hq

/-- A representation is sufficient for a family of protected consequences
    exactly when every member factors through it. -/
def SufficientFor {I : Type*} (q : X → R) (C : I → X → Y) : Prop :=
  ∀ i, FactorsThrough q (C i)

/-- Under surjectivity, family sufficiency is exactly simultaneous fibre
    respect. -/
theorem sufficientFor_iff_all_respect {I : Type*}
    (q : X → R) (C : I → X → Y)
    (hq : Function.Surjective q) :
    SufficientFor q C ↔ ∀ i, RespectsFibres q (C i) := by
  constructor
  · intro h i
    exact factorsThrough_respectsFibres q (C i) (h i)
  · intro h i
    exact respectsFibres_factorsThrough_of_surjective q (C i) hq (h i)

end FactorizationSufficiency

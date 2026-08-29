import Std
import SeparationRelationAblation
import IdentityCompositionConsequence
import ResourceIndexedConsequence

namespace MinimalSufficientInterface.BottomUpCalculusDerivation

open MinimalSufficientInterface.SeparationRelationAblation
open MinimalSufficientInterface.IdentityCompositionConsequence
open ResourceIndexedConsequence

universe u

/-- Layer 0: lawful separation already derives a genuine equivalence relation. -/
theorem lawful_separation_derives_equivalence
    {X : Type u} (S : LawfulSeparation X) :
    (∀ x, Same S.toSeparation x x) ∧
    (∀ {x y}, Same S.toSeparation x y → Same S.toSeparation y x) ∧
    (∀ {x y z}, Same S.toSeparation x y → Same S.toSeparation y z → Same S.toSeparation x z) := by
  exact ⟨lawful_same_refl S, lawful_same_symm S, lawful_same_trans S⟩

/-- Layer 0 is strictly weaker than dynamics: the same separation structure can
come from incompatible actions. -/
theorem separation_does_not_determine_dynamics :
    ∃ (A B : Action Bool Bool),
      (∀ x y, (inducedSep A).sep x y ↔ (inducedSep B).sep x y) ∧
      A.act true false ≠ B.act true false := by
  exact ⟨a1, a2, same_separation_incompatible_actions⟩

/-- Layer 1 is strictly stronger: even lawful static identity does not force
arbitrary dynamics to respect that identity. -/
theorem dynamics_needs_identity_respect :
    ∃ (S : LawfulSeparation (Fin 3)) (A : Action Bool (Fin 3)) (x y : Fin 3),
      Same S.toSeparation x y ∧
      ¬ Same S.toSeparation (A.act true x) (A.act true y) := by
  exact ⟨twoClassSeparation, badDynamic, 0, 1,
    lawful_static_identity_does_not_force_dynamic_invariance.1,
    lawful_static_identity_does_not_force_dynamic_invariance.2⟩

/-- Layer 2 is strictly stronger again: an action family need not contain its
own sequential composites. -/
theorem dynamics_does_not_determine_composition :
    ∃ (A : Action Bool (Fin 3)), ¬ HasComposition A := by
  exact ⟨nonClosedAction, action_does_not_imply_compositional_closure⟩

/-- Once identity action and compositional action are supplied, the bottom-up
layers compile exactly into the existing minimal calculus. No associativity or
unit equations for `comp` are added. -/
structure DynamicClosure (M X : Type u) where
  one : M
  comp : M → M → M
  act : M → X → X
  one_act : ∀ x, act one x = x
  comp_act : ∀ f g x, act (comp f g) x = act f (act g x)

def DynamicClosure.toCalculus {M X : Type u} (D : DynamicClosure M X) : Calculus M X where
  one := D.one
  comp := D.comp
  act := D.act
  one_act := D.one_act
  comp_act := D.comp_act

/-- The old consequence calculus is therefore not an extra semantic layer: it
is the compiled form of identity-pointing plus compositional dynamics. -/
theorem compiled_calculus_recovers_observation_and_invariance
    {M X Y : Type u} (D : DynamicClosure M X)
    (observe : X → Y) (S : Stage D.toCalculus) {x y : X}
    (h : SameAt D.toCalculus observe S x y) :
    observe x = observe y ∧
    ∀ {g : M}, S.allows g →
      SameAt D.toCalculus observe S (D.act g x) (D.act g y) := by
  constructor
  · exact sameAt_observation D.toCalculus observe S h
  · intro g hg
    exact sameAt_invariant D.toCalculus observe S h hg

/-- The same compiled calculus recovers the developmental split/refinement law. -/
theorem compiled_calculus_recovers_development
    {M X Y : Type u} (D : DynamicClosure M X)
    (observe : X → Y) (S : Stage D.toCalculus) (seed : M) {x y : X}
    (hOld : SameAt D.toCalculus observe S x y)
    (hSep : observe (D.act seed x) ≠ observe (D.act seed y)) :
    SameAt D.toCalculus observe S x y ∧
    ¬ SameAt D.toCalculus observe (adjoin D.toCalculus S seed) x y := by
  exact verified_compositional_portal D.toCalculus observe S seed hOld hSep

/-- Least generated extension is also inherited unchanged from the compiled
calculus. -/
theorem compiled_calculus_recovers_least_extension
    {M X : Type u} (D : DynamicClosure M X)
    (S T : Stage D.toCalculus) (seed : M)
    (hST : Extends D.toCalculus S T) (hSeed : T.allows seed) :
    Extends D.toCalculus (adjoin D.toCalculus S seed) T := by
  exact adjoin_least D.toCalculus S T seed hST hSeed

/-- Resource-graded promotion is a grading on this same compiled calculus, not
another semantic primitive. -/
theorem compiled_calculus_recovers_resource_phase_change
    {M X : Type u} (D : DynamicClosure M X)
    (L L' : CompositionalCostModel D.toCalculus)
    (seed tail : M)
    (hseed : L'.cost seed < L.cost seed)
    (htail : L'.cost tail = L.cost tail) :
    ∃ B,
      ¬ TransformReachableAt L B (D.comp seed tail) ∧
      TransformReachableAt L' B (D.comp seed tail) := by
  exact promoted_ancestor_creates_descendant_phase_horizon
    D.toCalculus L L' seed tail hseed htail

/-- One-shot scientific decision: the verified hierarchy is strict below the
compiled calculus, while the existing developmental and resource theorems are
recovered once the minimal missing dynamic/compositional structure is added. -/
theorem bottom_up_foundation_decision :
    (∃ (A B : Action Bool Bool),
      (∀ x y, (inducedSep A).sep x y ↔ (inducedSep B).sep x y) ∧
      A.act true false ≠ B.act true false) ∧
    (∃ (S : LawfulSeparation (Fin 3)) (A : Action Bool (Fin 3)) (x y : Fin 3),
      Same S.toSeparation x y ∧
      ¬ Same S.toSeparation (A.act true x) (A.act true y)) ∧
    (∃ (A : Action Bool (Fin 3)), ¬ HasComposition A) := by
  exact ⟨separation_does_not_determine_dynamics,
    dynamics_needs_identity_respect,
    dynamics_does_not_determine_composition⟩

end MinimalSufficientInterface.BottomUpCalculusDerivation

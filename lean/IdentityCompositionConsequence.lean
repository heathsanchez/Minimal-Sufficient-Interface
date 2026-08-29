import Std

universe u v w

/-!
Compression experiment: can consequential identity, separation/union, compositional
closure, developmental refinement, and least generated extension be recovered from
one small calculus rather than treated as separate laws?

This file deliberately imports only `Std`.
-/

namespace IdentityCompositionConsequence

/-- Minimal compositional substrate: a monoid of executable transformations acting
on states. -/
structure Calculus (M : Type u) (X : Type v) where
  one : M
  comp : M → M → M
  act : M → X → X
  one_comp : ∀ f, comp one f = f
  comp_one : ∀ f, comp f one = f
  comp_assoc : ∀ f g h, comp (comp f g) h = comp f (comp g h)
  one_act : ∀ x, act one x = x
  comp_act : ∀ f g x, act (comp f g) x = act f (act g x)

variable {M : Type u} {X : Type v} {Y : Type w}
variable (K : Calculus M X) (observe : X → Y)

/-- A stage is the currently licensed compositional language. -/
structure Stage where
  allows : M → Prop
  one_mem : allows K.one
  comp_mem : ∀ f g, allows f → allows g → allows (K.comp f g)

/-- Identity at a stage is exactly equality under all currently licensed
compositional consequences. -/
def SameAt (S : Stage K) (x y : X) : Prop :=
  ∀ f, S.allows f → observe (K.act f x) = observe (K.act f y)

/-- A relation is compatible with the immediate protected consequence. -/
def ObsCompatible (R : X → X → Prop) : Prop :=
  ∀ x y, R x y → observe x = observe y

/-- A relation is invariant under every transformation licensed by the stage. -/
def StageInvariant (S : Stage K) (R : X → X → Prop) : Prop :=
  ∀ f, S.allows f → ∀ x y, R x y → R (K.act f x) (K.act f y)

/-- UNION / maximal forgetting: stage identity is the greatest relation that is
both observation-compatible and invariant under every licensed composition. -/
theorem sameAt_greatest_invariant
    (S : Stage K) (R : X → X → Prop)
    (hObs : ObsCompatible observe R)
    (hInv : StageInvariant K S R) :
    ∀ x y, R x y → SameAt K observe S x y := by
  intro x y hxy f hf
  exact hObs (K.act f x) (K.act f y) (hInv f hf x y hxy)

/-- Immediate observation is among the consequences because identity is licensed. -/
theorem sameAt_observation
    (S : Stage K) {x y : X}
    (h : SameAt K observe S x y) : observe x = observe y := by
  simpa [K.one_act] using h K.one S.one_mem

/-- Stage identity is preserved by every licensed transformation. -/
theorem sameAt_invariant
    (S : Stage K) : StageInvariant K S (SameAt K observe S) := by
  intro g hg x y hxy f hf
  have h := hxy (K.comp f g) (S.comp_mem f g hf hg)
  simpa [K.comp_act] using h

/-- Extension of the licensed compositional language can only refine identity. -/
def Extends (S T : Stage K) : Prop := ∀ f, S.allows f → T.allows f

/-- SEPARATION law under language growth. -/
theorem extension_refines_identity
    (S T : Stage K) (hST : Extends K S T) :
    ∀ x y, SameAt K observe T x y → SameAt K observe S x y := by
  intro x y hT f hf
  exact hT f (hST f hf)

/-- A newly licensed morphism that distinguishes a previously united pair forces
strict separation at the extended stage. -/
theorem new_consequence_forces_split
    (S T : Stage K) (hST : Extends K S T)
    (f : M) (hfT : T.allows f)
    {x y : X}
    (hOld : SameAt K observe S x y)
    (hSep : observe (K.act f x) ≠ observe (K.act f y)) :
    ¬ SameAt K observe T x y := by
  intro hNew
  exact hSep (hNew f hfT)

/-- Free generated extension of a stage by one verified new transformation. -/
inductive Generated (S : Stage K) (seed : M) : M → Prop
  | old {f} : S.allows f → Generated S seed f
  | seed : Generated S seed seed
  | one : Generated S seed K.one
  | comp {f g} : Generated S seed f → Generated S seed g →
      Generated S seed (K.comp f g)

/-- The generated extension is itself a stage. -/
def adjoin (S : Stage K) (seed : M) : Stage K where
  allows := Generated K S seed
  one_mem := Generated.one
  comp_mem := by
    intro f g hf hg
    exact Generated.comp hf hg

/-- The old stage embeds in the generated stage. -/
theorem old_extends_to_adjoin (S : Stage K) (seed : M) :
    Extends K S (adjoin K S seed) := by
  intro f hf
  exact Generated.old hf

/-- The new verified transformation is available after adjoining. -/
theorem seed_mem_adjoin (S : Stage K) (seed : M) :
    (adjoin K S seed).allows seed := Generated.seed

/-- LEAST EXTENSION law: `adjoin` is the least composition-closed stage containing
both the old stage and the new verified transformation. -/
theorem adjoin_least
    (S T : Stage K) (seed : M)
    (hST : Extends K S T)
    (hseed : T.allows seed) :
    Extends K (adjoin K S seed) T := by
  intro f hf
  induction hf with
  | old hold => exact hST _ hold
  | seed => exact hseed
  | one => exact T.one_mem
  | comp hf hg ihf ihg => exact T.comp_mem _ _ ihf ihg

/-- End-to-end developmental portal: a pair can be united under the old
compositional regime, a verified seed can separate it, and the least lawful
composition-closed extension necessarily changes its identity. -/
theorem verified_compositional_portal
    (S : Stage K) (seed : M) {x y : X}
    (hOld : SameAt K observe S x y)
    (hSep : observe (K.act seed x) ≠ observe (K.act seed y)) :
    SameAt K observe S x y ∧
    ¬ SameAt K observe (adjoin K S seed) x y ∧
    (∀ T : Stage K,
      Extends K S T → T.allows seed → Extends K (adjoin K S seed) T) := by
  refine ⟨hOld, ?_, ?_⟩
  · exact new_consequence_forces_split K observe S (adjoin K S seed)
      (old_extends_to_adjoin K S seed) seed (seed_mem_adjoin K S seed) hOld hSep
  · intro T hST hseed
    exact adjoin_least K S T seed hST hseed

/-- Static fixed point relative to a stage: no relation may unite more states while
remaining both observation-compatible and invariant under the licensed calculus. -/
def StableRelation (S : Stage K) (R : X → X → Prop) : Prop :=
  ObsCompatible observe R ∧ StageInvariant K S R ∧
  ∀ Q : X → X → Prop,
    ObsCompatible observe Q → StageInvariant K S Q →
    ∀ x y, Q x y → R x y

/-- Consequential identity itself is the canonical maximal stable relation. -/
theorem sameAt_is_stable (S : Stage K) :
    StableRelation K observe S (SameAt K observe S) := by
  refine ⟨?_, sameAt_invariant K observe S, ?_⟩
  · intro x y h
    exact sameAt_observation K observe S h
  · intro Q hObs hInv x y hxy
    exact sameAt_greatest_invariant K observe S Q hObs hInv x y hxy

end IdentityCompositionConsequence

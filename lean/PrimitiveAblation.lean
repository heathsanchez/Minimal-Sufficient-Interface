import Std

namespace MinimalSufficientInterface.PrimitiveAblation

universe u v w

/-- Bare consequence substrate. No identity transformation, no composition,
and no closure laws are assumed. -/
structure Bare (M : Type u) (X : Type v) where
  act : M → X → X

variable {M : Type u} {X : Type v} {Y : Type w}

/-- A consequence language is only a predicate saying which transformations
are currently licensed. -/
structure Language (M : Type u) where
  allows : M → Prop

/-- Inclusion of consequence languages. -/
def Extends (S T : Language M) : Prop :=
  ∀ f, S.allows f → T.allows f

/-- Consequential indistinguishability requires no algebraic structure. -/
def SameAt (K : Bare M X) (observe : X → Y) (S : Language M)
    (x y : X) : Prop :=
  ∀ f, S.allows f → observe (K.act f x) = observe (K.act f y)

/-- NOTHING: no consequence is licensed. -/
def nothing : Language M where
  allows := fun _ => False

/-- ALL: every available consequence is licensed. -/
def all : Language M where
  allows := fun _ => True

/-- With no licensed distinctions, every pair collapses together. -/
theorem nothing_collapses_all
    (K : Bare M X) (observe : X → Y) (x y : X) :
    SameAt K observe (nothing : Language M) x y := by
  intro f hf
  contradiction

/-- Licensing more consequences can only refine consequential identity.
This needs neither identity nor composition. -/
theorem bare_extension_refines
    (K : Bare M X) (observe : X → Y)
    (S T : Language M) (hST : Extends S T) {x y : X}
    (hT : SameAt K observe T x y) :
    SameAt K observe S x y := by
  intro f hf
  exact hT f (hST f hf)

/-- A single licensed consequential difference forces a split.
This also needs neither identity nor composition. -/
theorem bare_consequence_forces_split
    (K : Bare M X) (observe : X → Y)
    (S : Language M) (f : M) (hf : S.allows f) {x y : X}
    (hSep : observe (K.act f x) ≠ observe (K.act f y)) :
    ¬ SameAt K observe S x y := by
  intro h
  exact hSep (h f hf)

/-- Converse: every strict identity refinement has a newly licensed separating
consequence. Again no identity transformation or composition is required. -/
theorem bare_strict_refinement_has_new_separator
    (K : Bare M X) (observe : X → Y)
    (S T : Language M) {x y : X}
    (hOld : SameAt K observe S x y)
    (hNew : ¬ SameAt K observe T x y) :
    ∃ f, T.allows f ∧ ¬ S.allows f ∧
      observe (K.act f x) ≠ observe (K.act f y) := by
  classical
  exact Classical.byContradiction (fun hNoWitness =>
    hNew (fun f hfT =>
      Classical.byContradiction (fun hSep =>
        hNoWitness ⟨f, hfT,
          (fun hfS => hSep (hOld f hfS)),
          hSep⟩)))

/-- Countermodel: without a licensed identity-like consequence, consequential
sameness need not imply equality of the raw observation. -/
theorem identity_witness_is_not_derivable_from_bare :
    ∃ (K : Bare Bool Bool) (observe : Bool → Bool) (S : Language Bool)
      (x y : Bool),
      SameAt K observe S x y ∧ observe x ≠ observe y := by
  let K : Bare Bool Bool := ⟨fun _ z => z⟩
  let observe : Bool → Bool := fun z => z
  let S : Language Bool := nothing
  refine ⟨K, observe, S, false, true, ?_, by decide⟩
  exact nothing_collapses_all K observe false true

/-- Pointing the language with a transformation that acts identically is exactly
what is needed to recover the protected observation from consequential sameness. -/
structure Pointed (M : Type u) (X : Type v) extends Bare M X where
  one : M
  one_act : ∀ x, act one x = x

structure PointedLanguage (K : Pointed M X) extends Language M where
  one_mem : allows K.one

 theorem pointed_same_implies_observation
    (K : Pointed M X) (observe : X → Y)
    (S : PointedLanguage K) {x y : X}
    (h : SameAt K.toBare observe S.toLanguage x y) :
    observe x = observe y := by
  simpa [K.one_act] using h K.one S.one_mem

/-- Composition is a separate primitive layer. -/
structure Composable (M : Type u) (X : Type v) extends Bare M X where
  comp : M → M → M
  comp_act : ∀ f g x, act (comp f g) x = act f (act g x)

structure ClosedLanguage (K : Composable M X) extends Language M where
  comp_mem : ∀ {f g}, allows f → allows g → allows (K.comp f g)

/-- Composition + closure, and only those ingredients, yield invariance of
consequential identity under licensed transformations. -/
theorem compositional_same_is_invariant
    (K : Composable M X) (observe : X → Y)
    (S : ClosedLanguage K) {x y : X}
    (h : SameAt K.toBare observe S.toLanguage x y)
    {g : M} (hg : S.allows g) :
    SameAt K.toBare observe S.toLanguage (K.act g x) (K.act g y) := by
  intro f hf
  rw [← K.comp_act, ← K.comp_act]
  exact h (K.comp f g) (S.comp_mem hf hg)

/-- Finite countermodel showing that bare consequence semantics alone does not
force invariance under sequential action. Two individually invisible actions
can compose into a visible distinction. -/
structure Cell where
  out : Bool
  armed : Bool
  payload : Bool
  deriving DecidableEq

def fAct (z : Cell) : Cell :=
  if z.armed then { z with out := z.payload } else { z with out := false }

def gAct (z : Cell) : Cell :=
  { z with out := false, armed := true }

def fgBare : Bare Bool Cell where
  act := fun m z => if m then gAct z else fAct z

 theorem bare_invariance_can_fail :
    ∃ (S : Language Bool) (x y : Cell) (g : Bool),
      S.allows g ∧
      SameAt fgBare Cell.out S x y ∧
      ¬ SameAt fgBare Cell.out S (fgBare.act g x) (fgBare.act g y) := by
  let S : Language Bool := all
  let x : Cell := ⟨false, false, false⟩
  let y : Cell := ⟨false, false, true⟩
  refine ⟨S, x, y, true, trivial, ?_, ?_⟩
  · intro m hm
    cases m <;> decide
  · intro h
    have hfalse := h false trivial
    simp [fgBare, gAct, fAct, x, y] at hfalse

/-- The dependency result: the split/refinement core lives strictly below both
identity and composition; identity-like pointing buys observation compatibility;
composition plus closure buys invariance. This is the ablation boundary to test
before adding any stronger algebraic laws. -/
theorem primitive_dependency_summary
    (K : Bare M X) (observe : X → Y)
    (S T : Language M) (hST : Extends S T) {x y : X}
    (hT : SameAt K observe T x y) :
    SameAt K observe S x y :=
  bare_extension_refines K observe S T hST hT

end MinimalSufficientInterface.PrimitiveAblation

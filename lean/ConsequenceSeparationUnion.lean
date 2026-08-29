import Std

universe u v w

/-!
A deliberately small compression experiment.

The existing MSI corpus contains many domain-specific presentations of the same
shape: protected consequences induce an identity; a violated consequence forces
separation; an unsupported distinction may be united; and adding one verified
consequence induces the least lawful refinement.

This file tests whether those laws can be recovered from one primitive notion
of consequential equality, without importing the existing MSI theorem stack.
-/

namespace ConsequenceSeparationUnion

variable {X : Type u} {I : Type v} {Y : Type w}

/-- Two states are the same exactly to the extent that every protected
    consequence gives the same result. -/
def ConsequentialEq (C : I → X → Y) (x y : X) : Prop :=
  ∀ i, C i x = C i y

/-- One relation is finer than another when every identification it makes is
    also made by the other relation. -/
def Subrel (E F : X → X → Prop) : Prop :=
  ∀ x y, E x y → F x y

/-- A representation relation preserves a protected consequence family. -/
def Preserves (E : X → X → Prop) (C : I → X → Y) : Prop :=
  ∀ x y, E x y → ConsequentialEq C x y

/-- A single consequence is constant on every represented equivalence class. -/
def PreservesOne (E : X → X → Prop) (c : X → Y) : Prop :=
  ∀ x y, E x y → c x = c y

/-- A verifier-visible disagreement hidden by the current representation. -/
def Residual (E : X → X → Prop) (c : X → Y) : Prop :=
  ∃ x y, E x y ∧ c x ≠ c y

/-- Add exactly one required distinction and nothing else. -/
def RefineWith (E : X → X → Prop) (c : X → Y) (x y : X) : Prop :=
  E x y ∧ c x = c y

/-- Strict refinement means no new identifications plus at least one removed
    identification. -/
def StrictlyRefines (F E : X → X → Prop) : Prop :=
  Subrel F E ∧ ∃ x y, E x y ∧ ¬ F x y

/-- Union is licensed precisely when all protected consequences agree. -/
def CanUnion (C : I → X → Y) (x y : X) : Prop :=
  ConsequentialEq C x y

/-- Separation is required precisely when some protected consequence disagrees. -/
def MustSeparate (C : I → X → Y) (x y : X) : Prop :=
  ∃ i, C i x ≠ C i y

/- The protected-consequence kernel is automatically an equivalence relation. -/
theorem consequentialEq_refl (C : I → X → Y) (x : X) :
    ConsequentialEq C x x := by
  intro i
  rfl

theorem consequentialEq_symm (C : I → X → Y) {x y : X}
    (h : ConsequentialEq C x y) : ConsequentialEq C y x := by
  intro i
  exact (h i).symm

theorem consequentialEq_trans (C : I → X → Y) {x y z : X}
    (hxy : ConsequentialEq C x y) (hyz : ConsequentialEq C y z) :
    ConsequentialEq C x z := by
  intro i
  exact (hxy i).trans (hyz i)

/-- CONSEQUENCE/DISTINCTION DUALITY: preserving a consequence family is exactly
    being a subrelation of its consequential identity. -/
theorem preserves_iff_subrel_consequentialEq
    (E : X → X → Prop) (C : I → X → Y) :
    Preserves E C ↔ Subrel E (ConsequentialEq C) := by
  rfl

/-- UNION LAW: consequential identity is the greatest relation that preserves
    every protected consequence. Any sound representation can identify no more. -/
theorem consequentialEq_greatest_preserving
    (E : X → X → Prop) (C : I → X → Y)
    (h : Preserves E C) :
    Subrel E (ConsequentialEq C) := by
  exact h

/-- The consequential identity itself preserves every protected consequence. -/
theorem consequentialEq_preserves (C : I → X → Y) :
    Preserves (ConsequentialEq C) C := by
  intro x y h
  exact h

/-- SEPARATION/UNION are exact logical duals. -/
theorem canUnion_iff_not_mustSeparate
    (C : I → X → Y) (x y : X) :
    CanUnion C x y ↔ ¬ MustSeparate C x y := by
  classical
  constructor
  · intro h ⟨i, hne⟩
    exact hne (h i)
  · intro h i
    by_contra hne
    exact h ⟨i, hne⟩

/-- A protected separator forbids union. -/
theorem separator_forces_split
    (C : I → X → Y) {x y : X} (h : MustSeparate C x y) :
    ¬ CanUnion C x y := by
  exact (canUnion_iff_not_mustSeparate C x y).mp |>.elim h

/-- Refinement by one consequence never creates a new identification. -/
theorem refineWith_subrel (E : X → X → Prop) (c : X → Y) :
    Subrel (RefineWith E c) E := by
  intro x y h
  exact h.1

/-- Refinement makes the newly protected consequence valid. -/
theorem refineWith_preserves_new (E : X → X → Prop) (c : X → Y) :
    PreservesOne (RefineWith E c) c := by
  intro x y h
  exact h.2

/-- LEAST-CHANGE LAW: `RefineWith E c` is the greatest subrelation of `E` that
    preserves the newly required consequence. Thus it removes exactly the
    identifications the verifier has made illegal, and no others. -/
theorem refineWith_is_least_change
    (E F : X → X → Prop) (c : X → Y)
    (hFE : Subrel F E) (hF : PreservesOne F c) :
    Subrel F (RefineWith E c) := by
  intro x y hxy
  exact ⟨hFE x y hxy, hF x y hxy⟩

/-- If the consequence was already preserved, least change is literally no
    change. -/
theorem refineWith_eq_self_of_preserves
    (E : X → X → Prop) (c : X → Y)
    (h : PreservesOne E c) :
    RefineWith E c = E := by
  funext x y
  apply propext
  constructor
  · intro hxy
    exact hxy.1
  · intro hxy
    exact ⟨hxy, h x y hxy⟩

/-- A residual is exactly the condition under which the canonical one-step
    repair is a genuine strict refinement. -/
theorem residual_iff_strict_refinement
    (E : X → X → Prop) (c : X → Y) :
    Residual E c ↔ StrictlyRefines (RefineWith E c) E := by
  constructor
  · rintro ⟨x, y, hE, hne⟩
    refine ⟨refineWith_subrel E c, x, y, hE, ?_⟩
    intro hR
    exact hne hR.2
  · rintro ⟨_, x, y, hE, hnot⟩
    refine ⟨x, y, hE, ?_⟩
    intro heq
    exact hnot ⟨hE, heq⟩

/-- A relation is developmentally stable for the current protected family when
    it is exactly consequential identity: neither an unsupported separation nor
    a forbidden union remains. -/
def StableFor (E : X → X → Prop) (C : I → X → Y) : Prop :=
  E = ConsequentialEq C

/-- FIXED-POINT LAW: stability is exactly soundness plus maximal union.
    This is the static endpoint of repeated verified separation/union. -/
theorem stable_iff_preserving_and_maximal
    (E : X → X → Prop) (C : I → X → Y) :
    StableFor E C ↔
      Preserves E C ∧ ∀ F : X → X → Prop, Preserves F C → Subrel F E := by
  constructor
  · intro h
    subst E
    constructor
    · exact consequentialEq_preserves C
    · intro F hF
      exact consequentialEq_greatest_preserving F C hF
  · rintro ⟨hE, hmax⟩
    unfold StableFor
    apply funext
    intro x
    apply funext
    intro y
    apply propext
    constructor
    · intro hxy
      exact hE x y hxy
    · intro hxy
      exact hmax (ConsequentialEq C) (consequentialEq_preserves C) x y hxy

/-- One-line compression: at the fixed point, every pair is united exactly when
    no verified protected consequence requires its separation. -/
theorem stable_union_separation_characterization
    (E : X → X → Prop) (C : I → X → Y)
    (hstable : StableFor E C) (x y : X) :
    E x y ↔ ¬ MustSeparate C x y := by
  rw [hstable]
  exact canUnion_iff_not_mustSeparate C x y

end ConsequenceSeparationUnion

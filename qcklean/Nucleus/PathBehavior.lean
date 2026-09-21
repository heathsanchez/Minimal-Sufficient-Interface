import Nucleus.Free
import Mathlib.CategoryTheory.Quotient

namespace Nucleus

open CategoryTheory

universe u v w z

structure PathAction (G : FiniteQuiver.{u, v}) where
  State : FreeCategory G → Type w
  map : {X Y : FreeCategory G} → (X ⟶ Y) → State X → State Y
  map_id : ∀ {X} (x : State X), map (𝟙 X) x = x
  map_comp : ∀ {X Y Z} (p : X ⟶ Y) (q : Y ⟶ Z) (x : State X),
    map (p ≫ q) x = map q (map p x)

def PathBehEq
    {G : FiniteQuiver.{u, v}}
    (A : PathAction G)
    (Obs : FreeCategory G → Type z)
    (observe : ∀ X, A.State X → Obs X)
    {X Y : FreeCategory G} (p q : X ⟶ Y) : Prop :=
  ∀ (x : A.State X) (Z : FreeCategory G) (r : Y ⟶ Z),
    observe Z (A.map (p ≫ r) x) =
      observe Z (A.map (q ≫ r) x)

def pathHomRel
    {G : FiniteQuiver.{u, v}}
    (A : PathAction G)
    (Obs : FreeCategory G → Type z)
    (observe : ∀ X, A.State X → Obs X) :
    HomRel (FreeCategory G) :=
  fun _ _ p q => PathBehEq A Obs observe p q

theorem pathBehEq_refl
    {G : FiniteQuiver.{u, v}}
    {A : PathAction G}
    {Obs : FreeCategory G → Type z}
    {observe : ∀ X, A.State X → Obs X}
    {X Y : FreeCategory G} (p : X ⟶ Y) :
    PathBehEq A Obs observe p p := by
  intro x Z r
  rfl

theorem pathBehEq_symm
    {G : FiniteQuiver.{u, v}}
    {A : PathAction G}
    {Obs : FreeCategory G → Type z}
    {observe : ∀ X, A.State X → Obs X}
    {X Y : FreeCategory G} {p q : X ⟶ Y}
    (h : PathBehEq A Obs observe p q) :
    PathBehEq A Obs observe q p := by
  intro x Z r
  exact (h x Z r).symm

theorem pathBehEq_trans
    {G : FiniteQuiver.{u, v}}
    {A : PathAction G}
    {Obs : FreeCategory G → Type z}
    {observe : ∀ X, A.State X → Obs X}
    {X Y : FreeCategory G} {p q r : X ⟶ Y}
    (hpq : PathBehEq A Obs observe p q)
    (hqr : PathBehEq A Obs observe q r) :
    PathBehEq A Obs observe p r := by
  intro x Z s
  exact (hpq x Z s).trans (hqr x Z s)

theorem pathBehEq_precomp
    {G : FiniteQuiver.{u, v}}
    {A : PathAction G}
    {Obs : FreeCategory G → Type z}
    {observe : ∀ X, A.State X → Obs X}
    {W X Y : FreeCategory G} {p q : X ⟶ Y}
    (h : PathBehEq A Obs observe p q)
    (f : W ⟶ X) :
    PathBehEq A Obs observe (f ≫ p) (f ≫ q) := by
  intro x Z r
  have h' := h (A.map f x) Z r
  rw [← A.map_comp f (p ≫ r) x, ← A.map_comp f (q ≫ r) x] at h'
  simpa only [Category.assoc] using h'

theorem pathBehEq_postcomp
    {G : FiniteQuiver.{u, v}}
    {A : PathAction G}
    {Obs : FreeCategory G → Type z}
    {observe : ∀ X, A.State X → Obs X}
    {X Y Z : FreeCategory G} {p q : X ⟶ Y}
    (h : PathBehEq A Obs observe p q)
    (g : Y ⟶ Z) :
    PathBehEq A Obs observe (p ≫ g) (q ≫ g) := by
  intro x T r
  simpa only [Category.assoc] using h x T (g ≫ r)

theorem pathBehEq_congruence
    {G : FiniteQuiver.{u, v}}
    {A : PathAction G}
    {Obs : FreeCategory G → Type z}
    {observe : ∀ X, A.State X → Obs X}
    {W X Y Z : FreeCategory G} {p q : X ⟶ Y}
    (h : PathBehEq A Obs observe p q)
    (f : W ⟶ X) (g : Y ⟶ Z) :
    PathBehEq A Obs observe (f ≫ p ≫ g) (f ≫ q ≫ g) := by
  simpa only [Category.assoc] using
    (pathBehEq_postcomp (pathBehEq_precomp h f) g)

instance pathHomRelCongruence
    {G : FiniteQuiver.{u, v}}
    (A : PathAction G)
    (Obs : FreeCategory G → Type z)
    (observe : ∀ X, A.State X → Obs X) :
    CategoryTheory.Congruence (pathHomRel A Obs observe) where
  equivalence := by
    intro X Y
    exact {
      refl := pathBehEq_refl
      symm := pathBehEq_symm
      trans := pathBehEq_trans
    }
  comp_left := by
    intro X Y Z f g g' h
    exact pathBehEq_precomp h f
  comp_right := by
    intro X Y Z f f' g h
    exact pathBehEq_postcomp h g

end Nucleus

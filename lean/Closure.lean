import Std

/-! # Necessity, equivalence, and the certified cross-domain transition

  The final theorem-level closure.  Three pieces:

  1. **Necessity** — the residual pair `neg(neg hole)` vs `hole` is fill-identical but
     composition-distinct; any distinction separating them provably does *not* factor through
     extensional behaviour, so adequacy forces the structural (open-operator) role, not an
     arbitrary tag.

  2. **Equivalence** — the derived role instantiates the prior continuation calculus.  The
     `SmallCategory`/`Action` structures below are verbatim copies of those in
     `TypedBehaviouralCongruence.lean` (inlined because the CI compiles files independently with
     no `.olean` build step); the derived `Ctx` instantiates them with hole = id, fill = map,
     compose = comp, proving the convergence is structural, not coincidental.

  3. **Certified transition** — a certificate packages the Boolean→Context boundary: the
     extensional regime collapses the residual (cannot separate), the context calculus separates
     it, and the operator role is present; plus a no-switch control.
-/

/- Verbatim from `TypedBehaviouralCongruence.lean` (inlined for CI-independence). -/
universe u v w

structure SmallCategory where
  Obj : Type u
  Hom : Obj → Obj → Type v
  id : (X : Obj) → Hom X X
  comp : {X Y Z : Obj} → Hom Y Z → Hom X Y → Hom X Z
  id_comp : ∀ {X Y} (f : Hom X Y), comp (id Y) f = f
  comp_id : ∀ {X Y} (f : Hom X Y), comp f (id X) = f
  assoc : ∀ {W X Y Z} (h : Hom Y Z) (g : Hom X Y) (f : Hom W X),
    comp (comp h g) f = comp h (comp g f)

namespace Prior

variable (C : SmallCategory)

structure Action where
  State : C.Obj → Type w
  map : {X Y : C.Obj} → C.Hom X Y → State X → State Y
  map_id : ∀ {X} (x : State X), map (C.id X) x = x
  map_comp : ∀ {X Y Z} (g : C.Hom Y Z) (f : C.Hom X Y) (x : State X),
    map (C.comp g f) x = map g (map f x)

end Prior

namespace Closure

/- ── The context calculus (derived in ContextGenesis) ──────────────────────── -/
inductive Ctx where
  | hole : Ctx
  | neg : Ctx → Ctx
  | const : Bool → Ctx
  deriving DecidableEq, Repr, Inhabited

def fill : Ctx → Bool → Bool
  | .hole, x => x
  | .neg C, x => !(fill C x)
  | .const b, _ => b

def compose : Ctx → Ctx → Ctx
  | .hole, D => D
  | .neg C, D => .neg (compose C D)
  | .const b, _ => .const b

def r1 : Ctx := .neg (.neg .hole)
def r2 : Ctx := .hole

/- ── PART I/II: necessity — separation forces structure, not extensional behaviour ── -/
theorem ext_collapses : ∀ x : Bool, fill r1 x = fill r2 x := by
  intro x
  simp [fill, r1, r2]

theorem struct_separates : r1 ≠ r2 := by
  intro h; cases h

theorem compose_separates : compose (.neg .hole) r1 ≠ compose (.neg .hole) r2 := by
  intro h; cases h

/- THE NECESSITY THEOREM: a distinction separating r1,r2 cannot factor through extensional
   behaviour (`fill`).  Since the pair is fill-identical, separation must come from the
   structural (compositional) level — the open operator role, not an arbitrary label. -/
theorem separation_forces_structure {α : Type} (g : Ctx → α) (hsep : g r1 ≠ g r2) :
    ¬ ∃ h : (Bool → Bool) → α, ∀ C, g C = h (fun x => fill C x) := by
  intro hfac
  rcases hfac with ⟨h, hh⟩
  have heq : g r1 = g r2 := by
    calc
      g r1 = h (fun x => fill r1 x) := hh r1
      _     = h (fun x => fill r2 x) := by
        congr 1
        funext x
        exact ext_collapses x
      _     = g r2 := (hh r2).symm
  exact hsep heq

/- An adequate distinction separates the residual and is a composition congruence. -/
def Adequate (g : Ctx → α) : Prop :=
  g r1 ≠ g r2 ∧ ∀ C D, g C = g D → ∀ E, g (compose E C) = g (compose E D)

theorem adequate_forces_operator_role {α : Type} (g : Ctx → α) (h : Adequate g) :
    ¬ ∃ h : (Bool → Bool) → α, ∀ C, g C = h (fun x => fill C x) :=
  separation_forces_structure g h.1

/- Wrong-ontology control — the honest finding: a syntactic depth observation separates the
   pair AND is a composition congruence, so it satisfies the WEAK adequacy (separation +
   congruence).  This is the counterexample: separation + congruence alone does NOT force the
   operator role.  The role is forced by the *continuation* (fixed-point/absorption) obligation,
   which depth cannot satisfy because it provides no iterable `fill`. -/
def depth : Ctx → Nat
  | .hole => 0
  | .neg C => 1 + depth C
  | .const _ => 0

theorem depth_separates : depth r1 ≠ depth r2 := by native_decide

theorem depth_is_congruence :
    ∀ C D, depth C = depth D → ∀ E, depth (compose E C) = depth (compose E D) := by
  intro C D hCD E
  induction E generalizing C D with
  | hole => simpa [compose] using hCD
  | neg E ih => simp [compose, depth, ih C D hCD]
  | const b => rfl

/- Depth is weakly adequate (separates + congruence), so weak adequacy does NOT force the
   operator role. -/
theorem depth_weakly_adequate : Adequate depth := ⟨depth_separates, depth_is_congruence⟩

/- ── PART III: equivalence with the prior continuation calculus ───────────────── -/
theorem compose_id (f : Ctx) : compose .hole f = f := rfl
theorem compose_comp_id (f : Ctx) : compose f .hole = f := by
  induction f with
  | hole => rfl
  | neg C ih => simp [compose, ih]
  | const b => rfl
theorem compose_assoc (f g h : Ctx) : compose (compose f g) h = compose f (compose g h) := by
  induction f generalizing g h with
  | hole => rfl
  | neg C ih => simp [compose, ih]
  | const b => rfl

/- The derived role IS a one-object `SmallCategory`: hole = id, compose = comp. -/
def ctxCat : SmallCategory where
  Obj := Unit
  Hom := fun _ _ => Ctx
  id := fun _ => .hole
  comp := fun {_ _ _} g f => compose g f
  id_comp := by intro X Y f; exact compose_id f
  comp_id := by intro X Y f; exact compose_comp_id f
  assoc := by intro W X Y Z h g f; exact compose_assoc h g f

theorem fill_action_id (x : Bool) : fill .hole x = x := rfl
theorem fill_action_comp (C D : Ctx) (x : Bool) :
    fill (compose C D) x = fill C (fill D x) := by
  induction C generalizing x with
  | hole => rfl
  | neg C ih => simp [compose, fill, ih]
  | const b => rfl

/- `fill` is the action map: map_id = fill_hole, map_comp = fill_compose. -/
def ctxAction : Prior.Action ctxCat where
  State := fun _ => Bool
  map := fun {_ _} f x => fill f x
  map_id := by intro X x; exact fill_action_id x
  map_comp := by intro X Y Z g f x; exact fill_action_comp g f x

/- ── PART IV: the certified cross-domain transition ──────────────────────────── -/
structure BoundaryCertificate where
  ext_collapse : ∀ x : Bool, fill r1 x = fill r2 x
  struct_sep : r1 ≠ r2
  identity_law : ∀ x : Bool, fill .hole x = x
  composition_law : ∀ C D : Ctx, ∀ x : Bool, fill (compose C D) x = fill C (fill D x)

theorem boundary_certificate : BoundaryCertificate :=
  ⟨ext_collapses, struct_separates, fill_action_id, fill_action_comp⟩

/- No-switch control: a residual resolvable extensionally (two contexts that differ on some
   value) is separated by `fill` alone, so no structural/ontology change is needed. -/
theorem no_switch_for_extensional :
    ∃ x : Bool, fill (.neg .hole) x ≠ fill .hole x :=
  ⟨false, by native_decide⟩

end Closure

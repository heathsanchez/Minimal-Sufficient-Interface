# Nucleus Universal Property V0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (\`- [ ]\`) syntax for tracking.

**Goal:** Build and qualify a Lean 4 theorem package showing that a finite quiver has a free compositional completion, that a verifier-backed path congruence yields the expected quotient universal property, and that a certified residual can force the least fresh-arrow extension before warranted equations are imposed.

**Architecture:** Reuse Mathlib's pinned \`CategoryTheory.Paths\` and \`CategoryTheory.Quotient\` rather than reimplementing category theory. Wrap a finite edge/source/target presentation as a Mathlib quiver, define behavioural equality directly on paths, instantiate Mathlib's \`Congruence\`, then use \`Quotient.lift\` / \`lift_unique\` for factorization. Model fresh-arrow genesis as the path category of an augmented quiver containing all old arrows plus one new seed, quotiented only by the old category's identity/composition equations.

**Tech Stack:** Lean \`v4.35.0-rc2\`; Mathlib commit \`44ba35c6daa9d69aff8fed9fff9bbde17ded774d\`; Lake; GitHub Actions \`ubuntu-24.04\`.

**Spec:** \`docs/superpowers/specs/2026-09-21-nucleus-universal-property-v0-design.md\`

## Global Constraints

- Work only on branch \`nucleus-universal-property-v0\`, based on commit \`900a73c1d386ee0eee1205a1cf31d270f3311ef7\`.
- Preserve Lean \`v4.35.0-rc2\` and Mathlib \`44ba35c6daa9d69aff8fed9fff9bbde17ded774d\` exactly.
- Do not modify existing \`qcklean/QCK*.lean\` or \`qcklean/CLC/**\` theorem/test files.
- New theorem code lives under \`qcklean/Nucleus/**\`; only \`qcklean/lakefile.lean\` and a new Nucleus workflow may be modified outside that directory.
- Use Mathlib's pinned \`CategoryTheory.Paths\`, \`Paths.lift\`, \`Paths.lift_unique\`, \`Quiv.pathsEquiv\`, \`CategoryTheory.HomRel\`, \`CategoryTheory.Congruence\`, and \`CategoryTheory.Quotient\` APIs where applicable.
- Keep vertices explicit. Do not claim references are recoverable from edge incidence.
- \`PathBehEq\` must quantify over every source state and every future continuation; no weaker relation may instantiate the quotient congruence.
- \`ValidGen\` must be defined from a quiver interpretation plus an equation-respecting proof; it must not mention existence of a functor out of the quotient.
- Fresh-arrow genesis must not assume the new arrow already exists in the source category.
- The raw generated direction and behavioural refinement direction remain distinct; do not assert a forward colimit for quotient stages.
- No \`sorry\`, \`admit\`, project-local \`axiom\`, \`constant\`, or \`unsafe\` declaration may occur under \`qcklean/Nucleus/\`.
- Every task follows red/green TDD and ends with a focused commit.

## File Map

| Path | Responsibility |
|---|---|
| \`qcklean/Nucleus/Quiver.lean\` | finite edge/source/target presentation and Mathlib quiver wrapper |
| \`qcklean/Nucleus/Free.lean\` | free path category, lift, uniqueness, and free universal equivalence |
| \`qcklean/Nucleus/PathBehavior.lean\` | typed path action, protected observations, path behavioural congruence |
| \`qcklean/Nucleus/Quotient.lean\` | Nucleus quotient category and canonical projection |
| \`qcklean/Nucleus/Universal.lean\` | quotient descent, \`ValidGen\`, and \`nucleus_universal\` |
| \`qcklean/Nucleus/ResidualAdjoin.lean\` | fresh-arrow augmented quiver, structural quotient, inclusion, seed, universal lift |
| \`qcklean/Nucleus/Development.lean\` | free residual attachment followed by warranted quotient |
| \`qcklean/Nucleus/Temporal.lean\` | inverse refinement functor between behavioural quotients |
| \`qcklean/Nucleus/Fixtures.lean\` | finite positive and mandatory negative fixtures |
| \`qcklean/Nucleus/Audit.lean\` | \`#print axioms\` for the public theorem surface |
| \`qcklean/Nucleus/*Test.lean\` | compile-time interface and executable fixture tests |
| \`qcklean/lakefile.lean\` | register Nucleus modules/tests/audit as QCK roots |
| \`.github/workflows/nucleus-universal-property-v0.yml\` | frozen-source, build, test, placeholder, and axiom qualification |

## Review Focus

1. **Parallel edges with identical endpoints:** two distinct primitive edges must remain distinct singleton paths until warrant explicitly identifies them; \`FreeTest\` pins this.
2. **Immediate equality without future equality:** paths that have the same local observation but are separated after one continuation must fail the weak relation and remain distinct under \`PathBehEq\); \`PathBehaviorTest\` pins this.
3. **Agreement on one source state only:** path equality cannot be inferred from a distinguished input; a second source state must be able to separate them; \`PathBehaviorTest\` pins this.
4. **Old-arrow laws in residual attachment:** the adjoined category must identify singleton old identities with empty paths and two old arrows with their old composite, while leaving the fresh seed unconstrained; \`ResidualAdjoinTest\` pins this.
5. **Refinement direction:** if \`rNew ⊆ rOld\`, the canonical functor must be \`Quotient rNew ⥤ Quotient rOld\`, never silently reversed; \`TemporalTest\` pins this.

---

### Task 1: Finite quiver wrapper and free-category universal property

**Files:**
- Create: \`qcklean/Nucleus/QuiverTest.lean\`
- Create: \`qcklean/Nucleus/Quiver.lean\`
- Create: \`qcklean/Nucleus/FreeTest.lean\`
- Create: \`qcklean/Nucleus/Free.lean\`

**Interfaces:**
- Consumes: Mathlib \`CategoryTheory.PathCategory.Basic\` and \`CategoryTheory.Category.Quiv\`.
- Produces: \`FiniteQuiver\`, \`Vertex\`, \`primitiveEdge\`, \`FreeCategory\`, \`freeNucleus_lift\`, \`freeNucleus_lift_unique\`, and \`freeNucleus_equiv\`.

- [ ] **Step 1: Write the failing finite-quiver interface test**

\`\`\`lean
-- qcklean/Nucleus/QuiverTest.lean
import Nucleus.Quiver

open CategoryTheory
open Nucleus

#check FiniteQuiver
#check Vertex
#check primitiveEdge

inductive V | a | b deriving DecidableEq, Fintype
inductive E | left | right deriving DecidableEq, Fintype

def G : FiniteQuiver where
  V := V
  E := E
  vFinite := inferInstance
  eFinite := inferInstance
  vDecEq := inferInstance
  eDecEq := inferInstance
  src := fun _ => V.a
  tgt := fun _ => V.b

example : primitiveEdge G E.left ≠ primitiveEdge G E.right := by
  intro h
  have := congrArg Subtype.val h
  cases this
\`\`\`

- [ ] **Step 2: Run the test and verify RED**

Run: \`cd qcklean && lake env lean Nucleus/QuiverTest.lean\`

Expected: FAIL because \`Nucleus.Quiver\` is missing.

- [ ] **Step 3: Implement the finite quiver wrapper**

\`\`\`lean
-- qcklean/Nucleus/Quiver.lean
import Mathlib.CategoryTheory.PathCategory.Basic
import Mathlib.CategoryTheory.Category.Quiv

namespace Nucleus

universe u v

structure FiniteQuiver where
  V : Type u
  E : Type v
  vFinite : Fintype V
  eFinite : Fintype E
  vDecEq : DecidableEq V
  eDecEq : DecidableEq E
  src : E → V
  tgt : E → V

attribute [instance] FiniteQuiver.vFinite FiniteQuiver.eFinite
  FiniteQuiver.vDecEq FiniteQuiver.eDecEq

def Vertex (G : FiniteQuiver) := G.V

instance (G : FiniteQuiver) : Fintype (Vertex G) := G.vFinite
instance (G : FiniteQuiver) : DecidableEq (Vertex G) := G.vDecEq

instance (G : FiniteQuiver) : Quiver (Vertex G) where
  Hom X Y := {e : G.E // G.src e = X ∧ G.tgt e = Y}

def primitiveEdge (G : FiniteQuiver) (e : G.E) :
    (show Vertex G from G.src e) ⟶ (show Vertex G from G.tgt e) :=
  ⟨e, rfl, rfl⟩

end Nucleus
\`\`\`

- [ ] **Step 4: Run the finite-quiver test and verify GREEN**

Run: \`cd qcklean && lake env lean Nucleus/QuiverTest.lean\`

Expected: PASS.

- [ ] **Step 5: Write the failing free-category interface test**

\`\`\`lean
-- qcklean/Nucleus/FreeTest.lean
import Nucleus.Free

open CategoryTheory
open Nucleus

#check FreeCategory
#check freeNucleus_lift
#check freeNucleus_lift_unique
#check freeNucleus_equiv
#check CategoryTheory.Paths.lift
#check CategoryTheory.Paths.lift_unique
#check CategoryTheory.Quiv.pathsEquiv
\`\`\`

Add a two-parallel-edge fixture using Task 1's shape locally and prove the two singleton paths are not definitionally equal by reducing equality to the unequal underlying edge subtype values.

- [ ] **Step 6: Run the free test and verify RED**

Run: \`cd qcklean && lake env lean Nucleus/FreeTest.lean\`

Expected: FAIL because \`Nucleus.Free\` is missing.

- [ ] **Step 7: Implement the free-category aliases and theorem wrappers**

\`\`\`lean
-- qcklean/Nucleus/Free.lean
import Nucleus.Quiver

namespace Nucleus

open CategoryTheory

universe u v u' v'

abbrev FreeCategory (G : FiniteQuiver.{u, v}) :=
  CategoryTheory.Paths (Vertex G)

def freeNucleus_lift
    (G : FiniteQuiver.{u, v})
    {D : Type u'} [Category.{v'} D]
    (φ : Vertex G ⥤q D) :
    FreeCategory G ⥤ D :=
  CategoryTheory.Paths.lift φ

theorem freeNucleus_lift_unique
    (G : FiniteQuiver.{u, v})
    {D : Type u'} [Category.{v'} D]
    (φ : Vertex G ⥤q D)
    (F : FreeCategory G ⥤ D)
    (hF : CategoryTheory.Paths.of (Vertex G) ⋙q F.toPrefunctor = φ) :
    F = freeNucleus_lift G φ :=
  CategoryTheory.Paths.lift_unique φ F hF

def freeNucleus_equiv
    (G : FiniteQuiver.{u, v})
    {D : Type u'} [Category.{v'} D] :
    (FreeCategory G ⥤ D) ≃ (Vertex G ⥤q D) :=
  CategoryTheory.Quiv.pathsEquiv

end Nucleus
\`\`\`

- [ ] **Step 8: Run both Task 1 tests**

Run:
\`\`\`bash
cd qcklean
lake env lean Nucleus/QuiverTest.lean
lake env lean Nucleus/FreeTest.lean
\`\`\`

Expected: PASS.

- [ ] **Step 9: Commit the free-generation layer**

\`\`\`bash
git add qcklean/Nucleus/Quiver.lean qcklean/Nucleus/QuiverTest.lean \
  qcklean/Nucleus/Free.lean qcklean/Nucleus/FreeTest.lean
git commit -m "feat(nucleus): formalize free directed generation"
\`\`\`

### Task 2: Path-level behavioural equality and two-sided congruence

**Files:**
- Create: \`qcklean/Nucleus/PathBehaviorTest.lean\`
- Create: \`qcklean/Nucleus/PathBehavior.lean\`
- Create: \`qcklean/Nucleus/Fixtures.lean\` with the two behavioural counterexamples.

**Interfaces:**
- Consumes: \`FreeCategory\`.
- Produces: \`PathAction\`, \`PathBehEq\`, \`pathHomRel\`, congruence instances, \`pathBehEq_precomp\`, \`pathBehEq_postcomp\`, and \`pathBehEq_congruence\`.

- [ ] **Step 1: Write the failing path-behaviour interface test**

\`\`\`lean
-- qcklean/Nucleus/PathBehaviorTest.lean
import Nucleus.PathBehavior
import Nucleus.Fixtures

open CategoryTheory
open Nucleus
open Nucleus.Fixtures

#check PathAction
#check PathBehEq
#check pathHomRel
#check pathBehEq_refl
#check pathBehEq_symm
#check pathBehEq_trans
#check pathBehEq_precomp
#check pathBehEq_postcomp
#check pathBehEq_congruence

example : ¬ ImmediateObsEq futureFixtureAction futureFixtureObs
    futureP futureQ := by
  exact futureImmediateWeakness

example : ¬ OneStateEq sourceFixtureAction sourceFixtureObs
    sourceChosen sourceP sourceQ := by
  exact sourceStateWeakness
\`\`\`

The public negative names intentionally state that the corresponding weak relation is inadequate; the fixture definitions below must make these proofs executable rather than axiomatic.

- [ ] **Step 2: Run and verify RED**

Run: \`cd qcklean && lake env lean Nucleus/PathBehaviorTest.lean\`

Expected: FAIL because \`Nucleus.PathBehavior\` is missing.

- [ ] **Step 3: Implement typed path actions and behavioural equality**

\`\`\`lean
-- qcklean/Nucleus/PathBehavior.lean
import Nucleus.Free

namespace Nucleus

open CategoryTheory

universe u v w z

structure PathAction (G : FiniteQuiver.{u, v}) where
  State : Vertex G → Type w
  map : {X Y : Vertex G} → (X ⟶ Y) → State X → State Y
  map_id : ∀ {X} (x : State X), map (𝟙 X) x = x
  map_comp : ∀ {X Y Z} (p : X ⟶ Y) (q : Y ⟶ Z) (x : State X),
    map (p ≫ q) x = map q (map p x)

def PathBehEq
    {G : FiniteQuiver.{u, v}}
    (A : PathAction G)
    (Obs : Vertex G → Type z)
    (observe : ∀ X, A.State X → Obs X)
    {X Y : FreeCategory G} (p q : X ⟶ Y) : Prop :=
  ∀ (x : A.State X) (Z : Vertex G) (r : Y ⟶ Z),
    observe Z (A.map (p ≫ r) x) =
      observe Z (A.map (q ≫ r) x)

def pathHomRel
    {G : FiniteQuiver.{u, v}}
    (A : PathAction G)
    (Obs : Vertex G → Type z)
    (observe : ∀ X, A.State X → Obs X) :
    HomRel (FreeCategory G) :=
  fun _ _ p q => PathBehEq A Obs observe p q
\`\`\`

Prove \`pathBehEq_refl\`, \`pathBehEq_symm\`, and \`pathBehEq_trans\` by pointwise equality.

- [ ] **Step 4: Prove pre- and postcomposition stability**

Implement these exact theorem surfaces:

\`\`\`lean
theorem pathBehEq_precomp
    (h : PathBehEq A Obs observe p q)
    (f : W ⟶ X) :
    PathBehEq A Obs observe (f ≫ p) (f ≫ q)

theorem pathBehEq_postcomp
    (h : PathBehEq A Obs observe p q)
    (g : Y ⟶ Z) :
    PathBehEq A Obs observe (p ≫ g) (q ≫ g)

theorem pathBehEq_congruence
    (h : PathBehEq A Obs observe p q)
    (f : W ⟶ X) (g : Y ⟶ Z) :
    PathBehEq A Obs observe (f ≫ p ≫ g) (f ≫ q ≫ g)
\`\`\`

For precomposition, rewrite with \`Category.assoc\` and \`A.map_comp\`, then apply \`h\` to the source state \`A.map f x\`. For postcomposition, apply \`h\` to the composite future \`g ≫ r\` and normalize associativity.

Instantiate:

\`\`\`lean
instance pathHomRelCongruence :
    CategoryTheory.Congruence (pathHomRel A Obs observe)
\`\`\`

using the equivalence proofs and \`pathBehEq_precomp\` / \`pathBehEq_postcomp\`.

- [ ] **Step 5: Implement the two mandatory weak-relation fixtures**

In \`Nucleus/Fixtures.lean\`, import \`Mathlib.CategoryTheory.Types.Basic\` and define:

- a three-object quiver \`X → Y → Z\` with two parallel \`X → Y\` edges \`p,q\`;
- a state action where \`p\` and \`q\` reach different hidden \`Y\` states, \`observe Y\` is constant, and \`r : Y → Z\` exposes the hidden bit;
- \`ImmediateObsEq\` that compares only the observation at the common target and a theorem \`futureImmediateWeakness\` showing it holds for \`p,q\` while \`PathBehEq\` fails;
- a second fixture with two source states, a chosen source state on which \`p,q\` agree, and another source state on which they differ;
- \`OneStateEq\` and theorem \`sourceStateWeakness\` showing one-state agreement does not imply \`PathBehEq\`.

Use \`CategoryTheory.Paths.lift\` from a prefunctor into \`Type\` to define each fixture's total action on all generated paths; convert functions with the scoped \`↾\` notation from \`Mathlib.CategoryTheory.Types.Basic\`.

- [ ] **Step 6: Run the behavioural test and verify GREEN**

Run: \`cd qcklean && lake env lean Nucleus/PathBehaviorTest.lean\`

Expected: PASS, including both negative fixtures and the two-sided congruence checks.

- [ ] **Step 7: Commit the path-congruence layer**

\`\`\`bash
git add qcklean/Nucleus/PathBehavior.lean qcklean/Nucleus/PathBehaviorTest.lean \
  qcklean/Nucleus/Fixtures.lean
git commit -m "feat(nucleus): prove warranted path congruence"
\`\`\`

### Task 3: Nucleus quotient category and projection

**Files:**
- Create: \`qcklean/Nucleus/QuotientTest.lean\`
- Create: \`qcklean/Nucleus/Quotient.lean\`

**Interfaces:**
- Consumes: \`pathHomRel\` and its \`Congruence\` instance.
- Produces: \`NucleusCategory\`, \`nucleusProjection\`, \`nucleusProjection_sound\`, \`nucleusProjection_exact\`, and \`nucleusProjection_surjective_on_hom\`.

- [ ] **Step 1: Write the failing quotient interface test**

\`\`\`lean
-- qcklean/Nucleus/QuotientTest.lean
import Nucleus.Quotient

open CategoryTheory
open Nucleus

#check NucleusCategory
#check nucleusProjection
#check nucleusProjection_sound
#check nucleusProjection_exact
#check nucleusProjection_surjective_on_hom
\`\`\`

- [ ] **Step 2: Run and verify RED**

Run: \`cd qcklean && lake env lean Nucleus/QuotientTest.lean\`

Expected: FAIL because \`Nucleus.Quotient\` is missing.

- [ ] **Step 3: Implement the quotient category directly with Mathlib**

\`\`\`lean
-- qcklean/Nucleus/Quotient.lean
import Nucleus.PathBehavior
import Mathlib.CategoryTheory.Quotient

namespace Nucleus

open CategoryTheory

universe u v w z

abbrev NucleusCategory
    {G : FiniteQuiver.{u, v}}
    (A : PathAction G)
    (Obs : Vertex G → Type z)
    (observe : ∀ X, A.State X → Obs X) :=
  CategoryTheory.Quotient (pathHomRel A Obs observe)

def nucleusProjection
    {G : FiniteQuiver.{u, v}}
    (A : PathAction G)
    (Obs : Vertex G → Type z)
    (observe : ∀ X, A.State X → Obs X) :
    FreeCategory G ⥤ NucleusCategory A Obs observe :=
  CategoryTheory.Quotient.functor (pathHomRel A Obs observe)
\`\`\`

Prove:

\`\`\`lean
theorem nucleusProjection_sound
    (h : PathBehEq A Obs observe p q) :
    (nucleusProjection A Obs observe).map p =
      (nucleusProjection A Obs observe).map q :=
  CategoryTheory.Quotient.sound _ h

theorem nucleusProjection_exact (p q : X ⟶ Y) :
    (nucleusProjection A Obs observe).map p =
      (nucleusProjection A Obs observe).map q ↔
    PathBehEq A Obs observe p q :=
  CategoryTheory.Quotient.functor_map_eq_iff _ p q
\`\`\`

For hom-surjectivity, use the \`Full\` instance on \`CategoryTheory.Quotient.functor\`:

\`\`\`lean
theorem nucleusProjection_surjective_on_hom
    {X Y : FreeCategory G}
    (f : (nucleusProjection A Obs observe).obj X ⟶
      (nucleusProjection A Obs observe).obj Y) :
    ∃ p : X ⟶ Y, (nucleusProjection A Obs observe).map p = f :=
  (nucleusProjection A Obs observe).map_surjective f
\`\`\`

- [ ] **Step 4: Run and verify GREEN**

Run: \`cd qcklean && lake env lean Nucleus/QuotientTest.lean\`

Expected: PASS.

- [ ] **Step 5: Commit the quotient category**

\`\`\`bash
git add qcklean/Nucleus/Quotient.lean qcklean/Nucleus/QuotientTest.lean
git commit -m "feat(nucleus): construct warranted quotient category"
\`\`\`

### Task 4: Quotient descent and generator-level universal property

**Files:**
- Create: \`qcklean/Nucleus/UniversalTest.lean\`
- Create: \`qcklean/Nucleus/Universal.lean\`

**Interfaces:**
- Consumes: \`freeNucleus_lift\`, \`NucleusCategory\`, \`nucleusProjection\`.
- Produces: \`WarrantRespecting\`, \`nucleus_descend\`, \`nucleus_descend_comp_projection\`, \`nucleus_descend_unique\`, \`ValidGen\`, \`nucleusToValidGen\`, \`validGenToNucleus\`, and \`nucleus_universal\`.

- [ ] **Step 1: Write the failing universal-property test**

\`\`\`lean
-- qcklean/Nucleus/UniversalTest.lean
import Nucleus.Universal

open CategoryTheory
open Nucleus

#check WarrantRespecting
#check nucleus_descend
#check nucleus_descend_comp_projection
#check nucleus_descend_unique
#check ValidGen
#check nucleusToValidGen
#check validGenToNucleus
#check nucleus_universal
\`\`\`

- [ ] **Step 2: Run and verify RED**

Run: \`cd qcklean && lake env lean Nucleus/UniversalTest.lean\`

Expected: FAIL because \`Nucleus.Universal\` is missing.

- [ ] **Step 3: Implement quotient descent and uniqueness**

\`\`\`lean
-- qcklean/Nucleus/Universal.lean
import Nucleus.Quotient

namespace Nucleus

open CategoryTheory

universe u v w z u' v'

def WarrantRespecting
    {G : FiniteQuiver.{u, v}}
    (A : PathAction G)
    (Obs : Vertex G → Type z)
    (observe : ∀ X, A.State X → Obs X)
    {D : Type u'} [Category.{v'} D]
    (H : FreeCategory G ⥤ D) : Prop :=
  ∀ X Y (p q : X ⟶ Y),
    PathBehEq A Obs observe p q → H.map p = H.map q

def nucleus_descend
    (H : FreeCategory G ⥤ D)
    (hH : WarrantRespecting A Obs observe H) :
    NucleusCategory A Obs observe ⥤ D :=
  CategoryTheory.Quotient.lift
    (pathHomRel A Obs observe) H
    (fun X Y p q h => hH X Y p q h)

theorem nucleus_descend_comp_projection
    (H : FreeCategory G ⥤ D)
    (hH : WarrantRespecting A Obs observe H) :
    nucleusProjection A Obs observe ⋙ nucleus_descend A Obs observe H hH = H :=
  CategoryTheory.Quotient.lift_spec _ _ _

theorem nucleus_descend_unique
    (H : FreeCategory G ⥤ D)
    (hH : WarrantRespecting A Obs observe H)
    (K : NucleusCategory A Obs observe ⥤ D)
    (hK : nucleusProjection A Obs observe ⋙ K = H) :
    K = nucleus_descend A Obs observe H hH :=
  CategoryTheory.Quotient.lift_unique _ H _ K hK
\`\`\`

- [ ] **Step 4: Implement non-circular \`ValidGen\`**

\`\`\`lean
structure ValidGen
    {G : FiniteQuiver.{u, v}}
    (A : PathAction G)
    (Obs : Vertex G → Type z)
    (observe : ∀ X, A.State X → Obs X)
    (D : Type u') [Category.{v'} D] where
  gen : Vertex G ⥤q D
  respects : WarrantRespecting A Obs observe (freeNucleus_lift G gen)
\`\`\`

Add an extensionality theorem:

\`\`\`lean
@[ext]
theorem ValidGen.ext
    {x y : ValidGen A Obs observe D}
    (h : x.gen = y.gen) : x = y := by
  cases x
  cases y
  cases h
  rfl
\`\`\`

The proof works because the remaining fields are propositions.

- [ ] **Step 5: Implement both directions of the universal correspondence**

Define:

\`\`\`lean
def validGenToNucleus
    (v : ValidGen A Obs observe D) :
    NucleusCategory A Obs observe ⥤ D :=
  nucleus_descend A Obs observe
    (freeNucleus_lift G v.gen) v.respects

def nucleusToValidGen
    (F : NucleusCategory A Obs observe ⥤ D) :
    ValidGen A Obs observe D where
  gen :=
    CategoryTheory.Paths.of (Vertex G) ⋙q
      (nucleusProjection A Obs observe ⋙ F).toPrefunctor
  respects := by
    intro X Y p q hpq
    have hπ :
        (nucleusProjection A Obs observe).map p =
          (nucleusProjection A Obs observe).map q :=
      nucleusProjection_sound hpq
    simpa using congrArg F.map hπ
\`\`\`

Prove the two inverse laws.

For \`nucleusToValidGen (validGenToNucleus v) = v\`, use \`ValidGen.ext\`, then \`CategoryTheory.Paths.lift_spec\` and \`nucleus_descend_comp_projection\`.

For \`validGenToNucleus (nucleusToValidGen F) = F\`, first prove that the free lift of the restricted generator prefunctor equals \`nucleusProjection ⋙ F\` with \`CategoryTheory.Paths.lift_unique\`, then apply \`CategoryTheory.Quotient.lift_unique'\`.

Package:

\`\`\`lean
def nucleus_universal :
    (NucleusCategory A Obs observe ⥤ D) ≃
      ValidGen A Obs observe D where
  toFun := nucleusToValidGen A Obs observe
  invFun := validGenToNucleus A Obs observe
  left_inv := validGenToNucleus_nucleusToValidGen A Obs observe
  right_inv := nucleusToValidGen_validGenToNucleus A Obs observe
\`\`\`

- [ ] **Step 6: Run universal-property tests**

Run:
\`\`\`bash
cd qcklean
lake env lean Nucleus/UniversalTest.lean
lake env lean Nucleus/QuotientTest.lean
\`\`\`

Expected: PASS.

- [ ] **Step 7: Commit the Nucleus universal property**

\`\`\`bash
git add qcklean/Nucleus/Universal.lean qcklean/Nucleus/UniversalTest.lean
git commit -m "feat(nucleus): prove generators-and-relations universal property"
\`\`\`

### Task 5: Fresh-arrow augmented quiver and structural quotient

**Files:**
- Create: \`qcklean/Nucleus/ResidualAdjoinTest.lean\`
- Create: \`qcklean/Nucleus/ResidualAdjoin.lean\`

**Interfaces:**
- Consumes: Mathlib path category and quotient category.
- Produces: \`ResidualObj\`, \`ResidualEdge\`, \`ResidualRel\`, \`ResidualAdjoin\`, \`residualInclusion\`, and \`residualSeed\`.

- [ ] **Step 1: Write the failing fresh-arrow interface test**

\`\`\`lean
-- qcklean/Nucleus/ResidualAdjoinTest.lean
import Nucleus.ResidualAdjoin

open CategoryTheory
open Nucleus

#check ResidualObj
#check ResidualEdge.old
#check ResidualEdge.seed
#check ResidualRel
#check ResidualAdjoin
#check residualInclusion
#check residualSeed
\`\`\`

Add a fixture category \`NoXY\` with objects \`x | y\`, only identity morphisms, and prove there is no source morphism \`x ⟶ y\` but \`residualSeed (C := NoXY) x y\` typechecks in the adjoined category.

- [ ] **Step 2: Run and verify RED**

Run: \`cd qcklean && lake env lean Nucleus/ResidualAdjoinTest.lean\`

Expected: FAIL because \`Nucleus.ResidualAdjoin\` is missing.

- [ ] **Step 3: Define the augmented quiver**

\`\`\`lean
-- qcklean/Nucleus/ResidualAdjoin.lean
import Mathlib.CategoryTheory.PathCategory.Basic
import Mathlib.CategoryTheory.Quotient

namespace Nucleus

open CategoryTheory

universe u v u' v'

def ResidualObj (C : Type u) := C

inductive ResidualEdge
    (C : Type u) [Category.{v} C] (X Y : C) :
    ResidualObj C → ResidualObj C → Type (max u v)
  | old {A B : C} (f : A ⟶ B) : ResidualEdge C X Y A B
  | seed : ResidualEdge C X Y X Y

instance residualQuiver
    (C : Type u) [Category.{v} C] (X Y : C) :
    Quiver (ResidualObj C) where
  Hom := ResidualEdge C X Y

abbrev ResidualFree
    (C : Type u) [Category.{v} C] (X Y : C) :=
  CategoryTheory.Paths (ResidualObj C)
\`\`\`

- [ ] **Step 4: Define only the old-category equations**

Define the generating relation:

\`\`\`lean
inductive ResidualRel
    (C : Type u) [Category.{v} C] (X Y : C) :
    HomRel (ResidualFree C X Y)
  | old_id (A : C) :
      ResidualRel C X Y
        (Quiver.Hom.toPath (ResidualEdge.old (C := C) (X := X) (Y := Y) (𝟙 A)))
        (𝟙 (show ResidualObj C from A))
  | old_comp {A B D : C} (f : A ⟶ B) (g : B ⟶ D) :
      ResidualRel C X Y
        (Quiver.Hom.toPath
          (ResidualEdge.old (C := C) (X := X) (Y := Y) f) ≫
         Quiver.Hom.toPath
          (ResidualEdge.old (C := C) (X := X) (Y := Y) g))
        (Quiver.Hom.toPath
          (ResidualEdge.old (C := C) (X := X) (Y := Y) (f ≫ g)))
\`\`\`

Then:

\`\`\`lean
abbrev ResidualAdjoin
    (C : Type u) [Category.{v} C] (X Y : C) :=
  CategoryTheory.Quotient (ResidualRel C X Y)
\`\`\`

Do not add any relation mentioning \`ResidualEdge.seed\`.

- [ ] **Step 5: Implement the old-category inclusion and fresh seed**

\`\`\`lean
def residualInclusion
    (C : Type u) [Category.{v} C] (X Y : C) :
    C ⥤ ResidualAdjoin C X Y where
  obj A := CategoryTheory.Quotient.mk (show ResidualObj C from A)
  map f :=
    (CategoryTheory.Quotient.functor (ResidualRel C X Y)).map
      (Quiver.Hom.toPath
        (ResidualEdge.old (C := C) (X := X) (Y := Y) f))
  map_id A := CategoryTheory.Quotient.sound _ (ResidualRel.old_id A)
  map_comp f g :=
    CategoryTheory.Quotient.sound _ (ResidualRel.old_comp f g)

def residualSeed
    (C : Type u) [Category.{v} C] (X Y : C) :
    (residualInclusion C X Y).obj X ⟶
      (residualInclusion C X Y).obj Y :=
  (CategoryTheory.Quotient.functor (ResidualRel C X Y)).map
    (Quiver.Hom.toPath
      (ResidualEdge.seed (C := C) (X := X) (Y := Y)))
\`\`\`

- [ ] **Step 6: Run the fresh-arrow tests**

Run: \`cd qcklean && lake env lean Nucleus/ResidualAdjoinTest.lean\`

Expected: PASS, including the no-ambient-\`X→Y\` fixture.

- [ ] **Step 7: Commit the residual syntax**

\`\`\`bash
git add qcklean/Nucleus/ResidualAdjoin.lean qcklean/Nucleus/ResidualAdjoinTest.lean
git commit -m "feat(nucleus): construct fresh-arrow residual extension"
\`\`\`

### Task 6: Universal property of the fresh-arrow extension

**Files:**
- Modify: \`qcklean/Nucleus/ResidualAdjoin.lean\`
- Modify: \`qcklean/Nucleus/ResidualAdjoinTest.lean\`

**Interfaces:**
- Consumes: \`ResidualRel\`, \`ResidualAdjoin\`, \`residualInclusion\`, \`residualSeed\`.
- Produces: \`residualPrefunctor\`, \`residualFreeEval\`, \`residualAdjoinLift\`, \`residualAdjoin_agrees\`, \`residualAdjoin_seed\`, \`residualAdjoin_unique\`, and \`residualAdjoin_universal\`.

- [ ] **Step 1: Add failing universal-property checks**

Append:

\`\`\`lean
#check residualPrefunctor
#check residualFreeEval
#check residualAdjoinLift
#check residualAdjoin_agrees
#check residualAdjoin_seed
#check residualAdjoin_unique
#check residualAdjoin_universal
\`\`\`

Run: \`cd qcklean && lake env lean Nucleus/ResidualAdjoinTest.lean\`

Expected: FAIL on the new declarations.

- [ ] **Step 2: Define evaluation of the augmented quiver**

For \`F : C ⥤ D\` and \`a : F.obj X ⟶ F.obj Y\`:

\`\`\`lean
def residualPrefunctor
    (F : C ⥤ D) (a : F.obj X ⟶ F.obj Y) :
    ResidualObj C ⥤q D where
  obj A := F.obj A
  map := by
    intro A B e
    cases e with
    | old f => exact F.map f
    | seed => exact a

def residualFreeEval
    (F : C ⥤ D) (a : F.obj X ⟶ F.obj Y) :
    ResidualFree C X Y ⥤ D :=
  CategoryTheory.Paths.lift (residualPrefunctor F a)
\`\`\`

- [ ] **Step 3: Prove old equations are respected and descend**

Prove:

\`\`\`lean
theorem residualFreeEval_respects
    (F : C ⥤ D) (a : F.obj X ⟶ F.obj Y) :
    ∀ A B (p q : A ⟶ B),
      ResidualRel C X Y p q →
      (residualFreeEval F a).map p =
        (residualFreeEval F a).map q
\`\`\`

by cases on \`ResidualRel\`; use \`F.map_id\`, \`F.map_comp\`, and the simp lemmas for \`Paths.lift_toPath\`.

Then:

\`\`\`lean
def residualAdjoinLift
    (F : C ⥤ D) (a : F.obj X ⟶ F.obj Y) :
    ResidualAdjoin C X Y ⥤ D :=
  CategoryTheory.Quotient.lift
    (ResidualRel C X Y)
    (residualFreeEval F a)
    (residualFreeEval_respects F a)
\`\`\`

- [ ] **Step 4: Prove extension and seed equations**

Required exact statements:

\`\`\`lean
theorem residualAdjoin_agrees
    (F : C ⥤ D) (a : F.obj X ⟶ F.obj Y) :
    residualInclusion C X Y ⋙ residualAdjoinLift F a = F

theorem residualAdjoin_seed
    (F : C ⥤ D) (a : F.obj X ⟶ F.obj Y) :
    (residualAdjoinLift F a).map (residualSeed C X Y) = a
\`\`\`

For the first theorem use \`Functor.ext\`; object equality is reflexive and map equality reduces to \`CategoryTheory.Quotient.lift_map_functor_map\` plus \`Paths.lift_toPath\`.

- [ ] **Step 5: Prove uniqueness**

State:

\`\`\`lean
theorem residualAdjoin_unique
    (F : C ⥤ D) (a : F.obj X ⟶ F.obj Y)
    (K : ResidualAdjoin C X Y ⥤ D)
    (hK : residualInclusion C X Y ⋙ K = F)
    (hseed : K.map (residualSeed C X Y) = a) :
    K = residualAdjoinLift F a
\`\`\`

Proof route:

1. apply \`CategoryTheory.Quotient.lift_unique'\` to reduce equality of functors from the quotient to equality after precomposition with the quotient projection;
2. use \`CategoryTheory.Paths.lift_unique\` on the augmented quiver;
3. for a generator \`ResidualEdge.old f\`, rewrite with \`hK\`;
4. for \`ResidualEdge.seed\`, rewrite with \`hseed\`.

Expose:

\`\`\`lean
theorem residualAdjoin_universal
    (F : C ⥤ D) (a : F.obj X ⟶ F.obj Y) :
    ∃! K : ResidualAdjoin C X Y ⥤ D,
      residualInclusion C X Y ⋙ K = F ∧
      K.map (residualSeed C X Y) = a
\`\`\`

using \`residualAdjoinLift\` for existence and \`residualAdjoin_unique\` for uniqueness.

- [ ] **Step 6: Run the residual universal-property tests**

Run: \`cd qcklean && lake env lean Nucleus/ResidualAdjoinTest.lean\`

Expected: PASS.

- [ ] **Step 7: Commit the fresh-arrow universal property**

\`\`\`bash
git add qcklean/Nucleus/ResidualAdjoin.lean qcklean/Nucleus/ResidualAdjoinTest.lean
git commit -m "feat(nucleus): prove residual fresh-arrow universal property"
\`\`\`

### Task 7: Warranted quotient after residual attachment

**Files:**
- Create: \`qcklean/Nucleus/DevelopmentTest.lean\`
- Create: \`qcklean/Nucleus/Development.lean\`

**Interfaces:**
- Consumes: \`ResidualAdjoin\` and Mathlib quotient-category APIs.
- Produces: \`WarrantedRelations\`, \`DevelopmentStep\`, \`developmentProjection\`, \`development_descend\`, and \`development_descend_unique\`.

- [ ] **Step 1: Write the failing development interface test**

\`\`\`lean
-- qcklean/Nucleus/DevelopmentTest.lean
import Nucleus.Development

open CategoryTheory
open Nucleus

#check WarrantedRelations
#check DevelopmentStep
#check developmentProjection
#check development_descend
#check development_descend_unique
\`\`\`

- [ ] **Step 2: Run and verify RED**

Run: \`cd qcklean && lake env lean Nucleus/DevelopmentTest.lean\`

Expected: FAIL because \`Nucleus.Development\` is missing.

- [ ] **Step 3: Define a supplied warranted congruence and the developmental quotient**

\`\`\`lean
-- qcklean/Nucleus/Development.lean
import Nucleus.ResidualAdjoin

namespace Nucleus

open CategoryTheory

universe u v

structure WarrantedRelations
    (C : Type u) [Category.{v} C] (X Y : C) where
  rel : HomRel (ResidualAdjoin C X Y)
  congruence : CategoryTheory.Congruence rel

attribute [instance] WarrantedRelations.congruence

abbrev DevelopmentStep
    (W : WarrantedRelations C X Y) :=
  CategoryTheory.Quotient W.rel

def developmentProjection
    (W : WarrantedRelations C X Y) :
    ResidualAdjoin C X Y ⥤ DevelopmentStep W :=
  CategoryTheory.Quotient.functor W.rel
\`\`\`

The congruence is evidence supplied by the verifier boundary. Do not add a search procedure.

- [ ] **Step 4: Expose the second universal factorization**

\`\`\`lean
def development_descend
    (W : WarrantedRelations C X Y)
    (F : ResidualAdjoin C X Y ⥤ D)
    (hF : ∀ A B (p q : A ⟶ B), W.rel p q → F.map p = F.map q) :
    DevelopmentStep W ⥤ D :=
  CategoryTheory.Quotient.lift W.rel F hF

theorem development_descend_unique
    (W : WarrantedRelations C X Y)
    (F : ResidualAdjoin C X Y ⥤ D)
    (hF : ∀ A B (p q : A ⟶ B), W.rel p q → F.map p = F.map q)
    (K : DevelopmentStep W ⥤ D)
    (hK : developmentProjection W ⋙ K = F) :
    K = development_descend W F hF :=
  CategoryTheory.Quotient.lift_unique W.rel F hF K hK
\`\`\`

Add a theorem \`developmentStep_two_stage\` whose conclusion records both:
- \`residualAdjoin_universal\` for the free attachment; and
- \`development_descend_unique\` for the warranted quotient.

Do not collapse these into one opaque constructor.

- [ ] **Step 5: Run and verify GREEN**

Run: \`cd qcklean && lake env lean Nucleus/DevelopmentTest.lean\`

Expected: PASS.

- [ ] **Step 6: Commit the free-then-quotient developmental step**

\`\`\`bash
git add qcklean/Nucleus/Development.lean qcklean/Nucleus/DevelopmentTest.lean
git commit -m "feat(nucleus): formalize free then warranted quotient development"
\`\`\`

### Task 8: Direct generator growth versus inverse behavioural refinement

**Files:**
- Create: \`qcklean/Nucleus/TemporalTest.lean\`
- Create: \`qcklean/Nucleus/Temporal.lean\`

**Interfaces:**
- Consumes: Mathlib quotient categories and the residual inclusion.
- Produces: \`RelationRefines\`, \`forgetRefinement\`, \`forgetRefinement_commutes\`, and \`residualGrowth_forward\`.

- [ ] **Step 1: Write the failing temporal-direction test**

\`\`\`lean
-- qcklean/Nucleus/TemporalTest.lean
import Nucleus.Temporal

open CategoryTheory
open Nucleus

#check RelationRefines
#check forgetRefinement
#check forgetRefinement_commutes
#check residualGrowth_forward
\`\`\`

- [ ] **Step 2: Run and verify RED**

Run: \`cd qcklean && lake env lean Nucleus/TemporalTest.lean\`

Expected: FAIL because \`Nucleus.Temporal\` is missing.

- [ ] **Step 3: Implement the canonical inverse refinement functor**

\`\`\`lean
-- qcklean/Nucleus/Temporal.lean
import Nucleus.Development

namespace Nucleus

open CategoryTheory

universe u v

def RelationRefines
    {C : Type u} [Category.{v} C]
    (rNew rOld : HomRel C) : Prop :=
  ∀ A B (f g : A ⟶ B), rNew f g → rOld f g

def forgetRefinement
    {C : Type u} [Category.{v} C]
    (rNew rOld : HomRel C)
    [CategoryTheory.Congruence rNew]
    [CategoryTheory.Congruence rOld]
    (h : RelationRefines rNew rOld) :
    CategoryTheory.Quotient rNew ⥤
      CategoryTheory.Quotient rOld :=
  CategoryTheory.Quotient.lift rNew
    (CategoryTheory.Quotient.functor rOld)
    (fun A B f g hfg =>
      CategoryTheory.Quotient.sound rOld (h A B f g hfg))
\`\`\`

- [ ] **Step 4: Prove the direction is forced**

\`\`\`lean
theorem forgetRefinement_commutes
    (h : RelationRefines rNew rOld) :
    CategoryTheory.Quotient.functor rNew ⋙
      forgetRefinement rNew rOld h =
    CategoryTheory.Quotient.functor rOld :=
  CategoryTheory.Quotient.lift_spec _ _ _

def residualGrowth_forward
    (C : Type u) [Category.{v} C] (X Y : C) :
    C ⥤ ResidualAdjoin C X Y :=
  residualInclusion C X Y
\`\`\`

Add a test with two explicit relations where \`rNew\` is strictly finer than \`rOld\`; assert the only canonical theorem produced here has type \`Quotient rNew ⥤ Quotient rOld\`.

- [ ] **Step 5: Run and verify GREEN**

Run: \`cd qcklean && lake env lean Nucleus/TemporalTest.lean\`

Expected: PASS.

- [ ] **Step 6: Commit the temporal-direction theorem**

\`\`\`bash
git add qcklean/Nucleus/Temporal.lean qcklean/Nucleus/TemporalTest.lean
git commit -m "feat(nucleus): separate growth from behavioural refinement"
\`\`\`

### Task 9: Mandatory falsifiers and integrated finite qualification fixtures

**Files:**
- Modify: \`qcklean/Nucleus/Fixtures.lean\`
- Create: \`qcklean/Nucleus/FixturesTest.lean\`

**Interfaces:**
- Consumes: every public layer through \`Nucleus.Temporal\`.
- Produces: named executable witnesses for all five mandatory negative cases and one positive end-to-end generators→quotient→fresh-arrow fixture.

- [ ] **Step 1: Write the failing integrated fixture test**

\`\`\`lean
-- qcklean/Nucleus/FixturesTest.lean
import Nucleus.Temporal
import Nucleus.Fixtures

open CategoryTheory
open Nucleus
open Nucleus.Fixtures

#check future_context_required
#check all_source_states_required
#check free_not_minimal_fixture
#check noncongruent_relation_rejected
#check fresh_arrow_not_ambient
#check positive_nucleus_factorization
#check positive_residual_extension
\`\`\`

- [ ] **Step 2: Run and verify RED**

Run: \`cd qcklean && lake env lean Nucleus/FixturesTest.lean\`

Expected: FAIL on the new public fixture theorem names.

- [ ] **Step 3: Complete the five negative fixtures**

In \`Fixtures.lean\` add:

1. \`future_context_required\`: immediate observation equality holds for two paths, but \`PathBehEq\` fails because a one-edge continuation separates them.
2. \`all_source_states_required\`: a one-source-state relation holds at the distinguished input but \`PathBehEq\` fails at another input.
3. \`free_not_minimal_fixture\`: two distinct parallel singleton paths are unequal in \`FreeCategory\`, a supplied warranted congruence identifies them, and their images become equal under the quotient projection.
4. \`noncongruent_relation_rejected\`: define an equivalence relation on one hom-set that is not stable under postcomposition and prove no \`CategoryTheory.Congruence\` instance can be constructed by deriving contradiction from \`HomRel.comp_right\`.
5. \`fresh_arrow_not_ambient\`: reuse the identity-only two-object category to prove \`IsEmpty (x ⟶ y)\` in the source while \`residualSeed\` inhabits the adjoined hom.

Each theorem must be proved from concrete finite data; no local axiom or opaque proposition is allowed.

- [ ] **Step 4: Add one positive integrated fixture**

Construct:

- a finite quiver with two generators;
- a concrete \`PathAction\` and protected observation;
- a \`ValidGen\` into a small target category that respects the warranted path equations;
- the descended functor from \`nucleus_universal\`;
- a source category with a certified fresh-arrow extension and target interpretation.

Expose:

\`\`\`lean
theorem positive_nucleus_factorization :
  nucleusProjection A Obs observe ⋙
    validGenToNucleus A Obs observe validGen =
  freeNucleus_lift G validGen.gen

theorem positive_residual_extension :
  residualInclusion C X Y ⋙ residualAdjoinLift F a = F ∧
    (residualAdjoinLift F a).map (residualSeed C X Y) = a
\`\`\`

- [ ] **Step 5: Run all Nucleus tests**

Run:
\`\`\`bash
cd qcklean
for file in Nucleus/*Test.lean; do
  lake env lean "$file"
done
\`\`\`

Expected: every test exits 0.

- [ ] **Step 6: Commit the falsification suite**

\`\`\`bash
git add qcklean/Nucleus/Fixtures.lean qcklean/Nucleus/FixturesTest.lean
git commit -m "test(nucleus): add universal-property falsifiers"
\`\`\`

### Task 10: Lake roots, theorem audit, frozen-source guard, and CI qualification

**Files:**
- Create: \`qcklean/Nucleus/Audit.lean\`
- Modify: \`qcklean/lakefile.lean\`
- Create: \`.github/workflows/nucleus-universal-property-v0.yml\`

**Interfaces:**
- Consumes: entire Nucleus theorem surface.
- Produces: a reproducible green qualification gate and axiom report.

- [ ] **Step 1: Write the audit file**

\`\`\`lean
-- qcklean/Nucleus/Audit.lean
import Nucleus.Temporal
import Nucleus.Fixtures

#print axioms Nucleus.freeNucleus_lift_unique
#print axioms Nucleus.pathBehEq_congruence
#print axioms Nucleus.nucleusProjection_exact
#print axioms Nucleus.nucleus_descend_unique
#print axioms Nucleus.nucleus_universal
#print axioms Nucleus.residualAdjoin_universal
#print axioms Nucleus.development_descend_unique
#print axioms Nucleus.forgetRefinement_commutes
#print axioms Nucleus.Fixtures.future_context_required
#print axioms Nucleus.Fixtures.all_source_states_required
#print axioms Nucleus.Fixtures.fresh_arrow_not_ambient
\`\`\`

- [ ] **Step 2: Extend the Lake roots**

Append these roots to the existing \`QCK\` library root array without removing or reordering existing QCK/CLC roots:

\`\`\`lean
    \`Nucleus.Quiver, \`Nucleus.QuiverTest,
    \`Nucleus.Free, \`Nucleus.FreeTest,
    \`Nucleus.PathBehavior, \`Nucleus.PathBehaviorTest,
    \`Nucleus.Quotient, \`Nucleus.QuotientTest,
    \`Nucleus.Universal, \`Nucleus.UniversalTest,
    \`Nucleus.ResidualAdjoin, \`Nucleus.ResidualAdjoinTest,
    \`Nucleus.Development, \`Nucleus.DevelopmentTest,
    \`Nucleus.Temporal, \`Nucleus.TemporalTest,
    \`Nucleus.Fixtures, \`Nucleus.FixturesTest,
    \`Nucleus.Audit
\`\`\`

- [ ] **Step 3: Run the clean local qualification**

Run:
\`\`\`bash
cd qcklean
lake update
lake exe cache get
lake build QCK
for file in Nucleus/*Test.lean; do lake env lean "$file"; done
lake env lean Nucleus/Audit.lean
\`\`\`

Expected:
- build exits 0;
- every Nucleus test exits 0;
- audit prints no \`sorryAx\`;
- theorem dependencies are limited to Lean/Mathlib foundations accepted by the existing repository policy.

- [ ] **Step 4: Run the source placeholder scan**

Run:
\`\`\`bash
cd qcklean
! grep -RInE '(^|[^[:alnum:]_])(sorry|admit|axiom|constant|unsafe)([^[:alnum:]_]|$)' Nucleus \
  | grep -vE '^[^:]+:[0-9]+:[[:space:]]*#print[[:space:]]+axioms([[:space:]]|$)'
\`\`\`

Expected: exit 0 with no forbidden source declaration.

- [ ] **Step 5: Verify frozen QCK and CLC sources**

Run from repository root:

\`\`\`bash
git diff --exit-code 900a73c1d386ee0eee1205a1cf31d270f3311ef7 -- 'qcklean/QCK*.lean' 'qcklean/CLC/**'
test "$(git hash-object qcklean/QCKCore.lean)" = "b9b1921c49c9947a02009be124286cfe3c723cb4"
\`\`\`

Expected: no diff and exact QCKCore blob hash match.

- [ ] **Step 6: Add the dedicated GitHub Actions workflow**

Create \`.github/workflows/nucleus-universal-property-v0.yml\` with:

\`\`\`yaml
name: Nucleus Universal Property V0

on:
  push:
    branches: [nucleus-universal-property-v0]
    paths:
      - 'qcklean/**'
      - 'docs/superpowers/specs/2026-09-21-nucleus-universal-property-v0-design.md'
      - 'docs/superpowers/plans/2026-09-21-nucleus-universal-property-v0.md'
      - '.github/workflows/nucleus-universal-property-v0.yml'
  workflow_dispatch:

permissions:
  contents: read

jobs:
  nucleus-v0:
    runs-on: ubuntu-24.04
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Verify frozen QCK and CLC sources
        run: |
          set -euo pipefail
          test "$(git hash-object qcklean/QCKCore.lean)" = "b9b1921c49c9947a02009be124286cfe3c723cb4"
          git diff --exit-code 900a73c1d386ee0eee1205a1cf31d270f3311ef7 -- \
            'qcklean/QCK*.lean' 'qcklean/CLC/**'

      - name: Install Lean via elan
        run: |
          curl https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh -sSf | sh -s -- -y
          echo "$HOME/.elan/bin" >> "$GITHUB_PATH"

      - name: Fetch pinned Mathlib
        working-directory: qcklean
        run: |
          lake update
          lake exe cache get

      - name: Reject placeholders and local axioms
        working-directory: qcklean
        run: |
          set -euo pipefail
          ! grep -RInE '(^|[^[:alnum:]_])(sorry|admit|axiom|constant|unsafe)([^[:alnum:]_]|$)' Nucleus \
            | grep -vE '^[^:]+:[0-9]+:[[:space:]]*#print[[:space:]]+axioms([[:space:]]|$)'

      - name: Build QCK, CLC, and Nucleus
        working-directory: qcklean
        run: lake build QCK

      - name: Run every Nucleus interface and fixture test
        working-directory: qcklean
        run: |
          set -euo pipefail
          for file in Nucleus/*Test.lean; do
            lake env lean "$file"
          done

      - name: Audit Nucleus theorem dependencies
        working-directory: qcklean
        run: |
          set -euo pipefail
          lake env lean Nucleus/Audit.lean 2>&1 | tee /tmp/nucleus-axioms.log
          ! grep -E 'sorryAx' /tmp/nucleus-axioms.log
          if grep -F 'depends on axioms:' /tmp/nucleus-axioms.log \
            | grep -vE "depends on axioms: \[(propext|Classical\.choice|Quot\.sound)(, (propext|Classical\.choice|Quot\.sound))*\]$"; then
            echo "Unexpected foundational dependency detected"
            exit 1
          fi
\`\`\`

- [ ] **Step 7: Commit the qualification harness**

\`\`\`bash
git add qcklean/Nucleus/Audit.lean qcklean/lakefile.lean \
  .github/workflows/nucleus-universal-property-v0.yml
git commit -m "ci(nucleus): qualify universal property V0"
\`\`\`

- [ ] **Step 8: Push and inspect the remote run**

Run:

\`\`\`bash
git push origin nucleus-universal-property-v0
\`\`\`

Then inspect the triggered \`Nucleus Universal Property V0\` workflow.

Expected: overall GitHub Actions conclusion \`success\`; frozen-source guard, build, all Nucleus tests, placeholder scan, and axiom audit all green.

- [ ] **Step 9: Record the final theorem boundary in the branch summary**

Add no new proof claims. Report only:

\[
\boxed{
\text{free generation}
+
\text{warranted path congruence}
=
\text{universal consequential presentation}
}
\]

under the finite/quiver/path assumptions of the spec, plus the separate theorem that one fresh residual arrow is the least extension with its stated endpoints. Explicitly repeat that object genesis, infinite colimits, automatic residual discovery, and completeness of warrant remain deferred.

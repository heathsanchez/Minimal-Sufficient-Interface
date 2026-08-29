import UnifiedDevelopmentalLaw

universe u z

namespace BoundedDevelopmentalCapability

open TypedBehaviouralCongruence
open DevelopmentalCategory
open GeneratedStage
open VerifiedConsequenceGenesis
open UnifiedDevelopmentalLaw

/-- A fixed one-query controller.  Its only proposal is the canonical immediate
    descendant of `seed`; it returns that proposal exactly when the current
    language can express it and the external verifier accepts it.

    This is intentionally a minimal bounded-search semantics: budget = 1,
    proposal rule frozen, verifier arbitrary. -/
noncomputable def oneQueryController
    {A : Type u}
    (L : Lang A) (seed : A) (verify : Expr A → Prop) : Option (Expr A) := by
  classical
  let candidate : Expr A := .op (.atom seed)
  exact if Expressible L candidate ∧ verify candidate then some candidate else none

/-- Promotion changes an actual bounded controller result, not merely an
    abstract expressibility predicate.  If `seed` was absent before promotion
    and the verifier accepts its immediate descendant, the same frozen
    one-query controller fails cold and succeeds warm. -/
theorem promotion_changes_one_query_controller
    {A : Type u}
    (L : Lang A) (seed : A) (verify : Expr A → Prop)
    (hmissing : ¬ L seed)
    (hverify : verify (.op (.atom seed))) :
    oneQueryController (Promote L seed) seed verify = some (.op (.atom seed)) ∧
    oneQueryController L seed verify = none := by
  constructor
  · unfold oneQueryController
    simp [promotion_enables_descendant L seed, hverify]
  · unfold oneQueryController
    have hblocked : ¬ Expressible L (.op (.atom seed)) :=
      ancestral_ablation_blocks_descendant L seed hmissing
    simp [hblocked]

/-- Full verified developmental cycle with bounded capability change.

    The same separator morphism `seed` drives every stage:
    * it exposes a consequence that cannot factor through the old quotient;
    * canonical product repair equals meet/kernel refinement;
    * adjoining it gives the least composition-closed stage extension;
    * promoting that same seed changes the structural frontier;
    * under a frozen one-query proposal rule and arbitrary accepting verifier,
      the promoted system returns the verified descendant while exact ancestor
      ablation returns failure.

    This closes the formal gap between structural promotion and a concrete
    resource-bounded controller outcome.  It does not claim optimal search,
    learning of the proposal rule, or a universal efficiency improvement. -/
theorem verified_consequence_changes_bounded_capability
    (C : SmallCategory)
    (A : Action C)
    (Obs : C.Obj → Type z)
    (observe : ∀ X, A.State X → Obs X)
    (S : Stage C)
    {X Y : C.Obj} {x y : A.State X}
    (seed : C.Hom X Y)
    (L : Lang (C.Hom X Y))
    (verify : Expr (C.Hom X Y) → Prop)
    (hold : BehEqAt C A Obs observe S X x y)
    (hsep : observe Y (A.map seed x) ≠ observe Y (A.map seed y))
    (hmissing : ¬ L seed)
    (hverify : verify (.op (.atom seed))) :
    let q := stageRepresentation C A Obs observe S X
    let c := seedConsequence C A Obs observe seed
    let O2 : Expr (C.Hom X Y) := .op (.atom seed)
    (((¬ FactorsThrough q c) ∧
        FactorsThrough (RefineWith q c) c ∧
        (RefinedEqRel q c =
          (relationMeetKernel (A.State X)).meet (EqRel q) (ConsequenceKernel c)) ∧
        Extends C S (adjoinStage C S seed) ∧
        (∀ T : Stage C, Extends C S T → T.allow seed →
          Extends C (adjoinStage C S seed) T) ∧
        (BehEqAt C A Obs observe S X x y ∧
          ¬ BehEqAt C A Obs observe (adjoinStage C S seed) X x y)) ∧
      Expressible (Promote L seed) O2 ∧
      ¬ Expressible L O2) ∧
    oneQueryController (Promote L seed) seed verify = some O2 ∧
    oneQueryController L seed verify = none := by
  dsimp
  constructor
  · exact verified_consequence_forces_recursive_promotion_cycle
      C A Obs observe S seed L hold hsep hmissing
  · exact promotion_changes_one_query_controller L seed verify hmissing hverify

end BoundedDevelopmentalCapability

#check BoundedDevelopmentalCapability.oneQueryController
#check BoundedDevelopmentalCapability.promotion_changes_one_query_controller
#check BoundedDevelopmentalCapability.verified_consequence_changes_bounded_capability

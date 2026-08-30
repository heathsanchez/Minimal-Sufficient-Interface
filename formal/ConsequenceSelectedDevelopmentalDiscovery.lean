import GeneratedCandidateDevelopmentalSearch
import UnifiedDevelopmentalLaw

universe z

namespace ConsequenceSelectedDevelopmentalDiscovery

open VerifiedConsequenceGenesis
open TypedBehaviouralCongruence
open DevelopmentalCategory
open GeneratedStage
open UnifiedDevelopmentalLaw
open MultiCandidateDevelopmentalSearch
open GeneratedCandidateDevelopmentalSearch

/-- Frozen selector over an anonymous primitive pool.  It knows no privileged
    primitive identity: it returns the first morphism whose *actual observed
    consequence* separates the currently compared states. -/
noncomputable def selectFirstSeparator
    (C : SmallCategory)
    (A : Action C)
    (Obs : C.Obj → Type z)
    (observe : ∀ X, A.State X → Obs X)
    {X Y : C.Obj} (x y : A.State X) :
    List (C.Hom X Y) → Option (C.Hom X Y)
  | [] => none
  | h :: rest => by
      classical
      exact if observe Y (A.map h x) ≠ observe Y (A.map h y) then
        some h
      else
        selectFirstSeparator C A Obs observe x y rest

/-- If the first anonymous primitive is observationally silent and the second
    is a genuine consequential separator, the frozen selector recovers the
    separator from verifier-observable consequences alone. -/
theorem selector_recovers_separator_from_consequence
    (C : SmallCategory)
    (A : Action C)
    (Obs : C.Obj → Type z)
    (observe : ∀ X, A.State X → Obs X)
    {X Y : C.Obj} (x y : A.State X)
    (decoy seed : C.Hom X Y)
    (hdecoySilent : observe Y (A.map decoy x) = observe Y (A.map decoy y))
    (hseedSep : observe Y (A.map seed x) ≠ observe Y (A.map seed y)) :
    selectFirstSeparator C A Obs observe x y [decoy, seed] = some seed := by
  classical
  simp [selectFirstSeparator, hdecoySilent, hseedSep]

/-- The complete frozen controller.  It first discovers a separator from the
    anonymous primitive pool, promotes exactly the selected primitive, asks the
    generic grammar generator for candidates, then runs the fixed bounded
    verifier search.  No winning compound expression and no winning primitive
    identity are supplied to this controller. -/
noncomputable def selectedPromotionSearch
    (C : SmallCategory)
    (A : Action C)
    (Obs : C.Obj → Type z)
    (observe : ∀ X, A.State X → Obs X)
    {X Y : C.Obj} (x y : A.State X)
    (L : Lang (C.Hom X Y))
    (verify : Expr (C.Hom X Y) → Prop)
    (budget : Nat)
    (pool : List (C.Hom X Y)) : Option (Expr (C.Hom X Y)) :=
  match selectFirstSeparator C A Obs observe x y pool with
  | none => boundedSearch L verify budget (generateDepthOne L pool)
  | some selected =>
      boundedSearch (Promote L selected) verify budget
        (generateDepthOne (Promote L selected) pool)

/-- Final integrated developmental-discovery theorem.

    Under one frozen protocol, an anonymous primitive pool contains a silent
    decoy followed by a genuine verified separator.  The current stage treats
    `x` and `y` as behaviourally equivalent.  The controller:

    1. selects the separator solely because its actual consequence distinguishes
       the currently collapsed pair;
    2. thereby inherits the already-proved non-factorization, canonical meet
       repair, least generated stage extension, and strict behavioural split;
    3. promotes the *selected* primitive rather than a supplied identity;
    4. lets the same generic grammar generator create the descendant;
    5. discovers that descendant with the same frozen bounded verifier search;
    6. fails under exact cold ancestor ablation.

    Thus the primitive identity, compound candidate, grammar expansion,
    verifier, search rule, and budget are all causally separated. -/
theorem verified_consequence_selects_promotes_generates_and_discovers
    (C : SmallCategory)
    (A : Action C)
    (Obs : C.Obj → Type z)
    (observe : ∀ X, A.State X → Obs X)
    (S : Stage C)
    {X Y : C.Obj} {x y : A.State X}
    (decoy seed : C.Hom X Y)
    (L : Lang (C.Hom X Y))
    (verify : Expr (C.Hom X Y) → Prop)
    (hold : BehEqAt C A Obs observe S X x y)
    (hdecoySilent : observe Y (A.map decoy x) = observe Y (A.map decoy y))
    (hseedSep : observe Y (A.map seed x) ≠ observe Y (A.map seed y))
    (hdecoyPresent : L decoy)
    (hseedMissing : ¬ L seed)
    (hrejectDecoyAtom : ¬ verify (.atom decoy))
    (hrejectDecoyOp : ¬ verify (.op (.atom decoy)))
    (hrejectSeedAtom : ¬ verify (.atom seed))
    (hacceptDescendant : verify (.op (.atom seed))) :
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
    selectFirstSeparator C A Obs observe x y [decoy, seed] = some seed ∧
    selectedPromotionSearch C A Obs observe x y L verify 4 [decoy, seed] = some O2 ∧
    boundedSearch L verify 4 (generateDepthOne L [decoy, seed]) = none := by
  dsimp
  have hcycle := verified_consequence_forces_recursive_promotion_cycle
    C A Obs observe S seed L hold hseedSep hseedMissing
  have hselect := selector_recovers_separator_from_consequence
    C A Obs observe x y decoy seed hdecoySilent hseedSep
  have hcap := promotion_changes_generated_multicandidate_capability
    L decoy seed verify hdecoyPresent hseedMissing
    hrejectDecoyAtom hrejectDecoyOp hrejectSeedAtom hacceptDescendant
  constructor
  · exact hcycle
  constructor
  · exact hselect
  constructor
  · simpa [selectedPromotionSearch, hselect] using hcap.1
  · exact hcap.2

end ConsequenceSelectedDevelopmentalDiscovery

#check ConsequenceSelectedDevelopmentalDiscovery.selectFirstSeparator
#check ConsequenceSelectedDevelopmentalDiscovery.selector_recovers_separator_from_consequence
#check ConsequenceSelectedDevelopmentalDiscovery.selectedPromotionSearch
#check ConsequenceSelectedDevelopmentalDiscovery.verified_consequence_selects_promotes_generates_and_discovers

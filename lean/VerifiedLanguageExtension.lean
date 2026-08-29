import Std
import GeneratedStage
import DevelopmentalFailureTaxonomy

universe u v w z

namespace VerifiedLanguageExtension

open DevelopmentalFailureTaxonomy
open VerifiedDevelopment
open GeneratedStage
open DevelopmentalCategory
open TypedBehaviouralCongruence

/-- One-step language extension: retain the old atoms and adjoin exactly one
    verifier-licensed atom. -/
def Adjoin {Atom : Type u} (a : Atom) (L : List Atom) : List Atom := a :: L

/-- A capability is a strict expressibility gain when it is impossible in the
    old generated language but expressible after adjoining one licensed atom. -/
def StrictExpressibilityGain {Atom : Type u} {Cap : Type v}
    (G : PromotionLanguage Atom Cap) (L : List Atom) (a : Atom) (c : Cap) : Prop :=
  ¬ G.Expresses L c ∧ G.Expresses (Adjoin a L) c

/-- A certified closure obstruction rules out every search confined to the old
    language, because the target is not in that language's expressible set. -/
theorem closure_obstruction_rules_out_old_language_search
    {Atom : Type u} {Cap : Type v}
    (G : PromotionLanguage Atom Cap) (L : List Atom) (c : Cap)
    (hclose : ClosureObstruction G L c) :
    ¬ G.Expresses L c := by
  exact hclose

/-- If a verifier-licensed atom makes a closure-obstructed capability
    expressible, the change is a genuine language extension rather than a
    different search path inside the old language. -/
theorem verified_constructor_forces_strict_extension
    {Atom : Type u} {Cap : Type v}
    (G : PromotionLanguage Atom Cap) (L : List Atom) (a : Atom) (c : Cap)
    (hclose : ClosureObstruction G L c)
    (hwarm : G.Expresses (Adjoin a L) c) :
    StrictExpressibilityGain G L a c := by
  exact ⟨hclose, hwarm⟩

/-- The same evidence packages directly as the strict-promotion witness already
    used by the developmental controller. -/
theorem strict_extension_is_strict_promotion
    {Atom : Type u} {Cap : Type v}
    (G : PromotionLanguage Atom Cap) (L : List Atom) (a : Atom) (c : Cap)
    (h : StrictExpressibilityGain G L a c) :
    StrictPromotion G L a c := by
  exact { cold := h.1, warm := h.2 }

/-- At the typed developmental-stage level, adjoining one licensed morphism is
    canonical and least: every composition-closed stage extending the old stage
    and containing the seed must contain the generated extension. -/
theorem licensed_morphism_extension_is_least
    (C : SmallCategory) (S T : Stage C)
    {X Y : C.Obj} (seed : C.Hom X Y)
    (hST : Extends C S T) (hseed : T.allow seed) :
    Extends C (adjoinStage C S seed) T := by
  exact adjoin_least C S T seed hST hseed

/-- Combined EXTEND law. A closure certificate rules out the old language; a
    verified constructor creates a strict expressibility gain; and at the stage
    level the corresponding one-seed generated extension is the least lawful
    composition-closed extension containing that seed. -/
theorem verified_extend_law
    {Atom : Type u} {Cap : Type v}
    (G : PromotionLanguage Atom Cap) (L : List Atom) (a : Atom) (c : Cap)
    (hclose : ClosureObstruction G L c)
    (hwarm : G.Expresses (Adjoin a L) c) :
    ¬ G.Expresses L c ∧ G.Expresses (Adjoin a L) c := by
  exact ⟨hclose, hwarm⟩

end VerifiedLanguageExtension

import Std
import ObservationalSeparation

/-! # Ontology extension — verified failure forces a new representational domain

  `ResidualMiner` proved "verified failure forces a new observable" within a fixed
  object type.  This file closes the harder gap: the current ontology is a
  FORMALLY COMPLETE observation language (an inductive syntax, closed under the
  admissible combinators), and yet a verifier-certified residual is inexpressible
  in it.  Then no distinction *constructible* in the old ontology suffices, so the
  repair cannot be "add another feature" — it must enlarge the ontology itself.

  Micro-world: objects are `Bool × Bool`.  The OLD language sees only the first
  component (complete for it: `first b`, `not`, `and`); the NEW language adds a
  `second` observation.  The residual pair `p = (true,false)`, `q = (true,true)`
  has the same first component (so EVERY old observation collapses it) but differs
  in the second (so the new `second` observation separates it).

  Chain proved below (zero sorry/axiom):
    (1) completeness: every OLD observation collapses p,q — by induction on the
        whole OldObs syntax;
    (2) the verifier-certified continuation separates them;
    (3) no OLD observation resolves the residual;
    (4) ontology extension necessary (via the general separation kernel);
    (5) the minimally-enlarged ontology resolves it;
    (6) minimality: any resolving extension must add a genuinely new capability.
-/

namespace OntologyExtension

open ObservationalSeparation

abbrev Obj := Bool × Bool

/- OLD observation language: complete for the first component. -/
inductive OldObs : Type where
  | first : Bool → OldObs
  | not : OldObs → OldObs
  | and : OldObs → OldObs → OldObs
  deriving Repr

def semOld : OldObs → Obj → Bool
  | .first b, (a, _) => decide (a = b)
  | .not o, x => !semOld o x
  | .and o1 o2, x => semOld o1 x && semOld o2 x

/- NEW observation language: adds a second-component observation. -/
inductive NewObs : Type where
  | old : OldObs → NewObs
  | second : NewObs
  | not : NewObs → NewObs
  | and : NewObs → NewObs → NewObs
  deriving Repr

def semNew : NewObs → Obj → Bool
  | .old o, x => semOld o x
  | .second, (_, b) => b
  | .not o, x => !semNew o x
  | .and o1 o2, x => semNew o1 x && semNew o2 x

/- The residual pair: same first component, different second. -/
def p : Obj := (true, false)
def q : Obj := (true, true)

/- COMPLETENESS (general): two objects with the same first component are
   indistinguishable by EVERY old observation.  Induction over the whole OldObs
   syntax — not a hand-picked list. -/
theorem same_first_collapses_all {x y : Obj} (h : x.1 = y.1) :
    ∀ o : OldObs, semOld o x = semOld o y := by
  intro o
  induction o with
  | first b => simpa [semOld] using congrArg (fun z : Bool => decide (z = b)) h
  | not o ih => simp [semOld, ih]
  | and o1 o2 ih1 ih2 => simp [semOld, ih1, ih2]

/- (1) The residual pair is collapsed by the complete old language. -/
theorem old_ontology_collapses : ∀ o : OldObs, semOld o p = semOld o q :=
  same_first_collapses_all (by rfl : p.1 = q.1)

/- The old-ontology observational family (realized old observations). -/
def OldFamily (b : Obj → Bool) : Prop := ∃ o : OldObs, b = semOld o

/- (2) The verifier-certified continuation separates the residual. -/
theorem second_separates : semNew .second p ≠ semNew .second q := by
  simp [semNew, p, q]

/- (3) No OLD observation resolves the residual. -/
theorem no_old_resolution : ¬ ∃ b, OldFamily b ∧ b p ≠ b q := by
  intro h
  rcases h with ⟨b, ⟨o, hb⟩, hsep⟩
  rw [hb] at hsep
  exact hsep (old_ontology_collapses o)

/- (4) Ontology extension necessary: every resolving family needs a separator
   OUTSIDE the complete old language. -/
theorem ontology_extension_necessary (B1 : (Obj → Bool) → Prop)
    (hresolve : ∃ b, B1 b ∧ b p ≠ b q) :
    ∃ b, B1 b ∧ ¬ OldFamily b ∧ b p ≠ b q :=
  forced_new_separator p q OldFamily B1
    (by intro b hb; rcases hb with ⟨o, ho⟩; rw [ho]; exact old_ontology_collapses o)
    hresolve

/- (5) The minimally-enlarged ontology resolves the residual (via `second`). -/
theorem new_ontology_resolves : ∃ b, (∃ o : NewObs, b = semNew o) ∧ b p ≠ b q := by
  refine ⟨semNew .second, ⟨.second, rfl⟩, ?_⟩
  exact second_separates

/- (6) Minimality: every satisfactory extension must add a capability not
   realizable in the old language — a genuinely new representational domain. -/
theorem extension_must_add_new_capability (B1 : (Obj → Bool) → Prop)
    (hresolve : ∃ b, B1 b ∧ b p ≠ b q) :
    ∃ b, B1 b ∧ ¬ (∃ o : OldObs, b = semOld o) ∧ b p ≠ b q :=
  ontology_extension_necessary B1 hresolve

end OntologyExtension

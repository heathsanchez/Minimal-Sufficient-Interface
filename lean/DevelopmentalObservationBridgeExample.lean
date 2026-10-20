import DevelopmentalObservationBridge
import VerifiedDevelopmentExample

/-!
Finite controls: R7.2's actual non-identity reveal action, not an identity-only
illustration. New observation values, witness and authority snapshots are
supplied by the test. This does not test autonomous observer invention.
-/

namespace DevelopmentalObservationBridgeExample

open DevelopmentalObservationBridge
open VerifiedDevelopmentExample
open ScopedCertificates

def oldQ (_ : Bool × Bool) : Unit := ()
def newD : Bool × Bool → Bool := visible
def oldEval (_ : Unit) (_ : Unit) : FiniteCLC.Verdict := .eq
def classify (d : Bool) : FiniteCLC.Verdict :=
  if d then .dist else .eq
def oldProtected (_ : Unit) : Bool := true

/-- Naive pointwise observation incorrectly merges this pair. -/
theorem pointwise_still_merges :
    (oldQ before, newD before) = (oldQ after, newD after) := by
  rfl

/-- History after R7.2's admitted non-identity reveal action separates them. -/
theorem future_history_splits :
    extended revealAction expandedStage oldQ newD before ≠
      extended revealAction expandedStage oldQ newD after := by
  apply future_separator_forces_split
    revealAction expandedStage oldQ newD true trivial
  exact actual_action_separates

/-- This is the constructed original CLC predicate, not a bespoke replacement. -/
theorem finite_clc_valid :
    FiniteCLC.Valid
      (sourceForm oldQ oldEval oldProtected)
      (targetForm revealAction expandedStage oldEval classify oldProtected)
      (extensionTransport revealAction expandedStage
        oldQ newD oldEval classify oldProtected) := by
  exact extensionTransport_valid
    revealAction expandedStage oldQ newD oldEval classify oldProtected

theorem old_known_test_preserved :
    (sourceForm oldQ oldEval oldProtected).eval before (some ()) =
      (targetForm revealAction expandedStage oldEval classify oldProtected).eval
        (extended revealAction expandedStage oldQ newD before) (.inl ()) := by
  apply old_decisive_preserved
    revealAction expandedStage oldQ newD oldEval classify oldProtected
    before ()
  decide

def sourceAuthority : AuthoritySnapshot Bool where
  signed := fun _ => True
  permitted := fun _ => True
  denied := fun _ => False

def noDependencies : Bool → Bool → Prop := fun _ _ => False

theorem alternate_originally_valid :
    Valid (eligible sourceAuthority) noDependencies true := by
  apply Valid.admit true
  · exact ⟨trivial, trivial, by intro h; exact False.elim h⟩
  · intro p hp; exact False.elim hp

/-- Revoking one proof invalidates that proof, not all equivalent claims. -/
theorem revoked_certificate_invalid :
    ¬ Valid (eligible (withdraw sourceAuthority false))
      noDependencies false := by
  exact withdraw_retracts_self sourceAuthority noDependencies false

theorem independent_certificate_remains :
    Valid (eligible (withdraw sourceAuthority false))
      noDependencies true := by
  apply independent_cone_survives sourceAuthority noDependencies true false
    alternate_originally_valid
  intro p h
  rcases h with hEq | hPath
  · subst p
    decide
  · cases hPath with
    | direct h => exact False.elim h
    | next h _ => exact False.elim h

/-- Two records can certify the same claim; a surviving alternative warrants it. -/
theorem current_claim_remains :
    ClaimWarrant (withdraw sourceAuthority false)
      noDependencies (fun _ : Bool => ()) () := by
  exact ⟨true, rfl, independent_certificate_remains⟩

/-- Current warrant cannot expand a separately denied permission ceiling. -/
theorem external_action_remains_denied :
    ¬ CanAct sourceAuthority noDependencies
      (fun _ : Unit => False) true () := by
  apply no_permission_escalation
    sourceAuthority noDependencies (fun _ : Unit => False) true ()
  intro h
  exact h

end DevelopmentalObservationBridgeExample

import Std

/-!
# Signature-generic developmental synthesis core

The domain signature, residual universe, observations, repair family, and repair
interpretation are parameters. `develop` is the one implementation that:

1. discovers the first inadequacy witness in the supplied finite universe;
2. synthesizes the least-ranked supplied discriminator that separates it;
3. replays adequacy under the quotient produced by that exact repair.
-/

namespace SynthesisCore

structure Candidate (α β tag : Type) where
  tag : tag
  rank : Nat
  disc : α → β

def minByRank {α β tag : Type} :
    List (Candidate α β tag) → Option (Candidate α β tag)
  | [] => none
  | [candidate] => some candidate
  | candidate :: rest =>
      match minByRank rest with
      | none => some candidate
      | some current =>
          some (if candidate.rank ≤ current.rank then candidate else current)

def synthesize {α β tag : Type} [DecidableEq β]
    (candidates : List (Candidate α β tag)) (left right : α) : Option tag :=
  match minByRank
      (candidates.filter fun candidate =>
        decide (candidate.disc left ≠ candidate.disc right)) with
  | none => none
  | some candidate => some candidate.tag

def adequacyWitnesses {α β γ : Type} [DecidableEq β] [DecidableEq γ]
    (univ : List α) (quotient : α → β) (protectedObs : α → γ) : List (α × α) :=
  (univ.flatMap fun left => univ.map fun right => (left, right)).filter fun pair =>
    decide
      (quotient pair.1 = quotient pair.2 ∧
        protectedObs pair.1 ≠ protectedObs pair.2)

structure DevelopmentOutcome (α tag : Type) where
  residual : α × α
  selected : tag
  replayResiduals : List (α × α)

/-- One causal discovery → synthesis → replay implementation. -/
def develop {α initialObs protectedObs discObs repairedObs tag : Type}
    [DecidableEq initialObs] [DecidableEq protectedObs]
    [DecidableEq discObs] [DecidableEq repairedObs]
    (univ : List α)
    (initialQuotient : α → initialObs)
    (protectedFunction : α → protectedObs)
    (candidates : List (Candidate α discObs tag))
    (repairQuotient : tag → α → repairedObs) : Option (DevelopmentOutcome α tag) :=
  match adequacyWitnesses univ initialQuotient protectedFunction with
  | [] => none
  | residual :: _ =>
      match synthesize candidates residual.1 residual.2 with
      | none => none
      | some selected =>
          some
            { residual := residual
              selected := selected
              replayResiduals :=
                adequacyWitnesses univ (repairQuotient selected) protectedFunction }

end SynthesisCore

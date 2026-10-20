import DevelopmentalObservationBridge
import VerifiedDevelopmentExample

/-!
# Effectful observation: old protected tests must survive the actual successor.

An observer instrument is NOT just a readout: it also changes the physical
state. A retained historical observation is not evidence that old tests on the
new live state retain their values. This module gives a *conditional* CLC
transport construction and a concrete destructive countercontrol.

Measurement availability, source authority, full instrument semantics,
verifier soundness and physical real-world truth remain separately qualified.
-/

namespace EffectfulObservationBridge

open DevelopmentalObservationBridge
open VerifiedDevelopmentCore

variable {M X Q D T : Type}

/-- One deterministic instrument for the declared finite formal interface. -/
structure Instrument (X D : Type) where
  read : X → D
  after : X → X

/-- Protected future observations are compared on the actual live successor. -/
def PreservesOldFutures (A : ActionMonoid M X) (S : Stage A)
    (q : X → Q) (I : Instrument X D) : Prop :=
  ∀ x m, S.allow m →
    q (A.act m (I.after x)) = q (A.act m x)

/-- If the old quotient is action-congruent, verifying the actual successor's
    q value suffices to preserve every frozen-stage future q observation. -/
theorem nondisturbance_implies_old_futures
    (A : ActionMonoid M X) (S : Stage A)
    (q : X → Q) (I : Instrument X D)
    (hInv : InvariantAt A S (fun x y => q x = q y))
    (hKeep : ∀ x, q (I.after x) = q x) :
    PreservesOldFutures A S q I := by
  intro x m hm
  exact hInv m hm (I.after x) x (hKeep x)

/-- The previous trace contract includes identity, so it necessarily protects
    the current q of the physical successor (not the archival trace alone). -/
theorem old_futures_imply_nondisturbance
    (A : ActionMonoid M X) (S : Stage A)
    (q : X → Q) (I : Instrument X D)
    (h : PreservesOldFutures A S q I) :
    ∀ x, q (I.after x) = q x := by
  intro x
  have hOne := h x A.one S.one_allow
  simpa [A.one_act] using hOne

/-- The target state records the actual live successor AND archived new
    observations. Old tests evaluate against live q, not against archived q. -/
def liveTargetForm (A : ActionMonoid M X) (S : Stage A)
    (q : X → Q)
    (valQ : Q → T → FiniteCLC.Verdict)
    (classify : D → FiniteCLC.Verdict)
    (oldProtected : T → Bool) :
    FiniteCLC.Form (X × (Q × (Allowed A S → D))) (T ⊕ Allowed A S) where
  eval := fun z p =>
    match p with
    | .inl t => valQ (q z.1) t
    | .inr m => classify (z.2.2 m)
  isProtected := fun p =>
    match p with
    | .inl t => oldProtected t
    | .inr _ => true

/-- An effectful transport has two distinct outputs:
    actual successor (live) and readout history (archival). -/
def instrumentTransport (A : ActionMonoid M X) (S : Stage A)
    (q : X → Q) (I : Instrument X D)
    (valQ : Q → T → FiniteCLC.Verdict)
    (classify : D → FiniteCLC.Verdict)
    (oldProtected : T → Bool) :
    FiniteCLC.Transport
      (sourceForm q valQ oldProtected)
      (liveTargetForm A S q valQ classify oldProtected) where
  forward := fun x => (I.after x, extended A S q I.read x)
  pull := fun p =>
    match p with
    | .inl t => some t
    | .inr _ => none
  lift := fun p =>
    match p with
    | none => .inr ⟨A.one, S.one_allow⟩
    | some t => .inl t

/-- Sufficient actual-state contract for constructed CLC Valid.
    In contrast with archival-only transport, a destructive instrument fails
    the old-test refinement obligation for a sufficiently discriminating valQ. -/
theorem instrument_transport_valid_of_nondisturbance
    (A : ActionMonoid M X) (S : Stage A)
    (q : X → Q) (I : Instrument X D)
    (valQ : Q → T → FiniteCLC.Verdict)
    (classify : D → FiniteCLC.Verdict)
    (oldProtected : T → Bool)
    (hKeep : ∀ x, q (I.after x) = q x) :
    FiniteCLC.Valid
      (sourceForm q valQ oldProtected)
      (liveTargetForm A S q valQ classify oldProtected)
      (instrumentTransport A S q I valQ classify oldProtected) := by
  constructor
  · intro x p
    cases p with
    | inl t =>
        apply Or.inr
        change valQ (q x) t = valQ (q (I.after x)) t
        exact congrArg (fun v : Q => valQ v t) (hKeep x).symm
    | inr m =>
        exact Or.inl rfl
  constructor
  · intro p hp
    cases p with
    | inl t => exact hp
    | inr m => rfl
  · intro p hp
    cases p with
    | none => exact ⟨rfl, rfl⟩
    | some t => exact ⟨hp, rfl⟩

/-- One conditional composite: semantic future refinement, genuine separating
    witness and CLC-valid preservation over the *physical* successor.
    The witness and nondisturbance contract are independently supplied. -/
theorem conditional_instrument_extension
    (A : ActionMonoid M X) (S : Stage A)
    (q : X → Q) (I : Instrument X D)
    (valQ : Q → T → FiniteCLC.Verdict)
    (classify : D → FiniteCLC.Verdict)
    (oldProtected : T → Bool)
    (hInv : InvariantAt A S (fun x y => q x = q y))
    (hKeep : ∀ x, q (I.after x) = q x)
    {x y : X} (m : M) (hm : S.allow m)
    (hSep : I.read (A.act m x) ≠ I.read (A.act m y)) :
    InvariantAt A S
        (fun x y =>
          extended A S q I.read x = extended A S q I.read y) ∧
      FiniteCLC.Valid
        (sourceForm q valQ oldProtected)
        (liveTargetForm A S q valQ classify oldProtected)
        (instrumentTransport A S q I valQ classify oldProtected) ∧
      extended A S q I.read x ≠ extended A S q I.read y := by
  refine ⟨extended_invariant A S q I.read hInv, ?_, ?_⟩
  · exact instrument_transport_valid_of_nondisturbance
      A S q I valQ classify oldProtected hKeep
  · exact future_separator_forces_split A S q I.read m hm hSep

end EffectfulObservationBridge

namespace EffectfulObservationBridgeExample

open EffectfulObservationBridge
open DevelopmentalObservationBridge
open VerifiedDevelopmentCore
open VerifiedDevelopmentExample

def currentVisible (x : Bool × Bool) : Bool := x.1
def oldVal (b : Bool) (_ : Unit) : FiniteCLC.Verdict :=
  if b then .eq else .dist
def newerVal (b : Bool) : FiniteCLC.Verdict :=
  if b then .eq else .dist
def keepTest (_ : Unit) : Bool := true

def safe : Instrument (Bool × Bool) Bool where
  read := fun x => x.2
  after := id

def destructive : Instrument (Bool × Bool) Bool where
  read := fun x => x.2
  after := fun x => (false, x.2)

/-- Safe instrument retains actual physical state. -/
theorem safe_is_valid :
    FiniteCLC.Valid
      (sourceForm currentVisible oldVal keepTest)
      (liveTargetForm toyAction toyStage currentVisible
        oldVal newerVal keepTest)
      (instrumentTransport toyAction toyStage currentVisible
        safe oldVal newerVal keepTest) := by
  apply instrument_transport_valid_of_nondisturbance
    toyAction toyStage currentVisible safe oldVal newerVal keepTest
  intro x
  rfl

/-- The observation separates hidden bits while the current q merges them. -/
theorem safe_adds_distinction :
    extended toyAction toyStage currentVisible safe.read
        (true, false) ≠
      extended toyAction toyStage currentVisible safe.read
        (true, true) := by
  apply future_separator_forces_split
    toyAction toyStage currentVisible safe.read () trivial
  decide

/-- Destructive measurement leaves a historical record but changes q=visible. -/
theorem destructive_changes_old_consequence :
    currentVisible (destructive.after (true, false)) ≠
      currentVisible (true, false) := by
  decide

/-- CRITICAL COUNTERCONTROL: A revealing sensor that destroys an original
    decisive test cannot pass the actual effectful CLC transport. -/
theorem destructive_not_clc_valid :
    ¬ FiniteCLC.Valid
      (sourceForm currentVisible oldVal keepTest)
      (liveTargetForm toyAction toyStage currentVisible
        oldVal newerVal keepTest)
      (instrumentTransport toyAction toyStage currentVisible
        destructive oldVal newerVal keepTest) := by
  intro hValid
  have hOld := hValid.1 (true, false) (.inl ())
  change FiniteCLC.Refines .eq .dist at hOld
  change (FiniteCLC.Verdict.eq = FiniteCLC.Verdict.unknown) ∨
    (FiniteCLC.Verdict.eq = FiniteCLC.Verdict.dist) at hOld
  rcases hOld with h | h
  · cases h
  · cases h

end EffectfulObservationBridgeExample

#print axioms EffectfulObservationBridge.nondisturbance_implies_old_futures
#print axioms EffectfulObservationBridge.old_futures_imply_nondisturbance
#print axioms EffectfulObservationBridge.instrument_transport_valid_of_nondisturbance
#print axioms EffectfulObservationBridge.conditional_instrument_extension
#print axioms EffectfulObservationBridgeExample.safe_is_valid
#print axioms EffectfulObservationBridgeExample.safe_adds_distinction
#print axioms EffectfulObservationBridgeExample.destructive_not_clc_valid

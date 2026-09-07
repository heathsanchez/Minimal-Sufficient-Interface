import Std

/-! # Transition soundness — the composed promotion/preservation/attachment theorem

  Gate 2 target: an ACCEPTED developmental transition
    (1) preserves its declared protected invariants,
    (2) cannot widen a claim without the required certificate, and
    (3) promotes only consequences supported by the actual verifier.

  Reused machinery (integrated source):
    - `SelfContainedWorld.lean` — `Certificate w w'` = `{ctor, built : w' = applyCtor ctor w}`: the
      CONSTRUCTION certificate (clause 2: a transition is claimed only with its build certificate).
    - `verified_promotion_contract.py` — scope / attachment / equality-completion (the promotion
      boundary).  This file pulls the ATTACHMENT clause into Lean.
    - `TypedBehaviouralCongruence.lean` — congruence of the quotient (preservation under the quotient).

  The canonical REFINEMENT adds exactly the distinction needed to separate a residual while keeping
  every prior distinction.  Its codomain grows from `R` to `R × Bool`, so the transition is
  type-changing (the representation, not just its parameter, develops).  The composed theorem is
  `refine_accepted`: construction (`built`), preservation (`Refines`), attachment (`resolves`).

  A residual ρ = (a, b) is collapsed (observe a = observe b) yet distinct (a ≠ b).  The canonical
  repair `refine` keeps the old observation AND adds a fresh bit flagging `x = a`:
    - preservation: `refine` is a strict refinement (new kernel finer than old) — provable generally;
    - attachment: `refine` separates the residual pair — provable generally.
-/

namespace TransitionSoundness

/- ── the world: a carrier and an observation into an arbitrary representation type ── -/
structure World (α R : Type) where
  observe : α → R

def Residual (w : World α R) : Type := α × α

/- A residual is a pair the observation collapses but that is nevertheless distinct. -/
abbrev IsResidual (w : World α R) (ρ : Residual w) : Prop :=
  w.observe ρ.1 = w.observe ρ.2 ∧ ρ.1 ≠ ρ.2

/- ── preservation: a refinement never merges states the old observation distinguished.
       Codomains may differ (the transition may change the representation type). ── -/
def Refines {α R R' : Type} (o : α → R) (o' : α → R') : Prop :=
  ∀ x y, o' x = o' y → o x = o y

/- ── the canonical repair: keep the old observation, add one bit flagging ρ.1 ───── -/
def refine {α R : Type} [DecidableEq α] (w : World α R) (ρ : Residual w) : World α (R × Bool) :=
  ⟨fun x => (w.observe x, decide (x = ρ.1))⟩

/- ── the accepted-transition predicate: construction + preservation + attachment ── -/
structure AcceptedTransition {α R : Type} [DecidableEq α]
    (w : World α R) (ρ : Residual w) (w' : World α (R × Bool)) : Prop where
  built      : w' = refine w ρ                        -- (2) construction certificate
  preserves  : Refines w.observe w'.observe           -- (1) preserves prior distinctions
  attached   : w'.observe ρ.1 ≠ w'.observe ρ.2        -- (3) resolves the motivating residual

/- ── THE composition theorem: the canonical refinement is an accepted transition ── -/
theorem refine_accepted {α R : Type} [DecidableEq α]
    (w : World α R) (ρ : Residual w) (hρ : IsResidual w ρ) :
    AcceptedTransition w ρ (refine w ρ) := by
  constructor
  · rfl  -- built: refine w ρ = refine w ρ
  · -- preservation: the first component of (observe x, _) is observe x
    intro x y h
    exact congrArg Prod.fst h
  · -- attachment: ρ.1 flags true, ρ.2 flags false (since ρ.1 ≠ ρ.2)
    intro h
    have h2 : decide (ρ.1 = ρ.1) = decide (ρ.2 = ρ.1) := congrArg Prod.snd h
    have hfalse : decide (ρ.2 = ρ.1) = false := decide_eq_false (fun e => hρ.2 e.symm)
    rw [hfalse] at h2
    have htrue : decide (ρ.1 = ρ.1) = true := by simp
    rw [htrue] at h2
    exact Bool.noConfusion h2

/- ── preservation is real: the repaired world still distinguishes every pair the old one did ── -/
theorem refine_does_not_collapse {α R : Type} [DecidableEq α]
    (w : World α R) (ρ : Residual w) :
    Refines w.observe (refine w ρ).observe := by
  intro x y h
  exact congrArg Prod.fst h

/- ── attachment is real: the repaired world separates the motivating residual ── -/
theorem refine_resolves {α R : Type} [DecidableEq α]
    (w : World α R) (ρ : Residual w) (hρ : IsResidual w ρ) :
    (refine w ρ).observe ρ.1 ≠ (refine w ρ).observe ρ.2 := by
  intro h
  have h2 : decide (ρ.1 = ρ.1) = decide (ρ.2 = ρ.1) := congrArg Prod.snd h
  have hfalse : decide (ρ.2 = ρ.1) = false := decide_eq_false (fun e => hρ.2 e.symm)
  rw [hfalse] at h2
  have htrue : decide (ρ.1 = ρ.1) = true := by simp
  rw [htrue] at h2
  exact Bool.noConfusion h2

/- ── scope is structural: `refine`'s observation is DEFINED as (old observation, residual-flag) ──
       exactly one bit is added — the observation cannot widen beyond "old distinctions + separate ρ".
       This is the Lean counterpart of the promotion contract's scope check. -/
theorem refine_image_is_product {α R : Type} [DecidableEq α]
    (w : World α R) (ρ : Residual w) (x : α) :
    (refine w ρ).observe x = (w.observe x, decide (x = ρ.1)) := rfl

/-  The three clauses of Gate 2 are composed in one structure (`AcceptedTransition`) and one
    theorem (`refine_accepted`): construction (built), preservation (preserves), attachment (attached).
    Scope-narrowness is structural (`refine_image_is_product`). -/

end TransitionSoundness

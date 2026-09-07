import Std

/-! # Constructor-genesis control — the swap residual in an ORDER-FREE substrate is unrepairable

  Gate 3 (PREREGISTRATION_SYMMETRY_CONSTRUCTOR.md, frozen) asks whether the swap residual can DERIVE a
  constructor from the raw substrate without supplying `lt` / index-order comparison.

  This file proves the NEGATIVE CONTROL (falsifier F2), which is the clean, decisive half:

    In a substrate whose ONLY relation primitives over variables are EQUALITY and INEQUALITY (no order
    on the variable indices), EVERY constructible relation is argument-symmetric, and therefore — by
    `SymmetryClass.sym_σ_does_not_separate` — NONE separates the swap witness ρ = (f x y, f y x).

  What this establishes (and what it rules out):
    - The constraint "the separator must break σ" (SymmetryClass) is NECESSARY but NOT SUFFICIENT.
    - Asymmetry cannot be manufactured from symmetric primitives: an order-free substrate has no
      asymmetric relation, so the swap residual is UNREPAIRABLE there — a theorem, not a search miss.
    - The separator's asymmetry is therefore SOURCED from the substrate (the `Nat` order carried by
      `Nat`-indexed variables), not synthesized by the developmental machinery.

  Four-outcome classification (recorded honestly):
    1. DERIVE the asymmetric constraint      — PROVED (`SymmetryClass.separating_breaks_symmetry`).
    2. SYNTHESIZE an actual constructor       — NOT achieved; the system SELECTS `lt` from a named
                                                portfolio (RelForm = eq | neq | lt), outcome (3).
    3. SELECT from a predeclared portfolio    — CURRENT state (`lt` is a named constructor).
    4. FAIL (substrate cannot express)        — PROVED here (negative control F2).
-/

namespace ConstructorGenesisControl

/- ── an order-free substrate: variables carry only equality, no index order ───── -/
inductive V where | vx | vy deriving DecidableEq, Repr, Inhabited

mutual
  inductive T where
    | var : V → T
    | f : T → T → T
  deriving DecidableEq
  -- note: no `g`, no `a0`, no Nat index — the minimal substrate needed for the swap witness.
end

def xT : T := .var .vx
def yT : T := .var .vy
def t1 : T := .f xT yT          -- f x y
def t2 : T := .f yT xT          -- f y x   (the swap)

/- ── the two child subterms ──────────────────────────────────────────────────── -/
def child0 : T → Option T
  | .f a _ => some a
  | _ => none
def child1 : T → Option T
  | .f _ b => some b
  | _ => none

/- ── a relation observed at the two argument positions ───────────────────────── -/
def obsR (R : T → T → Bool) (t : T) : Bool :=
  match child0 t, child1 t with
  | some a, some b => R a b
  | _, _ => false

def Separates (R : T → T → Bool) : Prop := obsR R t1 ≠ obsR R t2

/- ── an ORDER-FREE relation is one built from equality alone: argument-symmetric ──
       (the only order-free primitives are `=` and `≠`, both symmetric). ────────── -/
def OrderFree (R : T → T → Bool) : Prop := ∀ a b, R a b = R b a

/- ── THE negative control: an order-free relation cannot separate the swap witness ── -/
theorem order_free_does_not_separate : ∀ R, OrderFree R → ¬ Separates R := by
  intro R hR hsep
  change R xT yT ≠ R yT xT at hsep
  exact hsep (hR xT yT)

/- ── the contrapositive: any separator must break order-freedom (use an asymmetric primitive) ── -/
theorem separating_breaks_order_freedom : ∀ R, Separates R → ¬ OrderFree R := by
  intro R hsep hR
  exact order_free_does_not_separate R hR hsep

/- ── the ONLY order-free relations (equality, inequality) are indeed order-free ── -/
theorem eq_is_order_free : OrderFree (fun a b => decide (a = b)) := by
  intro a b
  by_cases h : a = b
  · simp [h]
  · have hba : b ≠ a := fun hb => h hb.symm
    simp [h, hba]

theorem neq_is_order_free : OrderFree (fun a b => decide (a ≠ b)) := by
  intro a b
  by_cases h : a = b
  · simp [h]
  · have hba : b ≠ a := fun hb => h hb.symm
    simp [h, hba]

/- ── consequence: in the order-free substrate, NO relation separates the witness ──
       (eq and neq are order-free, hence blind; and there is no asymmetric primitive). ── -/
theorem eq_neq_blind :
    ¬ Separates (fun a b => decide (a = b)) ∧ ¬ Separates (fun a b => decide (a ≠ b)) := by
  constructor
  · exact order_free_does_not_separate _ eq_is_order_free
  · exact order_free_does_not_separate _ neq_is_order_free

/- ── the substrate-trace: asymmetry must come from an ASYMMETRIC substrate primitive.
       The Nat-indexed substrate (SymmetryClass) supplies the order; this bare substrate does not,
       so the witness is unrepairable here.  A relation that separates MUST be non-order-free,
       i.e. must use a primitive that distinguishes vx from vy asymmetrically (an ORDER). ─────── -/

/-  Honest record: outcome (2) — synthesizing the constructor — is NOT established.  The system
    currently achieves outcome (3) (selecting `lt` from the named portfolio {eq, neq, lt}); this file
    proves outcome (4) (the order-free substrate fails).  What a synthesis would require: a generator
    that, given the substrate's raw primitives and the "must be asymmetric" constraint, COMPOSES an
    asymmetric primitive (e.g. the Nat order) without that primitive being pre-named in the relation
    portfolio.  That generator does not yet exist. -/

end ConstructorGenesisControl

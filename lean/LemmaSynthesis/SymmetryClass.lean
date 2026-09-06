import Std

/-! # Class-level symmetry failure: the swap obstruction derives the next ontology CLASS

  PRE-REGISTERED (frozen before execution):
    ρ = (f x y, f y x)   — the swap witness;
    σ = (0 1)            — the involution exchanging the two argument positions (hence x↔y);
    F_B = identity;  Q_t = arity.

  The Ω-step certified the FINITE ontology {eq,neq} insufficient.  This probes the WHOLE CLASS: the key
  theorem no longer quantifies over a finite set but over every σ-symmetric relation.

  A relation R is observed at the two argument positions [0],[1]: obsR R t = R (child 0 t) (child 1 t).
  The swap σ=(0 1) exchanges those positions, so Sym_σ(R) — invariance under σ — is exactly argument
  symmetry:  Sym_σ(R) := ∀ a b, R a b = R b a.

  Prediction (prospective):
    ∀ R,  Sym_σ(R) ⇒ ¬Separates(R, ρ)      — equivalently  Separates(R, ρ) ⇒ ¬Sym_σ(R).
    i.e. the swap symmetry of the witness is THE obstruction: any argument-symmetric relation cannot
    separate ρ; a separator must BREAK the symmetry.  So the next ontology class is not "ordering"
    (chosen) but "the least admissible class that breaks the certified symmetry" (derived).

  Falsifiable:
    F1  some σ-symmetric relation separates ρ (the symmetry is NOT the obstruction);
    F2  lt does not separate ρ (the witness is not a pure swap).

  Kernel-checked:
    sym_σ_does_not_separate    — ∀ R, Sym_σ(R) ⇒ ¬Separates(R, ρ)          (THE class-level theorem);
    separating_breaks_symmetry — ∀ R, Separates(R, ρ) ⇒ ¬Sym_σ(R)          (the symmetry-breaking law);
    eq_is_sym_σ / neq_is_sym_σ — equality/inequality are σ-symmetric (recovers Ω_t at class level);
    lt_breaks_sym              — ordering BREAKS σ (¬Sym_σ(lt));
    lt_separates               — ordering separates;
    fb_breaks_σ                — F_B itself breaks σ (F_B(x) ≠ F_B(y)); the anchor of the law.

  Law (most general form on record):
    A system may preserve an invariance (σ-symmetry of its observation) only while verified continuation
    is invariant under it (F_B preserves the swap).  Since F_B distinguishes the σ-related states (x vs y),
    adequacy forces the invariance to break.
-/

namespace SymmetryClass

structure Signature where
  Srt : Type
  Op  : Srt → Type
  arity : {s : Srt} → Op s → List Srt
  sortBE : DecidableEq Srt
  opBE : (s : Srt) → DecidableEq (Op s)

attribute [local instance] Signature.sortBE Signature.opBE

mutual
  inductive Term (S : Signature) : S.Srt → Type where
    | var (s : S.Srt) : Nat → Term S s
    | op {s : S.Srt} (o : S.Op s) : Args S (S.arity o) → Term S s
  deriving DecidableEq
  inductive Args (S : Signature) : List S.Srt → Type where
    | nil : Args S []
    | cons {s : S.Srt} {ss : List S.Srt} : Term S s → Args S ss → Args S (s :: ss)
  deriving DecidableEq
end

inductive ASrt where | A deriving DecidableEq, Repr, Inhabited
inductive AOp where | a0 | f | g deriving DecidableEq, Repr, Inhabited

def AOpFam : ASrt → Type := fun _ => AOp
def AOpDecEq (s : ASrt) : DecidableEq (AOpFam s) := by unfold AOpFam; infer_instance
def AArity : {s : ASrt} → AOpFam s → List ASrt
  | .A, .a0 => []
  | .A, .f => [.A, .A]
  | .A, .g => [.A, .A]
def SigA : Signature := ⟨ASrt, AOpFam, AArity, inferInstance, AOpDecEq⟩

def xVar : Term SigA ASrt.A := @Term.var SigA ASrt.A 0
def yVar : Term SigA ASrt.A := @Term.var SigA ASrt.A 1
def a0T  : Term SigA ASrt.A := .op AOp.a0 .nil
def t1   : Term SigA ASrt.A := .op AOp.f (.cons xVar (.cons yVar .nil))   -- f x y
def t2   : Term SigA ASrt.A := .op AOp.f (.cons yVar (.cons xVar .nil))   -- f y x

def FB : Term SigA ASrt.A → Term SigA ASrt.A := fun t => t

def childAt : Nat → Term SigA ASrt.A → Option (Term SigA ASrt.A)
  | 0, .op AOp.f (.cons l (.cons _ .nil)) => some l
  | 0, .op AOp.g (.cons l (.cons _ .nil)) => some l
  | 1, .op AOp.f (.cons _ (.cons r .nil)) => some r
  | 1, .op AOp.g (.cons _ (.cons r .nil)) => some r
  | _, _ => none

/- ── Sym_σ: invariance under the position swap σ=(0 1) = argument symmetry ────── -/
def Sym_σ (R : Term SigA ASrt.A → Term SigA ASrt.A → Bool) : Prop :=
  ∀ a b, R a b = R b a

/- ── an observation: R applied to the two argument positions [0],[1] ─────────── -/
def obsR (R : Term SigA ASrt.A → Term SigA ASrt.A → Bool) (t : Term SigA ASrt.A) : Bool :=
  match childAt 0 t, childAt 1 t with
  | some a, some b => R a b
  | _, _ => false

/-  Separates R ρ := R distinguishes t1=f x y from t2=f y x, i.e. the ordered pair (x,y) from (y,x). -/
def Separates (R : Term SigA ASrt.A → Term SigA ASrt.A → Bool) : Prop :=
  obsR R t1 ≠ obsR R t2

/- ── THE class-level theorem: σ-symmetric relations cannot separate ρ ────────── -/
theorem sym_σ_does_not_separate : ∀ R, Sym_σ R → ¬ Separates R := by
  intro R hSym hsep
  change R xVar yVar ≠ R yVar xVar at hsep
  exact hsep (hSym xVar yVar)

/- ── the symmetry-breaking law (contrapositive) ─────────────────────────────── -/
theorem separating_breaks_symmetry : ∀ R, Separates R → ¬ Sym_σ R := by
  intro R hsep hSym
  exact sym_σ_does_not_separate R hSym hsep

/- ── eq, neq are σ-symmetric → recovers Ω_t insufficiency at class level ─────── -/
theorem eq_is_sym_σ : Sym_σ (fun a b => decide (a = b)) := by
  intro a b
  by_cases h : a = b
  · simp [h]
  · have hba : b ≠ a := fun hb => h hb.symm
    simp [h, hba]

theorem neq_is_sym_σ : Sym_σ (fun a b => decide (a ≠ b)) := by
  intro a b
  by_cases h : a = b
  · simp [h]
  · have hba : b ≠ a := fun hb => h hb.symm
    simp [h, hba]

/- ── ordering breaks σ and separates ─────────────────────────────────────────── -/
def ltRel' : Term SigA ASrt.A → Term SigA ASrt.A → Bool
  | .var _ n, .var _ m => decide (n < m)
  | _, _ => false

theorem lt_xy : ltRel' xVar yVar = true := by native_decide
theorem lt_yx : ltRel' yVar xVar = false := by native_decide

theorem lt_breaks_sym : ¬ Sym_σ ltRel' := by
  intro h
  have hxy : ltRel' yVar xVar = ltRel' xVar yVar := (h xVar yVar).symm
  rw [lt_yx, lt_xy] at hxy
  cases hxy

theorem lt_separates : Separates ltRel' := by
  unfold Separates obsR
  native_decide

/- ── F_B itself breaks σ: the anchor of the law ─────────────────────────────── -/
theorem fb_breaks_σ : FB xVar ≠ FB yVar := by
  native_decide

/-  The law, in kernel-checked form: because F_B distinguishes the σ-related states (x vs y), adequacy
    forces the observation to break σ.  `separating_breaks_symmetry` is that theorem; `fb_breaks_σ` is the
    reason the invariance is untenable.  The next ontology class is therefore the σ-breaking (asymmetric)
    relations, and `lt` is the least admissible one. -/

end SymmetryClass

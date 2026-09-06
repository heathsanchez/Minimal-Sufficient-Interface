import Std

/-! # Candidate-constructor genesis (pre-registered)

  The deepest remaining manual seam: WHO proposes the new discriminator.  This removes it — the system
  derives a discriminator from the witness's STRUCTURE, using only the frozen constructor grammar G_t.

  PRE-REGISTERED (frozen before execution):
    Q_t = arity, F_B = identity, ρ = (f x a0, f y a0);
    H_t = {head, child 1}          (frozen, insufficient — missing the left-child observation);
    G_t = {head, child 0, child 1} (frozen constructor grammar: structural decomposition);
    order = list order (head coarsest).

  Genesis mechanism (no human naming "leftChild"): enumerate observations o ∈ G_t, test
  Separates(o, ρ) := observe o ρ_a ≠ observe o ρ_b, return the LEAST separating one.

  Falsifiable — "derived from the residual" fails if:
    F1  genesis returns head or child 1 (the invariant observations);
    F2  genesis returns none (no separating observation generable in G_t);
    F3  the generated observation is already in H_t (not new).

  Prediction (prospective): genesis discovers child 0 — head (f=f) and child 1 (a0=a0) are INVARIANT across
  the witness, child 0 (x≠y) DIFFERS, so child 0 is the least separating observation.

  Kernel-checked:
    ht_insufficient      — ∀ o ∈ H_t, ¬ Separates(o, ρ): certified insufficiency;
    genesis_finds_child0 — the generator (G_t only) returns child 0;
    generated_separates  — the generated observation separates;
    generated_not_in_Ht  — the generated observation is genuinely new;
    replay_adequate      — repaired quotient (arity, child 0) finds no witness.
-/

namespace CandidateGenesis

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
def fxa  : Term SigA ASrt.A := .op AOp.f (.cons xVar (.cons a0T .nil))   -- f x a0
def fya  : Term SigA ASrt.A := .op AOp.f (.cons yVar (.cons a0T .nil))   -- f y a0

def lenArgs {ss : List ASrt} : Args SigA ss → Nat
  | .nil => 0
  | .cons _ rest => 1 + lenArgs rest

def arity : Term SigA ASrt.A → Nat
  | .var _ _ => 0
  | .op _ args => lenArgs args

def Q_t : Term SigA ASrt.A → Nat := arity
def FB  : Term SigA ASrt.A → Term SigA ASrt.A := fun t => t

/- ── the frozen constructor grammar G_t: structural decomposition ─────────── -/
inductive Head where | var | op (o : AOp) deriving DecidableEq

def headOf : Term SigA ASrt.A → Head
  | .var _ _ => .var
  | .op o _ => .op o

inductive Obs where
  | head : Obs
  | child : Nat → Obs
deriving DecidableEq, Repr, Inhabited

inductive ObsVal where
  | head (h : Head)
  | term (t : Term SigA ASrt.A)
  | none
deriving DecidableEq

/- observation: the head, or the i-th child (structural decomposition; no "left"/"right" names) -/
def observe : Obs → Term SigA ASrt.A → ObsVal
  | .head, t => .head (headOf t)
  | .child 0, .op AOp.f (.cons l (.cons _ .nil)) => .term l
  | .child 0, .op AOp.g (.cons l (.cons _ .nil)) => .term l
  | .child 1, .op AOp.f (.cons _ (.cons r .nil)) => .term r
  | .child 1, .op AOp.g (.cons _ (.cons r .nil)) => .term r
  | .child _, _ => .none

/- H_t (frozen, insufficient) and G_t (frozen constructor grammar) -/
def Ht : List Obs := [.head, .child 1]
def Gt : List Obs := [.head, .child 0, .child 1]

/- ── the genesis: enumerate G_t, return the least separating observation ──── -/
def genesis (ra rb : Term SigA ASrt.A) : Option Obs :=
  match (Gt.filter fun o => decide (observe o ra ≠ observe o rb)) with
  | [] => none
  | o :: _ => some o

/- generic tester (for replay) -/
def adequacyWitnesses {α β γ : Type} [DecidableEq β] [DecidableEq γ]
    (xs : List α) (Q : α → β) (F : α → γ) : List (α × α) :=
  (xs.flatMap fun x => xs.map fun y => (x, y)).filter fun p => decide (Q p.1 = Q p.2 ∧ F p.1 ≠ F p.2)

/- ── 1. certified insufficiency: no observation in H_t separates ──────────── -/
theorem ht_insufficient : ∀ o, o ∈ Ht → ¬ (observe o fxa ≠ observe o fya) := by
  intro o ho hsep
  simp [Ht] at ho
  rcases ho with rfl | rfl
  · exact hsep rfl
  · exact hsep rfl

/- ── 2. the generator (G_t only) discovers child 0 ────────────────────────── -/
theorem genesis_finds_child0 : genesis fxa fya = some (.child 0) := by
  native_decide

/- ── 3. the generated observation separates ───────────────────────────────── -/
theorem generated_separates : observe (.child 0) fxa ≠ observe (.child 0) fya := by
  intro h
  cases h

/- ── 4. the generated observation is genuinely new (not in H_t) ───────────── -/
theorem generated_not_in_Ht : .child 0 ∉ Ht := by
  intro h
  simp [Ht] at h

/- ── 5. REPLAY: repaired quotient (arity, child 0) finds no witness ───────── -/
def repairedQ : Term SigA ASrt.A → Nat × ObsVal := fun t => (arity t, observe (.child 0) t)

theorem replay_adequate : adequacyWitnesses [fxa, fya] repairedQ FB = [] := by
  native_decide

/- Loop: Q_t → ρ → certify H_t insufficient → generate Δ (child 0, from G_t) → H_{t+1} → Q_{t+1} → replay.
   The new discriminator is DERIVED from the witness structure, not hand-supplied. -/

end CandidateGenesis

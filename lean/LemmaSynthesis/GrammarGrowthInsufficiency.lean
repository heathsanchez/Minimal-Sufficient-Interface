import Std

/-! # Certified grammar-growth insufficiency: Γ_t is inadequate → Γ_{t+1}

  The last fixed operator is Γ_t : G_t ↦ G_{t+1} = "extend paths by one more composition step".  This
  tests whether Γ_t ITSELF is adequate — with NO richer Γ until the old one is PROVEN insufficient.

  PRE-REGISTERED (frozen before execution):
    Q_t = arity, F_B = identity, ρ = (f x x, f x y);
    G_t = {[], [0], [1]} (depth-1 paths);  Γ_t = path extension (one composition step);
    Γ_t(G_t) = {[], [0], [1], [0,0], [0,1], [1,0], [1,1]} (depth ≤ 2, the tested bound);
    the path projection observes the OPERATOR SKELETON — head-at-path, with NO variable index, so
    variables x and y are path-INVISIBLE.

  Prediction (prospective): Γ_t is FUNDAMENTALLY insufficient.  f x x and f x y have the same operator
  skeleton at every path (f, var, var, none, …), so NO finite path separates them; they differ only in a
  RELATIONAL property — whether the two siblings are equal (x=x vs x≠y).  A path extension cannot express
  that; only a non-path observation constructor can.

  Falsifiable:
    F1  some path separates (the operator skeleton already distinguishes them);
    F2  no non-path (relational) observation separates.

  Kernel-checked:
    no_path_separates      — ∀ path, observe path (f x x) = observe path (f x y): NO path separates;
    gamma_insufficient     — ∀ p ∈ Γ_t(G_t), ¬ Separates(p, ρ): the growth mechanism is certified inadequate;
    sibling_eq_separates   — the relational "sibling equality" observation separates;
    sibling_eq_is_new      — sibling equality is a genuinely non-path discriminator;
    replay_adequate        — repaired quotient (arity, siblingEq) finds no witness.
-/

namespace GrammarGrowthInsufficiency

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
def t1   : Term SigA ASrt.A := .op AOp.f (.cons xVar (.cons xVar .nil))   -- f x x  (siblings equal)
def t2   : Term SigA ASrt.A := .op AOp.f (.cons xVar (.cons yVar .nil))   -- f x y  (siblings differ)

def lenArgs {ss : List ASrt} : Args SigA ss → Nat
  | .nil => 0
  | .cons _ rest => 1 + lenArgs rest

def arity : Term SigA ASrt.A → Nat
  | .var _ _ => 0
  | .op _ args => lenArgs args

def Q_t : Term SigA ASrt.A → Nat := arity
def FB  : Term SigA ASrt.A → Term SigA ASrt.A := fun t => t

/- ── path projection: head-at-path, NO variable index (variables path-invisible) ── -/
inductive Head where | var | op (o : AOp) deriving DecidableEq, Repr, Inhabited

def headOf : Term SigA ASrt.A → Head
  | .var _ _ => .var
  | .op o _ => .op o

def childAt : Nat → Term SigA ASrt.A → Option (Term SigA ASrt.A)
  | 0, .op AOp.f (.cons l (.cons _ .nil)) => some l
  | 0, .op AOp.g (.cons l (.cons _ .nil)) => some l
  | 1, .op AOp.f (.cons _ (.cons r .nil)) => some r
  | 1, .op AOp.g (.cons _ (.cons r .nil)) => some r
  | _, _ => none

def observe : List Nat → Term SigA ASrt.A → Option Head
  | [], t => some (headOf t)
  | (i :: rest), t =>
      match childAt i t with
      | some c => observe rest c
      | none => none

/- ── the relational (non-path) observation: sibling equality ──────────────── -/
def siblingEq : Term SigA ASrt.A → Bool
  | .op AOp.f (.cons l (.cons r .nil)) => decide (l = r)
  | .op AOp.g (.cons l (.cons r .nil)) => decide (l = r)
  | _ => true

/- G_t and Γ_t(G_t) (the tested bound: depth ≤ 2) -/
def Gt      : List (List Nat) := [[], [0], [1]]
def GammaGt : List (List Nat) := [[], [0], [1], [0,0], [0,1], [1,0], [1,1]]

def adequacyWitnesses {α β γ : Type} [DecidableEq β] [DecidableEq γ]
    (xs : List α) (Q : α → β) (F : α → γ) : List (α × α) :=
  (xs.flatMap fun x => xs.map fun y => (x, y)).filter fun p => decide (Q p.1 = Q p.2 ∧ F p.1 ≠ F p.2)

/- ── 0. variables are path-indistinguishable (no-index head) ──────────────── -/
theorem vars_path_equal : ∀ p : List Nat, observe p xVar = observe p yVar := by
  intro p
  cases p with
  | nil => rfl
  | cons i rest =>
      cases i with
      | zero => rfl
      | succ i => cases i with
        | zero => rfl
        | succ i => rfl

/- ── 1. NO path separates (the operator skeleton is identical) ────────────── -/
theorem no_path_separates : ∀ p : List Nat, observe p t1 = observe p t2 := by
  intro p
  cases p with
  | nil => rfl
  | cons i rest =>
      cases i with
      | zero => rfl
      | succ i =>
          cases i with
          | zero => exact vars_path_equal rest
          | succ i => rfl

/- ── 2. CERTIFIED Γ_t insufficiency: no path in Γ_t(G_t) separates ────────── -/
theorem gamma_insufficient : ∀ p, p ∈ GammaGt → ¬ (observe p t1 ≠ observe p t2) := by
  intro p hp hsep
  exact hsep (no_path_separates p)

/- ── 3. the relational observation separates ──────────────────────────────── -/
theorem sibling_eq_separates : siblingEq t1 ≠ siblingEq t2 := by
  native_decide

/- ── 4. sibling equality is a genuinely NON-path discriminator ────────────── -/
theorem sibling_eq_is_new : siblingEq t1 ≠ siblingEq t2 ∧ ∀ p : List Nat, ¬ (observe p t1 ≠ observe p t2) := by
  constructor
  · exact sibling_eq_separates
  · intro p hsep
    exact hsep (no_path_separates p)

/- ── 5. REPLAY: repaired quotient (arity, siblingEq) finds no witness ─────── -/
def repairedQ : Term SigA ASrt.A → Nat × Bool := fun t => (arity t, siblingEq t)

theorem replay_adequate : adequacyWitnesses [t1, t2] repairedQ FB = [] := by
  native_decide

/- The tower Q → H → G → Γ: the growth mechanism Γ_t (path extension) is itself certified inadequate —
   it can never express a relational discriminator.  Only then is Γ_{t+1} (non-path constructors) admitted. -/

end GrammarGrowthInsufficiency

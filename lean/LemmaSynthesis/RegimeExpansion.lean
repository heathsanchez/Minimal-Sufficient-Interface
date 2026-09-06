import Std

/-! # Constraint-derived regime expansion: the certified Γ_t failure generates the relational form

  The last human-supplied object was Γ_{t+1} = "admit relational observations such as sibling equality".
  This tests whether the CERTIFIED failure of Γ_t can itself GENERATE the new constructor family — the
  jump path-observation → relational-observation becomes residual-derived, not human-chosen.

  PRE-REGISTERED (frozen before execution):
    Q_t = arity, F_B = identity, ρ = (f x x, f x y);
    Ω_t = a FROZEN higher-order constructor language: unary path observations {path p} PLUS binary
          relational forms {rel Eq p q, rel Neq p q} over position pairs;
    the genesis enumerates Ω_t and returns the LEAST separating observation.

  The mechanism:
    1. certify Γ_t insufficient (every unary path observation is invariant — already proven);
    2. DERIVE the constraint: any separating observation must inspect ≥ 2 locations (non-unary);
    3. enumerate the frozen higher-order language Ω_t;
    4. synthesize the least separating observation — eq([0],[1]) — because the sibling relation
       (x=x vs x≠y) is exactly what differs, and no unary observation sees it.

  Falsifiable:
    F1  a unary path observation separates (no relational regime needed);
    F2  no observation in Ω_t separates (even the higher-order language is insufficient).

  Kernel-checked:
    unary_invariant         — ∀ path, observe2 (path p) is invariant (certified Γ_t failure);
    relational_separates    — eq([0],[1]) separates;
    genesis_finds_relational — the genesis (over frozen Ω_t) returns eq([0],[1]);
    constraint_derived      — any separating observation in Ω_t is RELATIONAL (the constraint is
                              derived from the certified unary failure, not assumed);
    replay_adequate         — repaired quotient (arity, eq([0],[1])) finds no witness.
-/

namespace RegimeExpansion

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
def t1   : Term SigA ASrt.A := .op AOp.f (.cons xVar (.cons xVar .nil))   -- f x x
def t2   : Term SigA ASrt.A := .op AOp.f (.cons xVar (.cons yVar .nil))   -- f x y

def lenArgs {ss : List ASrt} : Args SigA ss → Nat
  | .nil => 0
  | .cons _ rest => 1 + lenArgs rest

def arity : Term SigA ASrt.A → Nat
  | .var _ _ => 0
  | .op _ args => lenArgs args

def Q_t : Term SigA ASrt.A → Nat := arity
def FB  : Term SigA ASrt.A → Term SigA ASrt.A := fun t => t

/- ── unary path projection (head-at-path, no variable index) ──────────────── -/
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

/- ── the FROZEN higher-order constructor language Ω_t ─────────────────────── -/
def subtermAt : List Nat → Term SigA ASrt.A → Option (Term SigA ASrt.A)
  | [], t => some t
  | (i :: rest), t => match childAt i t with | some c => subtermAt rest c | none => none

inductive RelForm where | eq | neq deriving DecidableEq, Repr, Inhabited

inductive Obs2 where
  | path : List Nat → Obs2
  | rel  : RelForm → List Nat → List Nat → Obs2
deriving DecidableEq, Repr, Inhabited

inductive ObsVal2 where
  | head (h : Option Head)
  | bool (b : Bool)
deriving DecidableEq

def relEq (p q : List Nat) (t : Term SigA ASrt.A) : Bool :=
  match subtermAt p t, subtermAt q t with
  | some a, some b => decide (a = b)
  | _, _ => true

def relNeq (p q : List Nat) (t : Term SigA ASrt.A) : Bool :=
  match subtermAt p t, subtermAt q t with
  | some a, some b => decide (a ≠ b)
  | _, _ => false

def observe2 : Obs2 → Term SigA ASrt.A → ObsVal2
  | .path p, t => .head (observe p t)
  | .rel .eq p q, t => .bool (relEq p q t)
  | .rel .neq p q, t => .bool (relNeq p q t)

/- Ω_t (bounded enumeration of the higher-order language) -/
def Omegat : List Obs2 :=
  [.path [], .path [0], .path [1],
   .rel .eq [0] [1], .rel .eq [0] [0], .rel .eq [1] [1],
   .rel .neq [0] [1], .rel .neq [0] [0], .rel .neq [1] [1]]

def genesis2 (ra rb : Term SigA ASrt.A) : Option Obs2 :=
  match (Omegat.filter fun o => decide (observe2 o ra ≠ observe2 o rb)) with
  | [] => none
  | o :: _ => some o

def adequacyWitnesses {α β γ : Type} [DecidableEq β] [DecidableEq γ]
    (xs : List α) (Q : α → β) (F : α → γ) : List (α × α) :=
  (xs.flatMap fun x => xs.map fun y => (x, y)).filter fun p => decide (Q p.1 = Q p.2 ∧ F p.1 ≠ F p.2)

/- ── 1. CERTIFIED Γ_t failure: every unary path observation is invariant ──── -/
theorem vars_path_equal : ∀ p : List Nat, observe p xVar = observe p yVar := by
  intro p
  cases p with
  | nil => rfl
  | cons i rest => cases i with
    | zero => rfl
    | succ i => cases i with
      | zero => rfl
      | succ i => rfl

theorem no_path_separates : ∀ p : List Nat, observe p t1 = observe p t2 := by
  intro p
  cases p with
  | nil => rfl
  | cons i rest => cases i with
    | zero => rfl
    | succ i => cases i with
      | zero => exact vars_path_equal rest
      | succ i => rfl

theorem unary_invariant : ∀ p, observe2 (.path p) t1 = observe2 (.path p) t2 := by
  intro p
  simp [observe2]
  exact no_path_separates p

/- ── 2. the relational observation eq([0],[1]) separates ──────────────────── -/
theorem relational_separates : observe2 (.rel .eq [0] [1]) t1 ≠ observe2 (.rel .eq [0] [1]) t2 := by
  native_decide

/- ── 3. the genesis (over frozen Ω_t) finds eq([0],[1]) ───────────────────── -/
theorem genesis_finds_relational : genesis2 t1 t2 = some (.rel .eq [0] [1]) := by
  native_decide

/- ── 4. the CONSTRAINT is DERIVED: any separating observation is relational ── -/
def isRel : Obs2 → Prop
  | .path _ => False
  | .rel _ _ _ => True

theorem constraint_derived : ∀ o, o ∈ Omegat → observe2 o t1 ≠ observe2 o t2 → isRel o := by
  intro o ho hsep
  simp [Omegat] at ho
  rcases ho with rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl | rfl
  · exfalso; apply hsep; exact unary_invariant []
  · exfalso; apply hsep; exact unary_invariant [0]
  · exfalso; apply hsep; exact unary_invariant [1]
  · trivial
  · trivial
  · trivial
  · trivial
  · trivial
  · trivial

/- ── 5. REPLAY: repaired quotient (arity, eq([0],[1])) finds no witness ───── -/
def repairedQ : Term SigA ASrt.A → Nat × ObsVal2 := fun t => (arity t, observe2 (.rel .eq [0] [1]) t)

theorem replay_adequate : adequacyWitnesses [t1, t2] repairedQ FB = [] := by
  native_decide

/- The jump path→relational is now residual-derived: the certified Γ_t failure forces the constraint
   "must inspect ≥ 2 locations", and the genesis over the frozen higher-order language Ω_t synthesizes
   eq([0],[1]) — the human supplied the TEMPLATE family {eq, neq}, not the discriminator. -/

end RegimeExpansion

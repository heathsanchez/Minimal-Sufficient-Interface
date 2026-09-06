import Std

/-! # Certified ontology insufficiency: Ω_t = {eq, neq} cannot separate an ordering witness

  The last frozen seam is Ω_t — the ontology of relation TEMPLATES the system may instantiate.  This
  certifies Ω_t insufficient and enlarges to Ω_{t+1}, with NO new relation until the old ontology is
  PROVEN unable to separate.

  PRE-REGISTERED (frozen before execution):
    Q_t = arity, F_B = identity, ρ = (f x y, f y x);
    Ω_t = {eq, neq} — binary equality/inequality over accessible positions;
    accessible positions = {[], [0], [1]} (deeper positions are degenerate: leaves give none).

  Prediction (prospective): Ω_t is INSUFFICIENT.  f x y and f y x have the SAME equality pattern
  (child 0 ≠ child 1 in both, so eq([0],[1]) = false and neq([0],[1]) = true in both) — swapping the two
  variables preserves equality.  What differs is the ORDER of the two variables (x<y vs y<x), which
  equality cannot express.  So no eq/neq relation separates; an ORDERING relation does.

  Falsifiable:
    F1  some eq/neq relation over accessible positions separates (Ω_t is adequate);
    F2  no ordering relation separates (even Ω_{t+1} is insufficient).

  Kernel-checked:
    eq_neq_invariant   — ∀ eq/neq relation over accessible positions, invariant (certified Ω_t failure);
    lt_separates       — the ordering relation lt([0],[1]) separates;
    genesis_finds_lt   — the genesis over Ω_{t+1} = {eq, neq, lt} returns lt([0],[1]);
    constraint_derived — any separating relation is ≠ eq/neq, i.e. MUST be ordering (derived);
    replay_adequate    — repaired quotient (arity, lt([0],[1])) finds no witness.
-/

namespace OntologyInsufficiency

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

def lenArgs {ss : List ASrt} : Args SigA ss → Nat
  | .nil => 0
  | .cons _ rest => 1 + lenArgs rest

def arity : Term SigA ASrt.A → Nat
  | .var _ _ => 0
  | .op _ args => lenArgs args

def Q_t : Term SigA ASrt.A → Nat := arity
def FB  : Term SigA ASrt.A → Term SigA ASrt.A := fun t => t

def childAt : Nat → Term SigA ASrt.A → Option (Term SigA ASrt.A)
  | 0, .op AOp.f (.cons l (.cons _ .nil)) => some l
  | 0, .op AOp.g (.cons l (.cons _ .nil)) => some l
  | 1, .op AOp.f (.cons _ (.cons r .nil)) => some r
  | 1, .op AOp.g (.cons _ (.cons r .nil)) => some r
  | _, _ => none

def subtermAt : List Nat → Term SigA ASrt.A → Option (Term SigA ASrt.A)
  | [], t => some t
  | (i :: rest), t => match childAt i t with | some c => subtermAt rest c | none => none

/- ── the relation ontology Ω_t = {eq, neq} (binary equality/inequality) ────── -/
def relEq (p q : List Nat) (t : Term SigA ASrt.A) : Bool :=
  match subtermAt p t, subtermAt q t with
  | some a, some b => decide (a = b)
  | _, _ => true

def relNeq (p q : List Nat) (t : Term SigA ASrt.A) : Bool :=
  match subtermAt p t, subtermAt q t with
  | some a, some b => decide (a ≠ b)
  | _, _ => false

/- the NEW relation (ordering): is the variable at p < the variable at q? ───── -/
def ltRel (p q : List Nat) (t : Term SigA ASrt.A) : Bool :=
  match subtermAt p t, subtermAt q t with
  | some (.var _ n), some (.var _ m) => decide (n < m)
  | _, _ => false

/- the relation TEMPLATE and its instantiation ─────────────────────────────── -/
inductive RelForm where | eq | neq | lt deriving DecidableEq, Repr, Inhabited

def relObs : RelForm → List Nat → List Nat → Term SigA ASrt.A → Bool
  | .eq, p, q, t => relEq p q t
  | .neq, p, q, t => relNeq p q t
  | .lt, p, q, t => ltRel p q t

def accessiblePos : List (List Nat) := [[], [0], [1]]

def omegaObs : List (RelForm × List Nat × List Nat) :=
  (accessiblePos.flatMap fun p => accessiblePos.map fun q => (.eq, p, q)) ++
  (accessiblePos.flatMap fun p => accessiblePos.map fun q => (.neq, p, q)) ++
  (accessiblePos.flatMap fun p => accessiblePos.map fun q => (.lt, p, q))

def genesisOmega (ra rb : Term SigA ASrt.A) : Option (RelForm × List Nat × List Nat) :=
  match (omegaObs.filter fun (r, p, q) => decide (relObs r p q ra ≠ relObs r p q rb)) with
  | [] => none
  | o :: _ => some o

def adequacyWitnesses {α β γ : Type} [DecidableEq β] [DecidableEq γ]
    (xs : List α) (Q : α → β) (F : α → γ) : List (α × α) :=
  (xs.flatMap fun x => xs.map fun y => (x, y)).filter fun p => decide (Q p.1 = Q p.2 ∧ F p.1 ≠ F p.2)

/- ── 1. CERTIFIED Ω_t failure: every eq/neq relation is invariant ─────────── -/
theorem eq_neq_invariant :
    (∀ p ∈ accessiblePos, ∀ q ∈ accessiblePos, relEq p q t1 = relEq p q t2) ∧
    (∀ p ∈ accessiblePos, ∀ q ∈ accessiblePos, relNeq p q t1 = relNeq p q t2) := by
  constructor
  · intro p hp q hq
    simp [accessiblePos] at hp hq
    rcases hp with rfl | rfl | rfl <;> rcases hq with rfl | rfl | rfl <;> rfl
  · intro p hp q hq
    simp [accessiblePos] at hp hq
    rcases hp with rfl | rfl | rfl <;> rcases hq with rfl | rfl | rfl <;> rfl

/- ── 2. the ordering relation separates ───────────────────────────────────── -/
theorem lt_separates : relObs .lt [0] [1] t1 ≠ relObs .lt [0] [1] t2 := by
  native_decide

/- ── 3. the genesis over Ω_{t+1} = {eq, neq, lt} returns lt([0],[1]) ───────── -/
theorem genesis_finds_lt : genesisOmega t1 t2 = some (.lt, [0], [1]) := by
  native_decide

/- ── 4. the CONSTRAINT is DERIVED: any separating relation must be ordering ── -/
theorem constraint_derived : ∀ (r : RelForm), r ≠ .lt → ∀ p ∈ accessiblePos, ∀ q ∈ accessiblePos,
    ¬ (relObs r p q t1 ≠ relObs r p q t2) := by
  intro r hrlt p hp q hq hsep
  have hreq : r = .eq ∨ r = .neq := by
    cases r with
    | eq => exact Or.inl rfl
    | neq => exact Or.inr rfl
    | lt => exfalso; exact hrlt rfl
  rcases hreq with rfl | rfl
  · exact hsep (eq_neq_invariant.1 p hp q hq)
  · exact hsep (eq_neq_invariant.2 p hp q hq)

/- ── 5. REPLAY: repaired quotient (arity, lt([0],[1])) finds no witness ───── -/
def repairedQ : Term SigA ASrt.A → Nat × Bool := fun t => (arity t, ltRel [0] [1] t)

theorem replay_adequate : adequacyWitnesses [t1, t2] repairedQ FB = [] := by
  native_decide

/- The ontology Ω_t={eq,neq} is certified insufficient; the ordering relation is forced and generated.
   The tower Q→H→G→Γ→Ω now includes the ONTOLOGY OF RELATIONS as a developable object. -/

end OntologyInsufficiency

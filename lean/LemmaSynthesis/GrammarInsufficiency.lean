import Std

/-! # Certified generator-grammar insufficiency → grammar development (composition)

  The deepest seam now is G_t, the grammar that determines WHICH discriminators can be generated.
  This tests whether G_t itself is adequate, with NO enlargement until the old grammar is PROVEN unable
  to generate a separator.

  PRE-REGISTERED (frozen before execution):
    Q_t = arity, F_B = identity, ρ = (f (f x a0) a0, f (f y a0) a0);
    G_t = {[], [0], [1]}  — depth-1 observations (head + child(i)), the current generator grammar;
    observation = a PATH (List Nat) of child steps, then read the HEAD (with variable index) at that node.

  Prediction (prospective): G_t is INSUFFICIENT.  The witness agrees on every depth-1 observation
  (head f, child-0 head f, child-1 head a0 all match) but differs only at depth 2 (child(0)∘child(0):
  head of the left-left grandchild is x vs y).  So no depth-1 observation separates; the required
  discriminator is a COMPOSITION, not generable by G_t.

  Falsifiable:
    F1  some depth-1 observation separates (G_t is adequate);
    F2  no depth-2 (composed) observation separates.

  Kernel-checked:
    gt_insufficient       — ∀ p ∈ G_t, ¬ Separates(observe p, ρ): certified grammar insufficiency;
    composed_separates    — observe [0,0] (child 0 ∘ child 0) separates;
    composed_in_enlarged  — [0,0] ∈ G_{t+1} (the composed grammar);
    genesisG_finds_composed — the grammar-level genesis finds [0,0];
    replay_adequate       — repaired quotient (arity, observe [0,0]) finds no witness.
-/

namespace GrammarInsufficiency

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
def ffxa : Term SigA ASrt.A := .op AOp.f (.cons fxa (.cons a0T .nil))    -- f (f x a0) a0
def ffya : Term SigA ASrt.A := .op AOp.f (.cons fya (.cons a0T .nil))    -- f (f y a0) a0

def lenArgs {ss : List ASrt} : Args SigA ss → Nat
  | .nil => 0
  | .cons _ rest => 1 + lenArgs rest

def arity : Term SigA ASrt.A → Nat
  | .var _ _ => 0
  | .op _ args => lenArgs args

def Q_t : Term SigA ASrt.A → Nat := arity
def FB  : Term SigA ASrt.A → Term SigA ASrt.A := fun t => t

/- ── the generator grammar: observations are PATHS + read the head ────────── -/
inductive Head where | var (n : Nat) | op (o : AOp) deriving DecidableEq

def headOf : Term SigA ASrt.A → Head
  | .var _ n => .var n
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

/- G_t (depth-1) and G_{t+1} (depth ≤ 2, closed under composition) -/
def Gt  : List (List Nat) := [[], [0], [1]]
def Gt1 : List (List Nat) := [[], [0], [1], [0,0], [0,1], [1,0], [1,1]]

/- ── grammar-level genesis: find the least separating path in a grammar ───── -/
def genesisG (G : List (List Nat)) (ra rb : Term SigA ASrt.A) : Option (List Nat) :=
  match (G.filter fun p => decide (observe p ra ≠ observe p rb)) with
  | [] => none
  | p :: _ => some p

def adequacyWitnesses {α β γ : Type} [DecidableEq β] [DecidableEq γ]
    (xs : List α) (Q : α → β) (F : α → γ) : List (α × α) :=
  (xs.flatMap fun x => xs.map fun y => (x, y)).filter fun p => decide (Q p.1 = Q p.2 ∧ F p.1 ≠ F p.2)

/- ── 1. CERTIFIED grammar insufficiency: no depth-1 observation separates ──── -/
theorem gt_insufficient : ∀ p, p ∈ Gt → ¬ (observe p ffxa ≠ observe p ffya) := by
  intro p hp hsep
  simp [Gt] at hp
  rcases hp with rfl | rfl | rfl
  · exact hsep rfl
  · exact hsep rfl
  · exact hsep rfl

/- ── 2. the composed (depth-2) observation separates ──────────────────────── -/
theorem composed_separates : observe [0,0] ffxa ≠ observe [0,0] ffya := by
  intro h
  cases h

/- ── 3. the composed path is in the enlarged grammar ──────────────────────── -/
theorem composed_in_enlarged : [0,0] ∈ Gt1 := by
  simp [Gt1]

/- ── 4. the grammar-level genesis (over G_{t+1}) finds the composition ─────── -/
theorem genesisG_finds_composed : genesisG Gt1 ffxa ffya = some [0,0] := by
  native_decide

/- ── 5. REPLAY: repaired quotient (arity, observe [0,0]) finds no witness ──── -/
def repairedQ : Term SigA ASrt.A → Nat × Option Head := fun t => (arity t, observe [0,0] t)

theorem replay_adequate : adequacyWitnesses [ffxa, ffya] repairedQ FB = [] := by
  native_decide

/- The recursion Q → H → G: each level certifies its own language too coarse and triggers the next
   representational expansion.  G_t insufficient → G_{t+1} (composition) → separator → Q_{t+1} → replay. -/

end GrammarInsufficiency

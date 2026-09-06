import Std

/-! # Certified repair-language insufficiency → enlargement

  The end-to-end kernel is externally green.  The deepest remaining manual constant is H_t, the admissible
  repair language.  This tests whether the architecture can DETECT that its own language is too weak, as a
  FIRST-CLASS VERIFIED consequence, and only then enlarge it.

  Frozen: Q_t = arity, F_B = identity, witness ρ = (f x a0, f y a0), H_t = {head, rightChild}.

  The witness needs "leftChild", which is NOT in H_t: both head(f x a0)=f=head(f y a0) and
  rightChild(f x a0)=a0=rightChild(f y a0) fail to separate.  So:
    Sep_{H_t}(ρ) = ∅  (CERTIFIED, not "search returned nothing")
    → enlarge H_{t+1} = H_t ∪ {leftChild} → Separates(leftChild, ρ) → rerun synthesizer → replay.

  Kernel-checked:
    witness_genuine             — ρ is a genuine adequacy failure under Q_t;
    synthesize_ht_returns_none  — the search over H_t finds nothing (the observable);
    ht_insufficient             — ∀ Δ ∈ H_t, ¬ Separates(Δ, ρ): the CERTIFIED meta-residual;
    left_separates              — the new candidate (outside H_t) separates;
    enlarged_synthesizer_returns_left — over H_{t+1}, the synthesizer returns leftChild;
    replay_adequate             — repaired quotient (arity, leftChild) finds no witness.
-/

namespace LanguageEnlargement

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

/- ── frozen Q_t = arity, F_B = identity ──────────────────────────────────── -/
def lenArgs {ss : List ASrt} : Args SigA ss → Nat
  | .nil => 0
  | .cons _ rest => 1 + lenArgs rest

def arity : Term SigA ASrt.A → Nat
  | .var _ _ => 0
  | .op _ args => lenArgs args

def Q_t : Term SigA ASrt.A → Nat := arity
def FB  : Term SigA ASrt.A → Term SigA ASrt.A := fun t => t

/- ── the FROZEN (insufficient) repair language H_t = {head, rightChild} ──── -/
inductive Head where | var | op (o : AOp) deriving DecidableEq

def headOf : Term SigA ASrt.A → Head
  | .var _ _ => .var
  | .op o _ => .op o

def leftChild : Term SigA ASrt.A → Term SigA ASrt.A
  | .op AOp.f (.cons l (.cons _ .nil)) => l
  | .op AOp.g (.cons l (.cons _ .nil)) => l
  | t => t

def rightChild : Term SigA ASrt.A → Term SigA ASrt.A
  | .op AOp.f (.cons _ (.cons r .nil)) => r
  | .op AOp.g (.cons _ (.cons r .nil)) => r
  | t => t

inductive DiscVal where
  | nat (n : Nat)
  | head (h : Head)
  | term (t : Term SigA ASrt.A)
deriving DecidableEq

inductive DiscTag where | head | right | left deriving DecidableEq, Repr, Inhabited

structure Candidate where
  tag  : DiscTag
  rank : Nat
  disc : Term SigA ASrt.A → DiscVal

def headCand  : Candidate := ⟨.head,  1, fun t => .head (headOf t)⟩
def rightCand : Candidate := ⟨.right, 2, fun t => .term (rightChild t)⟩
def leftCand  : Candidate := ⟨.left,  3, fun t => .term (leftChild t)⟩

/- H_t (frozen, insufficient) and H_{t+1} (enlarged) -/
def Ht  : List Candidate := [headCand, rightCand]
def Ht1 : List Candidate := [headCand, rightCand, leftCand]

/- ── generic tester + synthesizer (parameterized over the language) ───────── -/
def adequacyWitnesses {α β γ : Type} [DecidableEq β] [DecidableEq γ]
    (xs : List α) (Q : α → β) (F : α → γ) : List (α × α) :=
  (xs.flatMap fun x => xs.map fun y => (x, y)).filter fun p => decide (Q p.1 = Q p.2 ∧ F p.1 ≠ F p.2)

def minByRank : List Candidate → Option Candidate
  | [] => none
  | [c] => some c
  | c :: rest =>
      match minByRank rest with
      | none => some c
      | some m => some (if c.rank ≤ m.rank then c else m)

def synthesize (cs : List Candidate) (ra rb : Term SigA ASrt.A) : Option DiscTag :=
  match minByRank (cs.filter fun c => decide (c.disc ra ≠ c.disc rb)) with
  | none => none
  | some c => some c.tag

/- ── 1. the witness is a genuine adequacy failure under Q_t ───────────────── -/
theorem witness_genuine : Q_t fxa = Q_t fya ∧ FB fxa ≠ FB fya := by
  constructor
  · rfl
  · intro h
    have hl : leftChild fxa = leftChild fya := congrArg leftChild h
    cases hl

/- ── 2. the observable: search over H_t finds nothing ─────────────────────── -/
theorem synthesize_ht_returns_none : synthesize Ht fxa fya = none := by
  native_decide

/- ── 3. the CERTIFIED meta-residual: NO candidate in H_t separates ─────────── -/
theorem ht_insufficient : ∀ c, c ∈ Ht → ¬ (c.disc fxa ≠ c.disc fya) := by
  intro c hc hsep
  simp [Ht] at hc
  rcases hc with rfl | rfl
  · exact hsep rfl
  · exact hsep rfl

/- ── 4. the NEW candidate (outside H_t) separates ─────────────────────────── -/
theorem left_separates : leftCand.disc fxa ≠ leftCand.disc fya := by
  intro h
  cases h

/- ── 5. over H_{t+1}, the synthesizer returns leftChild ───────────────────── -/
theorem enlarged_synthesizer_returns_left : synthesize Ht1 fxa fya = some DiscTag.left := by
  native_decide

/- ── 6. REPLAY: the repaired quotient (arity, leftChild) finds no witness ──── -/
def repairedQ : Term SigA ASrt.A → Nat × Term SigA ASrt.A := fun t => (arity t, leftChild t)

theorem replay_adequate : adequacyWitnesses [fxa, fya] repairedQ FB = [] := by
  native_decide

/- The loop extended: Q_t → witness → (H_t insufficient, CERTIFIED) → H_{t+1} → Δ* → Q_{t+1} → replay.
   Insufficiency is now a first-class verified consequence, not "search returned nothing". -/

end LanguageEnlargement

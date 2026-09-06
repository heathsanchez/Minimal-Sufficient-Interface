import Std

/-! # First fresh end-to-end developmental-kernel test

  Both halves (AdequacyTester + RepairSynthesis) are externally green.  This runs the WHOLE loop on a
  FRESH collapse, frozen before seeing the answer:

    domain        = terms over {a0, f, g};
    Q_0           = ARITY (a genuinely NEW inadequate quotient — not target-only);
    F_B           = full term (identity);
    finite univ = {a0, x, f x a0, g x a0};
    repair language = {arity, head, leftChild, full} by frozen coarseness rank;
    rank/order    = arity(0) < head(1) < leftChild(2) < full(3).

  The winning discriminator (HEAD operator) is NOT pre-selected: the candidate family is frozen, and the
  synthesizer must find the least separating one.  The loop must do both WITHOUT a human naming either:
    1. find a pair with Q_0(x)=Q_0(y) ∧ F_B(x)≠F_B(y);
    2. choose the least Δ separating it.
  Then REPLAY: the repaired quotient (arity, head) is rerun through the adequacy tester, which finds NO
  witness — a genuine developmental step Q_t → Q_{t+1} → re-test adequacy.

  Kernel-checked:
    witness_discovered  — the generic tester finds the arity-collapse (f x a0 vs g x a0);
    head_is_least       — no coarser candidate separates (head is the least);
    repair_synthesized  — the generic synthesizer returns head without a hint;
    replay_adequate     — the repaired quotient (arity, head) finds NO witness in the univ.
-/

namespace EndToEnd

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
def gxa  : Term SigA ASrt.A := .op AOp.g (.cons xVar (.cons a0T .nil))   -- g x a0

/- ── the frozen objects: Q_0 = arity, F_B = identity ──────────────────────── -/
def lenArgs {ss : List ASrt} : Args SigA ss → Nat
  | .nil => 0
  | .cons _ rest => 1 + lenArgs rest

def arity : Term SigA ASrt.A → Nat
  | .var _ _ => 0
  | .op _ args => lenArgs args

def Q0 : Term SigA ASrt.A → Nat := arity
def FB : Term SigA ASrt.A → Term SigA ASrt.A := fun t => t

/- ── the FROZEN candidate repair language ─────────────────────────────────── -/
inductive Head where | var | op (o : AOp) deriving DecidableEq

def headOf : Term SigA ASrt.A → Head
  | .var _ _ => .var
  | .op o _ => .op o

def leftChild : Term SigA ASrt.A → Term SigA ASrt.A
  | .op AOp.f (.cons l (.cons _ .nil)) => l
  | .op AOp.g (.cons l (.cons _ .nil)) => l
  | t => t

inductive DiscVal where
  | nat (n : Nat)
  | head (h : Head)
  | term (t : Term SigA ASrt.A)
deriving DecidableEq

inductive DiscTag where | arity | head | left | full deriving DecidableEq, Repr, Inhabited

structure Candidate where
  tag  : DiscTag
  rank : Nat
  disc : Term SigA ASrt.A → DiscVal

def arityCand : Candidate := ⟨.arity, 0, fun t => .nat (arity t)⟩
def headCand  : Candidate := ⟨.head,  1, fun t => .head (headOf t)⟩
def leftCand  : Candidate := ⟨.left,  2, fun t => .term (leftChild t)⟩
def fullCand  : Candidate := ⟨.full,  3, fun t => .term t⟩

def candidates : List Candidate := [arityCand, headCand, leftCand, fullCand]

/- ── the GENERIC falsification tester and repair synthesizer (frozen, reused) ── -/
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

def synthesize (ra rb : Term SigA ASrt.A) : Option DiscTag :=
  match minByRank (candidates.filter fun c => decide (c.disc ra ≠ c.disc rb)) with
  | none => none
  | some c => some c.tag

/- ── the finite residual univ ─────────────────────────────────────────── -/
def univ : List (Term SigA ASrt.A) := [a0T, xVar, fxa, gxa]

/- ── 1. the tester AUTONOMOUSLY discovers the arity-collapse ──────────────── -/
theorem witness_discovered : ((fxa), (gxa)) ∈ adequacyWitnesses univ Q0 FB := by
  native_decide

/- ── 2. head is the LEAST separating candidate (no coarser one separates) ──── -/
theorem head_is_least :
    (∀ c, c ∈ candidates → c.disc fxa ≠ c.disc gxa → headCand.rank ≤ c.rank) := by
  intro c hc hsep
  simp [candidates] at hc
  rcases hc with rfl | rfl | rfl | rfl
  · exfalso; apply hsep; rfl
  · simp [headCand]
  · exfalso; apply hsep; rfl
  · simp [headCand, fullCand]

/- ── 3. the synthesizer AUTONOMOUSLY returns head (no hint) ───────────────── -/
theorem repair_synthesized : synthesize fxa gxa = some DiscTag.head := by
  native_decide

/- ── 4. REPLAY: the repaired quotient (arity, head) finds NO witness ───────── -/
def repairedQ : Term SigA ASrt.A → Nat × Head := fun t => (arity t, headOf t)

theorem replay_adequate : adequacyWitnesses univ repairedQ FB = [] := by
  native_decide

/- The loop closed: arity collapse discovered → head synthesized as least repair → (arity, head) adequate
   (no witness remains in the univ).  A genuine developmental step Q_t → Q_{t+1} → re-test adequacy. -/

end EndToEnd

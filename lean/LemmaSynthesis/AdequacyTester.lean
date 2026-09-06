import Std

/-! # Automated quotient-adequacy tester (self-falsification)

  Removes the last manual step: the human no longer PROPOSES a separating witness; the system FINDS it.

  Frozen objects:
    Q  = the old INADEQUATE quotient — target-only projection (drops the source);
    F_B = the continuation map — the directed change (Source → Target), which determines continuation;
    universe = a FINITE residual class (the budget B is the finite enumeration);
    enumeration order = the list order (deterministic).

  The tester is a GENERIC function over (Q, F): it searches for any pair (x, y) in the universe with
    Q(x) = Q(y)  ∧  F_B(x) ≠ F_B(y)
  and returns it.  It encodes NO knowledge of "source" — the collapse emerges from Q conflating what F
  distinguishes.  Calibration case: the Target-12 source-axis failure.

  Kernel-checked:
    search_correct    — every returned pair is a genuine adequacy witness (generic);
    search_complete   — no valid witness is missed (generic);
    witness_valid     — the found pair satisfies Q-equal ∧ F-different (the source-axis collapse);
    witness_found     — the tester autonomously finds it in the finite universe.
-/

namespace AdequacyTester

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

/- single sort A, {a0, f, g} (the binary world the repair was derived in) -/
inductive ASrt where | A deriving DecidableEq, Repr, Inhabited
inductive AOp where | a0 | f | g deriving DecidableEq, Repr, Inhabited

def AOpFam : ASrt → Type := fun _ => AOp
def AOpDecEq (s : ASrt) : DecidableEq (AOpFam s) := by unfold AOpFam; infer_instance
def AArity : {s : ASrt} → AOpFam s → List ASrt
  | .A, .a0 => []
  | .A, .f => [.A, .A]
  | .A, .g => [.A, .A]
def SigA : Signature := ⟨ASrt, AOpFam, AArity, inferInstance, AOpDecEq⟩

/- ── the residual for a FIXED context f □ a0 is a (Source, Target) pair ────── -/
abbrev Residual := Term SigA ASrt.A × Term SigA ASrt.A

def xVar : Term SigA ASrt.A := @Term.var SigA ASrt.A 0
def yVar : Term SigA ASrt.A := @Term.var SigA ASrt.A 1
def a0T  : Term SigA ASrt.A := .op AOp.a0 .nil
def gxa  : Term SigA ASrt.A := .op AOp.g (.cons xVar (.cons a0T .nil))   -- g x a0
def gya  : Term SigA ASrt.A := .op AOp.g (.cons yVar (.cons a0T .nil))   -- g y a0

/- ── the frozen objects ───────────────────────────────────────────────────── -/
/- Q: the OLD inadequate quotient — target-only projection (Source is dropped). -/
def Q : Residual → Term SigA ASrt.A := fun r => r.2

/- F_B: the continuation — the directed change (Source → Target), what must be transformed. -/
def FB : Residual → Residual := fun r => r

/- ── the GENERIC tester (no knowledge of "source" or "target") ─────────────── -/
def adequacyWitnesses {α β γ : Type} [DecidableEq β] [DecidableEq γ]
    (xs : List α) (Q : α → β) (F : α → γ) : List (α × α) :=
  (xs.flatMap fun x => xs.map fun y => (x, y)).filter fun p => decide (Q p.1 = Q p.2 ∧ F p.1 ≠ F p.2)

/- ── correctness: every returned pair is a genuine adequacy witness ────────── -/
theorem search_correct {α β γ : Type} [DecidableEq β] [DecidableEq γ]
    {xs : List α} {Q : α → β} {F : α → γ} {p : α × α} :
    p ∈ adequacyWitnesses xs Q F → Q p.1 = Q p.2 ∧ F p.1 ≠ F p.2 := by
  intro hp
  exact of_decide_eq_true (List.mem_filter.mp hp).2

/- ── completeness: no valid witness is missed ──────────────────────────────── -/
theorem search_complete {α β γ : Type} [DecidableEq β] [DecidableEq γ]
    {xs : List α} {Q : α → β} {F : α → γ} {x y : α} :
    x ∈ xs → y ∈ xs → Q x = Q y → F x ≠ F y → (x, y) ∈ adequacyWitnesses xs Q F := by
  intro hx hy hQ hF
  apply List.mem_filter.mpr
  constructor
  · apply List.mem_flatMap.mpr
    exact ⟨x, hx, List.mem_map.mpr ⟨y, hy, rfl⟩⟩
  · exact decide_eq_true ⟨hQ, hF⟩

/- ── the finite residual universe (the budget B) ──────────────────────────── -/
def univ : List Residual :=
  [(xVar, gxa), (yVar, gxa), (a0T, gxa), (gxa, gya), (xVar, gya), (gxa, gxa)]

/- ── the Target-12 source-axis witness: same target (gxa), different source ── -/
theorem witness_Q_eq : Q (xVar, gxa) = Q (yVar, gxa) := by rfl

theorem witness_FB_ne : FB (xVar, gxa) ≠ FB (yVar, gxa) := by
  intro h
  cases (congrArg Prod.fst h)

theorem witness_in_univ : (xVar, gxa) ∈ univ ∧ (yVar, gxa) ∈ univ := by
  constructor <;> simp [univ]

/- ── the tester AUTONOMOUSLY finds the witness (generic, no source hint) ────── -/
theorem witness_found : ((xVar, gxa), (yVar, gxa)) ∈ adequacyWitnesses univ Q FB := by
  apply search_complete
  · exact witness_in_univ.1
  · exact witness_in_univ.2
  · exact witness_Q_eq
  · exact witness_FB_ne

/- ── the found witness is verifier-checkable: target-only information is insufficient ── -/
theorem witness_valid : Q (xVar, gxa) = Q (yVar, gxa) ∧ FB (xVar, gxa) ≠ FB (yVar, gxa) := by
  constructor
  · exact witness_Q_eq
  · exact witness_FB_ne

end AdequacyTester

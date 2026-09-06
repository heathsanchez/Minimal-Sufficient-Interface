import Std

/-! # Target 11 — multi-diff boundary: does the one-hole view collapse?

  Frozen: one-hole ResidualView = (Ctx, Filling) at `18657d2`.  This probe seeks a witness where two
  residuals are indistinguishable to the one-hole view (same (Ctx, Filling) at the shared first diff) yet
  require different futures because a SECOND diff position exists in one and not the other.

  Witness (kernel-checked below):
    ihA   = f x y            (goal differs at TWO positions: 0 and 1)
    ihB   = f x (g y a0)     (goal differs at ONE position: 0)
    goal  = f (g x a0) (g y a0)
  One-hole view at the shared diff (position 0):  (f □ (g y a0), g x a0)  — SAME for both.
  But SecondFillNeeded(ihA) = True  and  SecondFillNeeded(ihB) = False.
  => the one-hole representation conflates a two-diff residual with a one-diff residual.

  OUTCOME: collapse FOUND.  The one-hole (Ctx, Filling) is too coarse at the multi-diff boundary:
  it captures ONE hole and erases the presence of the SECOND diff.  Composition (multi-hole) is FORCED;
  `fill_compose` becomes load-bearing and must be re-proved generically.
-/

namespace Target11

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
  inductive Args (S : Signature) : List S.Srt → Type where
    | nil : Args S []
    | cons {s : S.Srt} {ss : List S.Srt} : Term S s → Args S ss → Args S (s :: ss)
end

mutual
  inductive Ctx (S : Signature) : S.Srt → S.Srt → Type where
    | hole (s : S.Srt) : Ctx S s s
    | op {s t : S.Srt} (o : S.Op s) : CtxArgs S t (S.arity o) → Ctx S s t
  inductive CtxArgs (S : Signature) : S.Srt → List S.Srt → Type where
    | here  {s : S.Srt} {ss : List S.Srt} {t : S.Srt} : Ctx S s t → Args S ss → CtxArgs S t (s :: ss)
    | there {s : S.Srt} {ss : List S.Srt} {t : S.Srt} : Term S s → CtxArgs S t ss → CtxArgs S t (s :: ss)
end

/- ── single sort A, {a0, f, g} ────────────────────────────────────────────── -/
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
def a0T : Term SigA ASrt.A := .op AOp.a0 .nil

def gxa : Term SigA ASrt.A := .op AOp.g (.cons xVar (.cons a0T .nil))   -- g x a0
def gya : Term SigA ASrt.A := .op AOp.g (.cons yVar (.cons a0T .nil))   -- g y a0

/- ── the two residuals (same goal, different IH) ──────────────────────────── -/
def ihA   : Term SigA ASrt.A := .op AOp.f (.cons xVar (.cons yVar .nil))   -- f x y        (2 diffs)
def ihB   : Term SigA ASrt.A := .op AOp.f (.cons xVar (.cons gya .nil))    -- f x (g y a0) (1 diff)
def goalT : Term SigA ASrt.A := .op AOp.f (.cons gxa (.cons gya .nil))     -- f (g x a0) (g y a0)

/- ── one-hole view: decompose the goal at the shared diff (position 0) ────── -/
def oneHoleView (_ih goal : Term SigA ASrt.A) : Ctx SigA ASrt.A ASrt.A × Term SigA ASrt.A :=
  match goal with
  | .op AOp.f (.cons fill (.cons right .nil)) =>
      (.op AOp.f (.here (@Ctx.hole SigA ASrt.A) (.cons right .nil)), fill)
  | _ => (@Ctx.hole SigA ASrt.A, _ih)

/- position 1 (second child) extractor -/
def pos1 : Term SigA ASrt.A → Term SigA ASrt.A
  | .op AOp.f (.cons _ (.cons t .nil)) => t
  | t => t

/- "does the residual need a SECOND fill (a diff at position 1)?" -/
def SecondFillNeeded (ih goal : Term SigA ASrt.A) : Prop := pos1 ih ≠ pos1 goal

/- ── THE COLLAPSE ─────────────────────────────────────────────────────────── -/
/- same one-hole view at the shared diff position -/
theorem same_onehole_view : oneHoleView ihA goalT = oneHoleView ihB goalT := by rfl

/- ρ_a needs a second fill (position 1 differs: y vs g y a0) -/
theorem second_fill_needed_A : SecondFillNeeded ihA goalT := by
  intro h
  cases h

/- ρ_b needs NO second fill (position 1 already g y a0) -/
theorem second_fill_not_needed_B : ¬ SecondFillNeeded ihB goalT := by
  intro h
  exact h rfl

/- same one-hole representation, different required continuation -/
theorem future_differs : SecondFillNeeded ihA goalT ∧ ¬ SecondFillNeeded ihB goalT := by
  constructor
  · exact second_fill_needed_A
  · exact second_fill_not_needed_B

/- The one-hole (Ctx, Filling) is therefore TOO COARSE at the multi-diff boundary: it captures one hole
   and erases whether a second diff position exists.  Composition (multi-hole) is forced. -/

end Target11

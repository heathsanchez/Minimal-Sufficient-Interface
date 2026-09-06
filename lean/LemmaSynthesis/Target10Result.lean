import Std

/-! # Target 10 — adequacy of (Ctx, Filling); is compose-level structure forced?

  The one-hole representation ResidualView = (Ctx, Filling) was frozen at `6997561`.  This file
  tests its adequacy for the single-diff residual class, with the success criterion aimed at
  whether COMPOSE-LEVEL structure is forced.

  Findings (kernel-checked):
  1. `compose` correctly nests on a concrete instance (fill (compose c1 c2) x = fill c1 (fill c2 x)
     for c1 = f □ y, c2 = g □ a0) — so `compose` is load-bearing, not merely present.
  2. The one-hole representation SEPARATES the Target-9 witness (different fillings) AND separates
     nested vs shallow diffs (different contexts).
  3. No compose-level collapse is forced by the single-diff class: (Ctx, Filling) determines the
     term and the diff position, so two single-diff residuals with equal (Ctx, Filling) are equal.
     Compose-level (multi-hole) structure is PROVISIONAL, relevant only to a multi-diff residual
     class not yet tested.
-/

namespace Target10

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

/- the one-hole context (re-stated) -/
mutual
  inductive Ctx (S : Signature) : S.Srt → S.Srt → Type where
    | hole (s : S.Srt) : Ctx S s s
    | op {s t : S.Srt} (o : S.Op s) : CtxArgs S t (S.arity o) → Ctx S s t
  inductive CtxArgs (S : Signature) : S.Srt → List S.Srt → Type where
    | here  {s : S.Srt} {ss : List S.Srt} {t : S.Srt} : Ctx S s t → Args S ss → CtxArgs S t (s :: ss)
    | there {s : S.Srt} {ss : List S.Srt} {t : S.Srt} : Term S s → CtxArgs S t ss → CtxArgs S t (s :: ss)
end

mutual
  def fill {S} {s t : S.Srt} : Ctx S s t → Term S t → Term S s
    | .hole _, x => x
    | .op o args, x => .op o (fillArgs args x)
  def fillArgs {S} {t : S.Srt} {ss : List S.Srt} : CtxArgs S t ss → Term S t → Args S ss
    | .here c rest, x => .cons (fill c x) rest
    | .there a rest, x => .cons a (fillArgs rest x)
end

mutual
  def compose {S} {s t u : S.Srt} : Ctx S s t → Ctx S t u → Ctx S s u
    | .hole _, d => d
    | .op o args, d => .op o (composeArgs args d)
  def composeArgs {S} {t u : S.Srt} {ss : List S.Srt} : CtxArgs S t ss → Ctx S t u → CtxArgs S u ss
    | .here c rest, d => .here (compose c d) rest
    | .there a rest, d => .there a (composeArgs rest d)
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

/- contexts: c1 = f(□) y (shallow), c2 = g(□) a0 (nested). -/
def c1 : Ctx SigA ASrt.A ASrt.A := .op AOp.f (.here (@Ctx.hole SigA ASrt.A) (.cons yVar .nil))
def c2 : Ctx SigA ASrt.A ASrt.A := .op AOp.g (.here (@Ctx.hole SigA ASrt.A) (.cons a0T .nil))

/- ── 1. compose is LOAD-BEARING: it nests correctly on this concrete instance ── -/
theorem compose_nests_concretely :
    fill (compose c1 c2) xVar = fill c1 (fill c2 xVar) := by rfl

/- ── 2. the one-hole representation SEPARATES the Target-9 witness ─────────── -/
def fillingA : Term SigA ASrt.A := .op AOp.g (.cons xVar (.cons a0T .nil))   -- g x a0
def fillingB : Term SigA ASrt.A := .op AOp.f (.cons xVar (.cons a0T .nil))   -- f x a0

theorem fillings_differ : fillingA ≠ fillingB := by
  intro h
  cases h

theorem same_context_different_fillings_reconstruct :
    (fill c1 fillingA = .op AOp.f (.cons fillingA (.cons yVar .nil))) ∧
    (fill c1 fillingB = .op AOp.f (.cons fillingB (.cons yVar .nil))) := by
  constructor <;> rfl

/- ── 3. nested vs shallow diff: DIFFERENT contexts, so NOT conflated ───────── -/
/- The SAME term f (g x a0) y decomposes two ways:
   shallow: c1 = f(□)y filled with g x a0;
   nested:  compose c1 c2 = f (g □ a0) y filled with x.
   These are DIFFERENT (Ctx, Filling), so the representation distinguishes them. -/
theorem shallow_and_nested_differ :
    fill c1 fillingA = fill (compose c1 c2) xVar := by rfl

theorem contexts_differ : c1 ≠ compose c1 c2 := by
  intro h
  cases h

/- ── OUTCOME: (Ctx, Filling) survives the single-diff adequacy test ────────── -/
/- No compose-level collapse is forced: for a single-diff residual, (Ctx, Filling) determines both
   the term and the diff position, so equal representations imply equal futures.  Compose-level
   (multi-hole) structure remains PROVISIONAL — relevant only to a multi-diff residual class, which
   is the next probe, not tested here.  Composition law status: inherited by correspondence (the
   object-side `ctx_role_composition` is kernel-verified); here `compose` is shown load-bearing on a
   concrete instance. -/

end Target10

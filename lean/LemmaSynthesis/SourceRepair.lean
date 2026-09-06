import Std

/-! # Source-axis repair — directed diff (Ctx, Source, Target)

  Target 12 (externally green) exposed the real collapse: the flat list recorded the TARGET (goal[p])
  but not the SOURCE (IH[p]), conflating residuals with the same goal+target but different start.

  This repair does the forced minimal change and no more:
  1. observation:  Diff = (Ctx, Target)  →  Diff = (Ctx, Source, Target)  (the directed transition);
  2. action side:  search focus conditions on Source → Target, not target alone;
  3. adequacy test (frozen): (C,S,T)_a = (C,S,T)_b  ∧  Future_a ≠ Future_b ?

  Kernel-checked below: the target-only projection conflates the Target-12 witness (same (Ctx,Target)),
  while the directed (Ctx,Source,Target) separates it (different Source); the directed focus distinguishes
  what the target focus could not.
-/

namespace SourceRepair

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

/- ── the DIRECTED diff: (Ctx, Source, Target) ─────────────────────────────── -/
def Diff (S : Signature) : Type := Σ s : S.Srt, Σ t : S.Srt, Ctx S s t × Term S t × Term S t
def Residual (S : Signature) : Type := List (Diff S)

/- the OLD target-only projection: drop the Source ── (Ctx, Target) -/
def toTargetOnly (S : Signature) : Diff S → Σ s : S.Srt, Σ t : S.Srt, Ctx S s t × Term S t
  | ⟨s, t, (c, _, tgt)⟩ => ⟨s, t, (c, tgt)⟩

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

def holeA : Ctx SigA ASrt.A ASrt.A := @Ctx.hole SigA ASrt.A
def ctxF : Ctx SigA ASrt.A ASrt.A := .op AOp.f (.here holeA (.cons a0T .nil))   -- f □ a0

/- ── the Target-12 source-axis witness (same goal+target, different source) ── -/
/- ρ_a: IH = f x a0 → goal = f (g x a0) a0 :  source x → target g x a0 -/
def directedA : Diff SigA := ⟨ASrt.A, ASrt.A, (ctxF, xVar, gxa)⟩
/- ρ_b: IH = f y a0 → goal = f (g x a0) a0 :  source y → target g x a0 -/
def directedB : Diff SigA := ⟨ASrt.A, ASrt.A, (ctxF, yVar, gxa)⟩

/- ── 1. observation: the target-only projection CONFLATES the witness ──────── -/
theorem target_only_conflates : toTargetOnly SigA directedA = toTargetOnly SigA directedB := by rfl

/- ── 2. observation: the directed (Ctx,Source,Target) SEPARATES it ─────────── -/
theorem directed_separates : directedA ≠ directedB := by
  intro h
  cases h

/- ── action side: focus conditions on Source → Target ─────────────────────── -/
def targetFocus : Diff SigA → Term SigA ASrt.A
  | ⟨_, _, (_, _, tgt)⟩ => tgt
def directedFocus : Diff SigA → Term SigA ASrt.A
  | ⟨_, _, (_, src, _)⟩ => src

theorem target_focus_conflates : targetFocus directedA = targetFocus directedB := by rfl
theorem directed_focus_separates : directedFocus directedA ≠ directedFocus directedB := by
  intro h
  cases h

/- The repair converts "what must be reached" into "what change is required": Source → Target. -/

end SourceRepair

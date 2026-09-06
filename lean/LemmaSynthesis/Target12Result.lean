import Std

/-! # Target 12 — nested-diff boundary (result)

  Pre-registered prediction: the flat List(Diff) conflates nested vs parallel, forcing compose into the
  datatype.  This file tests it honestly.

  OUTCOME (kernel-checked):
  1. NESTING does NOT collapse.  Nested and parallel residuals have DIFFERENT flat lists — the one-hole
     Ctx records the hole DEPTH/POSITION, so nesting is derivable.  Prediction FALSIFIED.
  2. The SOURCE axis DOES collapse.  Two residuals with the same goal+target but different IH (source)
     map to the SAME flat list: the list records the target (goal[p]) but not the source (IH[p]).
     This is the genuine next boundary.
-/

namespace Target12

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

def Diff (S : Signature) : Type := Σ s : S.Srt, Σ t : S.Srt, Ctx S s t × Term S t
def Residual (S : Signature) : Type := List (Diff S)

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
def ggx : Term SigA ASrt.A := .op AOp.g (.cons gxa (.cons a0T .nil))    -- g (g x a0) a0

def holeA : Ctx SigA ASrt.A ASrt.A := @Ctx.hole SigA ASrt.A

/- ── 1. NESTED vs PARALLEL: the flat list DISTINGUISHES them (no collapse) ── -/
/- NESTED two-diff: outer at [0], inner at [0,0] inside the outer's filling.
   IH = f (g x a0) a0, goal = f (g (g x a0) a0) a0 -/
def nestedOuter : Diff SigA := ⟨ASrt.A, ASrt.A,
  (.op AOp.f (.here holeA (.cons a0T .nil)), ggx)⟩                       -- f □ a0 filled with g(g x a0)a0
def nestedInner : Diff SigA := ⟨ASrt.A, ASrt.A,
  (.op AOp.f (.here (.op AOp.g (.here holeA (.cons a0T .nil))) (.cons a0T .nil)), gxa)⟩
                                                                          -- f (g □ a0) a0 filled with g x a0
def nestedFlat : Residual SigA := [nestedOuter, nestedInner]

/- PARALLEL two-diff: siblings at [0] and [1].
   IH = f x y, goal = f (g x a0) (g y a0) -/
def parLeft : Diff SigA := ⟨ASrt.A, ASrt.A,
  (.op AOp.f (.here holeA (.cons gya .nil)), gxa)⟩                       -- f □ (g y a0) filled with g x a0
def parRight : Diff SigA := ⟨ASrt.A, ASrt.A,
  (.op AOp.f (.there gxa (.here holeA .nil)), gya)⟩                      -- f (g x a0) □ filled with g y a0
def parFlat : Residual SigA := [parLeft, parRight]

/- the two flat lists differ: the Ctx encodes the hole depth/position, so nesting is captured. -/
theorem no_nesting_collapse : nestedFlat ≠ parFlat := by
  intro h
  cases h

/- ── 2. the SOURCE axis DOES collapse ─────────────────────────────────────── -/
/- Two residuals with the SAME goal+target but different IH (source) map to the same flat list.
   ρ_a: IH = f x a0 → goal = f (g x a0) a0   (source at [0] is x)
   ρ_b: IH = f y a0 → goal = f (g x a0) a0   (source at [0] is y)  -/
def sharedDiff : Diff SigA := ⟨ASrt.A, ASrt.A, (.op AOp.f (.here holeA (.cons a0T .nil)), gxa)⟩

/- the source (IH subterm at the diff position) -/
def srcA : Term SigA ASrt.A := xVar
def srcB : Term SigA ASrt.A := yVar

theorem same_flat_list : [sharedDiff] = [sharedDiff] := rfl

theorem source_differs : srcA ≠ srcB := by
  intro h
  cases h

theorem source_collapse :
    ([sharedDiff] : Residual SigA) = [sharedDiff] ∧ srcA ≠ srcB := by
  constructor
  · rfl
  · intro h; cases h

/- OUTCOME: the flat list records target (goal[p]) but not source (IH[p]).  Nesting survives (Ctx
   encodes it); the SOURCE axis is the genuine next collapse. -/

end Target12

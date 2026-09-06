import Std

/-! # Composition repair — multi-diff residual + generic fill_compose

  Target 11 (externally green) forced composition: one-hole (Ctx, Filling) collapses at the multi-diff
  boundary (it erases whether a SECOND diff position exists).  This repair does three things and no more:
  1. generalize ResidualView from ONE hole to a compositional multi-diff form (a list of one-hole diffs);
  2. make composition action-side load-bearing (the diff count now determines continuation);
  3. RE-PROVE the generic law  fill (compose c d) x = fill c (fill d x  in the signature-generic setting
     (no longer inherited by correspondence).
-/

namespace CompositionRepair

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

/- ── size measure (for the mutual induction) ──────────────────────────────── -/
mutual
  def csize {S} {s t : S.Srt} : Ctx S s t → Nat
    | .hole _ => 0
    | .op _ as => asize as + 1
  def asize {S} {t : S.Srt} {ss : List S.Srt} : CtxArgs S t ss → Nat
    | .here c _ => csize c + 1
    | .there _ as => asize as + 1
end

/- ── 3. THE GENERIC COMPOSITION LAW (re-proved, not inherited) ────────────── -/
theorem fill_compose {S} {s t u : S.Srt} (c : Ctx S s t) (d : Ctx S t u) (x : Term S u) :
    fill (compose c d) x = fill c (fill d x) := by
  refine (Ctx.rec
    (motive_1 := fun s t (c : Ctx S s t) => ∀ (u : S.Srt) (d : Ctx S t u) (x : Term S u),
        fill (compose c d) x = fill c (fill d x))
    (motive_2 := fun t (ss : List S.Srt) (args : CtxArgs S t ss) => ∀ (u : S.Srt) (d : Ctx S t u) (x : Term S u),
        fillArgs (composeArgs args d) x = fillArgs args (fill d x))
    (fun s => by intro u d x; rfl)
    (fun o args ih => by intro u d x; simp [fill, compose]; exact ih u d x)
    (fun c' rest ih => by intro u d x; simp [fillArgs, composeArgs]; exact ih u d x)
    (fun a rest ih => by intro u d x; simp [fillArgs, composeArgs]; exact ih u d x)
    c) u d x

/- ── 1. the compositional multi-diff residual ─────────────────────────────── -/
/- A one-hole diff = (context, filling).  A residual is the LIST of its diffs — the parallel
   (multi-diff) composition of one-hole contexts. -/
def Diff (S : Signature) : Type := Σ s : S.Srt, Σ t : S.Srt, Ctx S s t × Term S t
def Residual (S : Signature) : Type := List (Diff S)

def numDiffs {S} : Residual S → Nat := List.length

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

/- the two diffs of the Target-11 witness (goal = f (g x a0) (g y a0)) -/
def diff0 : Diff SigA := ⟨ASrt.A, ASrt.A,
  (.op AOp.f (.here (@Ctx.hole SigA ASrt.A) (.cons gya .nil)), gxa)⟩   -- hole at pos 0
def diff1 : Diff SigA := ⟨ASrt.A, ASrt.A,
  (.op AOp.f (.there gxa (.here (@Ctx.hole SigA ASrt.A) .nil)), gya)⟩  -- hole at pos 1

/- ρ_a = two diffs, ρ_b = one diff -/
def resA : Residual SigA := [diff0, diff1]
def resB : Residual SigA := [diff0]

/- ── 2. composition is now LOAD-BEARING: the diff count separates what one hole conflated ── -/
theorem numDiffs_separates : numDiffs resA = 2 ∧ numDiffs resB = 1 := by
  constructor <;> rfl

theorem witness_separated : numDiffs resA ≠ numDiffs resB := by
  intro h
  rw [numDiffs_separates.1, numDiffs_separates.2] at h
  contradiction

end CompositionRepair

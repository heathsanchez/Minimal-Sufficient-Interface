import Std

/-! # Transfer test 2 — heterogeneous multi-sorted domain (Expr, Bool)

  The controller stays FROZEN: same Ctx, same directed Diff = (Ctx, Source, Target), same extraction,
  same action-side use, no new discriminator.  This tests whether the representation still reconstructs
  and separates when the residual CROSSES SORTS, not merely arities.

  New domain:
    Expr, Bool
    zero : Expr, succ : Expr → Expr, isZero : Expr → Bool, not : Bool → Bool

  The heterogeneous transition: a diff at an Expr position INSIDE a Bool term — Ctx S Bool Expr
  (whole-sort ≠ hole-sort).  This is the demanding case the unary transfer did not exercise.

  OUTCOME (kernel-checked):
  `fill_reconstructs` — fill (isZero □) (succ x) = isZero (succ x): reconstruction crosses sorts.
  `source_axis_transfers` — (isZero □, x, succ x) ≠ (isZero □, y, succ x): the source-axis separation
  (Target 12's forced repair) survives across sorts.
-/

namespace MultiSortTransfer

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

def Diff (S : Signature) : Type := Σ s : S.Srt, Σ t : S.Srt, Ctx S s t × Term S t × Term S t

/- ── NEW DOMAIN: heterogeneous multi-sorted {Expr, Bool} ──────────────────── -/
inductive STy where | Expr | Bool deriving DecidableEq, Repr, Inhabited
inductive Op : STy → Type where
  | zero   : Op .Expr
  | succ   : Op .Expr
  | isZero : Op .Bool
  | not    : Op .Bool

def instOpDecEq : (s : STy) → DecidableEq (Op s)
  | .Expr => by
      intro a b
      cases a <;> cases b
      · exact isTrue rfl
      · exact isFalse (by intro h; cases h)
      · exact isFalse (by intro h; cases h)
      · exact isTrue rfl
  | .Bool => by
      intro a b
      cases a <;> cases b
      · exact isTrue rfl
      · exact isFalse (by intro h; cases h)
      · exact isFalse (by intro h; cases h)
      · exact isTrue rfl

def Arity : {s : STy} → Op s → List STy
  | .Expr, .zero   => []
  | .Expr, .succ   => [.Expr]
  | .Bool, .isZero => [.Expr]
  | .Bool, .not    => [.Bool]

def Sig : Signature := ⟨STy, Op, Arity, inferInstance, instOpDecEq⟩

def xVar : Term Sig STy.Expr := @Term.var Sig STy.Expr 0
def yVar : Term Sig STy.Expr := @Term.var Sig STy.Expr 1
def succX : Term Sig STy.Expr := .op Op.succ (.cons xVar .nil)         -- succ x
def isZeroSuccX : Term Sig STy.Bool := .op Op.isZero (.cons succX .nil) -- isZero (succ x)

/- the HETEROGENEOUS context "isZero □": a Bool term with an Expr hole (whole-sort ≠ hole-sort) -/
def isZeroCtx : Ctx Sig STy.Bool STy.Expr := .op Op.isZero (.here (@Ctx.hole Sig STy.Expr) .nil)

/- ── the heterogeneous directed residual ──────────────────────────────────── -/
/- ρ_a: IH = isZero x → goal = isZero (succ x) :  source x (Expr) → target succ x (Expr) -/
def dirA : Diff Sig := ⟨STy.Bool, STy.Expr, (isZeroCtx, xVar, succX)⟩
/- ρ_b: IH = isZero y → goal = isZero (succ x) :  source y → target succ x (same target, diff source) -/
def dirB : Diff Sig := ⟨STy.Bool, STy.Expr, (isZeroCtx, yVar, succX)⟩

/- ── 1. reconstruction crosses sorts ──────────────────────────────────────── -/
theorem fill_reconstructs : fill isZeroCtx succX = isZeroSuccX := by rfl

/- ── 2. the source-axis separation survives across sorts ──────────────────── -/
theorem source_axis_transfers : dirA ≠ dirB := by
  intro h
  cases h

/- ── a second, sort-internal heterogeneous family: not : Bool → Bool ───────── -/
def bVar : Term Sig STy.Bool := @Term.var Sig STy.Bool 0
def notB : Term Sig STy.Bool := .op Op.not (.cons bVar .nil)
def notCtx : Ctx Sig STy.Bool STy.Bool := .op Op.not (.here (@Ctx.hole Sig STy.Bool) .nil)

theorem fill_reconstructs_bool : fill notCtx bVar = notB := by rfl

/- The frozen representation handles both the sort-crossing (isZero : Expr → Bool) and the sort-internal
   (not : Bool → Bool) cases with no modification.  Recurred transfer across arity AND sort structure. -/

end MultiSortTransfer

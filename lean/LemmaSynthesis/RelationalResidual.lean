import Std

/-! # Relational residual — one-hole context reused LITERALLY (the object-side machinery)

  Target 9 (externally green) proved the flat quotient {depth, arity, sort, operator, position}
  still collapses context-distinct residuals.  The object side already discovered — and kernel-
  verified — that extensional values collapse structurally-different contexts and forced
  `Ctx`/`fill`/`compose`.  This file reuses that SAME machinery at the meta level: a residual is
  represented as `(Ctx, Filling)` — the distinguished diff position becomes the hole, `fill`
  reconstructs the term, `compose` captures nested structure.  Load-bearing, not analogical.
-/

namespace RelationalResidual

/- ── the frozen substrate (re-stated) ─────────────────────────────────────── -/
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

/- ── the one-hole context: a term of sort `s` with ONE hole of sort `t` ────── -/
mutual
  inductive Ctx (S : Signature) : S.Srt → S.Srt → Type where
    | hole (s : S.Srt) : Ctx S s s
    | op {s t : S.Srt} (o : S.Op s) : CtxArgs S t (S.arity o) → Ctx S s t
  inductive CtxArgs (S : Signature) : S.Srt → List S.Srt → Type where
    | here  {s : S.Srt} {ss : List S.Srt} {t : S.Srt} : Ctx S s t → Args S ss → CtxArgs S t (s :: ss)
    | there {s : S.Srt} {ss : List S.Srt} {t : S.Srt} : Term S s → CtxArgs S t ss → CtxArgs S t (s :: ss)
end

/- `fill`: substitute a term into the hole (reconstructs the term). -/
mutual
  def fill {S} {s t : S.Srt} : Ctx S s t → Term S t → Term S s
    | .hole _, x => x
    | .op o args, x => .op o (fillArgs args x)
  def fillArgs {S} {t : S.Srt} {ss : List S.Srt} : CtxArgs S t ss → Term S t → Args S ss
    | .here c rest, x => .cons (fill c x) rest
    | .there a rest, x => .cons a (fillArgs rest x)
end

/- `compose`: nest contexts. -/
mutual
  def compose {S} {s t u : S.Srt} : Ctx S s t → Ctx S t u → Ctx S s u
    | .hole _, d => d
    | .op o args, d => .op o (composeArgs args d)
  def composeArgs {S} {t u : S.Srt} {ss : List S.Srt} : CtxArgs S t ss → Ctx S t u → CtxArgs S u ss
    | .here c rest, d => .here (compose c d) rest
    | .there a rest, d => .there a (composeArgs rest d)
end

/- ── the laws (reused from the object side, now signature-generic) ─────────── -/
theorem fill_hole {S} {s : S.Srt} (x : Term S s) : fill (.hole s) x = x := by rfl

/- The composition law `fill (compose c d) x = fill c (fill d x)` is the object-side
   `ctx_role_composition` (already kernel-verified in DomainGenericKernel.lean); its signature-
   generic form is the same mutual induction ("contexts form a category").  `compose` above is the
   literal reuse of that structure; the law is not re-derived here. -/

/- ── the residual view: (Ctx, Filling) ────────────────────────────────────── -/
def ResidualView (S : Signature) : Type := Σ s t, Ctx S s t × Term S t

/- ── calibration on the Target-9 witness (single sort A, {a0, f, g}) ───────── -/
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

def fillingA : Term SigA ASrt.A := .op AOp.g (.cons xVar (.cons a0T .nil))   -- g x a0
def fillingB : Term SigA ASrt.A := .op AOp.f (.cons xVar (.cons a0T .nil))   -- f x a0

def invA : Term SigA ASrt.A := .op AOp.f (.cons fillingA (.cons yVar .nil))
def invB : Term SigA ASrt.A := .op AOp.f (.cons fillingB (.cons yVar .nil))

/- the SHARED one-hole context: f(□) y (the distinguished diff position is the hole). -/
def ctx : Ctx SigA ASrt.A ASrt.A := .op AOp.f (.here (@Ctx.hole SigA ASrt.A) (.cons yVar .nil))

/- THE LOAD-BEARING CALIBRATION: the residual view (ctx, filling) RECONSTRUCTS each term,
   and the FILLING is the discriminator the flat quotient erased. -/
theorem fill_ctx_fillingA : fill ctx fillingA = invA := by rfl
theorem fill_ctx_fillingB : fill ctx fillingB = invB := by rfl

theorem fillings_differ : fillingA ≠ fillingB := by
  intro h
  cases h

end RelationalResidual

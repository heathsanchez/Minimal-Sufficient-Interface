import Std

/-! # Constructor-language genesis — the residual forces a new constructor

  `ResidualSynthesis` let the residual *select and combine* supplied primitives, but the
  constructor substrate (`BExpr`) was still given in advance.  This file closes that loop:

      Gen_t → ρ_t → K(ρ_t) → prove Gen_t insufficient → ΔGen_t → Gen_{t+1}

  Micro-world: carrier `Car3 = Bool × Bool × Bool`; a *repair* is a single distinction
  `Car3 → Bool` (smallest codomain, made load-bearing).  The old generator `Gen_0` has only
  atoms — coordinate projections `a,b,c` and constants `t,f` — no combinators, so its closure
  is exactly those five functions.

  The residual family `R = {ρ0, ρ1}` collapses a pair differing in the second coordinate (ρ0)
  and one differing in the third (ρ1).  No single atom separates *both*: `b` sees only ρ0,
  `c` sees only ρ1.  Separating both with one Bool-valued distinction requires a *binary
  combination* of `b` and `c` — a constructor no atom can form.  The residual therefore forces
  the genesis of a binary constructor, synthesized by searching all 16 binary truth tables
  against the derived requirement, not named in advance.
-/

namespace CtorGenesis

structure Car3 where
  a : Bool
  b : Bool
  c : Bool
  deriving DecidableEq, Repr, Inhabited

def Residual := Car3 × Car3

def ρ0 : Residual := (⟨false, false, false⟩, ⟨false, true, false⟩)
def ρ1 : Residual := (⟨false, false, false⟩, ⟨false, false, true⟩)

/- K(R): the concrete constraint — a distinction must separate BOTH residual pairs. -/
abbrev SeparatesR (d : Car3 → Bool) : Prop :=
  d ρ0.1 ≠ d ρ0.2 ∧ d ρ1.1 ≠ d ρ1.2

/- ── Stage A: the old generator (atoms only) ───────────────────────────────── -/
inductive G0 where
  | a | b | c | t | f
  deriving Repr, DecidableEq, Inhabited

def eval0 : G0 → Car3 → Bool
  | .a, x => x.a
  | .b, x => x.b
  | .c, x => x.c
  | .t, _ => true
  | .f, _ => false

/- Completeness of the old generator closure: every G0 term is one of the five atoms. -/
theorem G0_complete : ∀ e : G0, e = .a ∨ e = .b ∨ e = .c ∨ e = .t ∨ e = .f := by
  intro e
  cases e <;> simp

/- Gen_0 is insufficient: no atom separates BOTH residuals.  This is the exhaustion of the
   old closure — a genuine expressibility failure, not a "tried 20 terms" heuristic. -/
theorem G0_insufficient : ∀ e : G0, ¬ SeparatesR (eval0 e) := by
  intro e
  cases e <;> native_decide

/- ── Stage B/C: residual-derived requirement → synthesized constructor ─────── -/
structure BinOp where
  ff : Bool
  ft : Bool
  tf : Bool
  tt : Bool
  deriving DecidableEq, Repr, Inhabited

def BinOp.apply (θ : BinOp) (x y : Bool) : Bool :=
  match (x, y) with
  | (false, false) => θ.ff
  | (false, true) => θ.ft
  | (true, false) => θ.tf
  | (true, true) => θ.tt

def allBools : List Bool := [false, true]

def allBinOps : List BinOp :=
  allBools.flatMap (fun ff =>
    allBools.flatMap (fun ft =>
      allBools.flatMap (fun tf =>
        allBools.map (fun tt => ⟨ff, ft, tf, tt⟩))))

/- The requirement read off the residual: a binary op θ used as `θ b c` separates R iff
   `θ f f ≠ θ t f` (ρ0) and `θ f f ≠ θ f t` (ρ1). -/
def binReq (θ : BinOp) : Bool :=
  (θ.apply false false != θ.apply true false) && (θ.apply false false != θ.apply false true)

/- The bridge: the residual-derived requirement is exactly the separation condition. -/
theorem binReq_iff_separates (θ : BinOp) :
    SeparatesR (fun x => θ.apply (x.b) (x.c)) ↔ binReq θ = true := by
  cases θ.ff <;> cases θ.ft <;> cases θ.tf <;> cases θ.tt <;>
    simp [SeparatesR, binReq, BinOp.apply, ρ0, ρ1]

/- Synthesize: all binary truth tables satisfying the requirement. -/
def synthBinCtor : List BinOp := allBinOps.filter binReq

def orOp : BinOp := ⟨false, true, true, true⟩

theorem synthBinCtor_nonempty : synthBinCtor ≠ [] := by native_decide
theorem orOp_in_synth : orOp ∈ synthBinCtor := by native_decide
theorem orOp_satisfies_req : binReq orOp = true := by native_decide

/- ── Stage D: the new generator restores generability ──────────────────────── -/
inductive G1 where
  | atom : G0 → G1
  | bin : BinOp → G1 → G1 → G1
  deriving Repr, DecidableEq, Inhabited

def eval1 : G1 → Car3 → Bool
  | .atom g, x => eval0 g x
  | .bin θ e₁ e₂, x => θ.apply (eval1 e₁ x) (eval1 e₂ x)

/- The synthesized constructor makes the repair generable. -/
theorem or_separates_both : SeparatesR (eval1 (.bin orOp (.atom .b) (.atom .c))) := by
  native_decide

/- ── Stage E: ablation and negative control ─────────────────────────────────── -/
/- Ablation: removing the `bin` constructor returns exactly `G0_insufficient`. -/

/- Negative control: a single residual (ρ0 alone) is already generable by atom `b` — no
   constructor genesis occurs when the old generator suffices. -/
theorem rho0_alone_generable : eval0 .b ρ0.1 ≠ eval0 .b ρ0.2 := by
  native_decide

/- The whole residual family provably forces a constructor outside Cl(Gen_0). -/
theorem genesis_necessary : ¬ ∃ e : G0, SeparatesR (eval0 e) := by
  intro h
  rcases h with ⟨e, he⟩
  exact G0_insufficient e he

/- ── Stronger test: a second, structurally different genesis event ─────────── -/
/- Two residuals whose shared point is `⟨f,t,t⟩` (not the origin): the requirement shifts
   to `θ t t ≠ θ f t ∧ θ t t ≠ θ t f`, forcing the *conjunctive* constructors instead. -/
def ρ3 : Residual := (⟨false, true, true⟩, ⟨false, false, true⟩)
def ρ4 : Residual := (⟨false, true, true⟩, ⟨false, true, false⟩)

abbrev SeparatesRB (d : Car3 → Bool) : Prop :=
  d ρ3.1 ≠ d ρ3.2 ∧ d ρ4.1 ≠ d ρ4.2

theorem G0_insufficient_B : ∀ e : G0, ¬ SeparatesRB (eval0 e) := by
  intro e
  cases e <;> native_decide

def binReqB (θ : BinOp) : Bool :=
  (θ.apply true true != θ.apply false true) && (θ.apply true true != θ.apply true false)

theorem binReqB_iff_separates (θ : BinOp) :
    SeparatesRB (fun x => θ.apply (x.b) (x.c)) ↔ binReqB θ = true := by
  cases θ.ff <;> cases θ.ft <;> cases θ.tf <;> cases θ.tt <;>
    simp [SeparatesRB, binReqB, BinOp.apply, ρ3, ρ4]

def synthBinCtorB : List BinOp := allBinOps.filter binReqB

def andOp : BinOp := ⟨false, false, false, true⟩

theorem andOp_in_synthB : andOp ∈ synthBinCtorB := by native_decide
theorem orOp_not_in_synthB : orOp ∉ synthBinCtorB := by native_decide
theorem andOp_not_in_synthA : andOp ∉ synthBinCtor := by native_decide

/- The same mechanism produces *different* constructor sets for different residuals:
   the first forces disjunctive constructors (or/xor/nor/xnor), the second forces
   conjunctive ones (and/nand/xor/xnor). -/
theorem synth_different : synthBinCtor ≠ synthBinCtorB := by
  intro h
  have : orOp ∈ synthBinCtorB := by simpa [h] using orOp_in_synth
  exact orOp_not_in_synthB this

/- Executable demonstration. -/
#eval synthBinCtor.length
#eval synthBinCtor
#eval synthBinCtorB

end CtorGenesis

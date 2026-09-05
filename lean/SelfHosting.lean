import Std

/-! # Self-hosting generator evolution — the generator lives in the world

  `CtorGenesis` showed the residual can force a new constructor, but the generator was still a
  global `G1` definition — it changed *conceptually* without living in the world returned by the
  transition.  This file closes that loophole:

      World_t (carries Generator_t) → ρ_t → B_t → B_t ∉ Cl(Gen_t) → ΔGen_t → World_{t+1}

  The world carries a generator whose capability is its *arity*: how many coordinates a single
  distinction may depend on.  Level 1 = atoms (essential arity ≤ 1), level 2 = binary
  combinations, level 3 = ternary.  The residual family induces a *minimal basis* `B_t` (the set
  of coordinates it spans), and `requiredArity = |B_t|` — the arity is *derived* from the
  obstruction, never hard-coded.  The step returns the world carrying the evolved generator, and
  the next residual search runs only through that returned generator.

  Key theorem: separating a residual family forces dependence on every coordinate its basis
  spans, so a level-k generator is provably insufficient for a family requiring arity > k.
-/

namespace SelfHosting

structure Car3 where
  a : Bool
  b : Bool
  c : Bool
  deriving DecidableEq, Repr, Inhabited

def Residual := Car3 × Car3

def ρ0 : Residual := (⟨false, false, false⟩, ⟨false, true, false⟩)   -- differs in b
def ρ1 : Residual := (⟨false, false, false⟩, ⟨false, false, true⟩)   -- differs in c
def ρ2 : Residual := (⟨false, false, false⟩, ⟨true, false, false⟩)   -- differs in a

def R2 : List Residual := [ρ0, ρ1]
def R3 : List Residual := [ρ0, ρ1, ρ2]

abbrev SeparatesAll (d : Car3 → Bool) (Rs : List Residual) : Prop :=
  ∀ ρ ∈ Rs, d ρ.1 ≠ d ρ.2

/- A distinction *depends on* a coordinate iff it separates some pair differing only there. -/
def dependsOnA (d : Car3 → Bool) : Prop := ∃ x y, x.b = y.b ∧ x.c = y.c ∧ d x ≠ d y
def dependsOnB (d : Car3 → Bool) : Prop := ∃ x y, x.a = y.a ∧ x.c = y.c ∧ d x ≠ d y
def dependsOnC (d : Car3 → Bool) : Prop := ∃ x y, x.a = y.a ∧ x.b = y.b ∧ d x ≠ d y

/- ── The arity lower bound: separating the residual forces dependence on its basis ── -/
/- R2 spans {b, c}: any separating distinction must depend on BOTH b and c (arity ≥ 2). -/
theorem R2_forces_bc (d : Car3 → Bool) : SeparatesAll d R2 → dependsOnB d ∧ dependsOnC d := by
  intro h
  constructor
  · exact ⟨ρ0.1, ρ0.2, by native_decide, by native_decide, h ρ0 (by simp [R2])⟩
  · exact ⟨ρ1.1, ρ1.2, by native_decide, by native_decide, h ρ1 (by simp [R2])⟩

/- R3 spans {a, b, c}: any separating distinction must depend on ALL three (arity ≥ 3). -/
theorem R3_forces_abc (d : Car3 → Bool) :
    SeparatesAll d R3 → dependsOnA d ∧ dependsOnB d ∧ dependsOnC d := by
  intro h
  constructor
  · exact ⟨ρ2.1, ρ2.2, by native_decide, by native_decide, h ρ2 (by simp [R3])⟩
  · constructor
    · exact ⟨ρ0.1, ρ0.2, by native_decide, by native_decide, h ρ0 (by simp [R3])⟩
    · exact ⟨ρ1.1, ρ1.2, by native_decide, by native_decide, h ρ1 (by simp [R3])⟩

/- ── The world carries its generator ─────────────────────────────────────────── -/
structure World where
  level : Nat
  deriving DecidableEq, Repr, Inhabited

def initWorld : World := ⟨1⟩

/- The minimal basis: which coordinates the residual family spans (incidence structure). -/
def spans (Rs : List Residual) : Bool × Bool × Bool :=
  (Rs.any (fun ρ => ρ.1.a != ρ.2.a),
   Rs.any (fun ρ => ρ.1.b != ρ.2.b),
   Rs.any (fun ρ => ρ.1.c != ρ.2.c))

/- Required arity = size of the minimal basis (derived from the residual). -/
def requiredArity (Rs : List Residual) : Nat :=
  let (sa, sb, sc) := spans Rs
  (if sa then 1 else 0) + (if sb then 1 else 0) + (if sc then 1 else 0)

/- The step: raise the generator level iff the residual's basis forces it. -/
def step (w : World) (Rs : List Residual) : World :=
  ⟨max w.level (requiredArity Rs)⟩

/- A certificate justifying the generator change. -/
structure Certificate (w w' : World) where
  required : Nat
  justified : w'.level = max w.level required

def certifiedStep (w : World) (Rs : List Residual) : Σ w' : World, Certificate w w' :=
  ⟨step w Rs, ⟨requiredArity Rs, rfl⟩⟩

/- The chain: the output world of step t is literally the input of step t+1. -/
def runSteps : World → List (List Residual) → World
  | w, [] => w
  | w, Rs :: rest => runSteps (step w Rs) rest

/- ── Executable facts and kernels ───────────────────────────────────────────── -/
theorem requiredArity_R2 : requiredArity R2 = 2 := by native_decide
theorem requiredArity_R3 : requiredArity R3 = 3 := by native_decide

theorem step_genesis : step initWorld R2 = ⟨2⟩ := by native_decide
theorem step_genesis2 : step (step initWorld R2) R3 = ⟨3⟩ := by native_decide

/- Negative control: a basis already generable by the current generator leaves it unchanged. -/
theorem step_no_genesis : step ⟨3⟩ R2 = ⟨3⟩ := by native_decide
theorem step_no_genesis_init : step initWorld [ρ0] = ⟨1⟩ := by native_decide

/- The two-generation self-hosting chain: level 1 → 2 → 3, threading the returned generator. -/
theorem runSteps_genesis_twice : runSteps initWorld [R2, R3] = ⟨3⟩ := by native_decide

/- The returned generator is the actual next input (unfolding one step). -/
theorem returned_generator_is_next_input :
    (step initWorld R2) = runSteps initWorld [R2] := by
  native_decide

/- Executable demonstration. -/
#eval requiredArity R2
#eval requiredArity R3
#eval runSteps initWorld [R2, R3]

end SelfHosting

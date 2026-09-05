import Std

/-! # Residual-derived representation synthesis

  `SelfContainedWorld` removed the external level schedule, but the repair vocabulary still
  contained a hand-written operation: `split`.  The constructor was *selected*, but its
  semantics were supplied beforehand.

  This file makes the repair SHAPE arise from the residual.  The pipeline is

      ρ  →  K(ρ)  →  V(ρ)  →  Δ_ρ  →  verify(Δ_ρ)  →  minimal(Δ_ρ)  →  G'

  - The micro-world: carrier `Car3 = Bool × Bool × Bool`; the ontology observes only the
    first coordinate (`observe x = x.a`).
  - A residual is a pair the ontology collapses but whose coordinates genuinely differ.
  - K(ρ): (1) separate the collapsed pair; (2) preserve every old distinction (refinement).
  - V(ρ): candidate repairs are nonempty lists of boolean-expression *distinctions*; a repair's
    observation is the tuple of their evaluations.
  - Synthesis enumerates the version space, filters by K, and returns the minimal-cost
    survivors (cost is lexicographic: fewest distinctions = smallest codomain, then smallest
    term size).
  - The primitive `split` does not appear: the needed distinction (the missing coordinate) is
    *derived* from K(ρ) and proved minimal.
-/

namespace ResidualSynthesis

structure Car3 where
  a : Bool
  b : Bool
  c : Bool
  deriving DecidableEq, Repr, Inhabited

def observe (x : Car3) : Bool := x.a

def Residual := Car3 × Car3

abbrev IsResidual (ρ : Residual) : Prop := observe ρ.1 = observe ρ.2 ∧ ρ.1 ≠ ρ.2

/- Two residuals: both collapsed by `observe` (= first coordinate), but one differs in the
   second coordinate and the other in the third. -/
def ρ0 : Residual := (⟨false, false, false⟩, ⟨false, true, false⟩)
def ρ1 : Residual := (⟨false, false, false⟩, ⟨false, false, true⟩)

/- The distinction grammar: boolean expressions over the three coordinates. -/
inductive BExpr where
  | a | b | c | t | f
  | not : BExpr → BExpr
  | and : BExpr → BExpr → BExpr
  | or : BExpr → BExpr → BExpr
  deriving Repr, DecidableEq, Inhabited

def eval : BExpr → Car3 → Bool
  | .a, x => x.a
  | .b, x => x.b
  | .c, x => x.c
  | .t, _ => true
  | .f, _ => false
  | .not e, x => !(eval e x)
  | .and e₁ e₂, x => eval e₁ x && eval e₂ x
  | .or e₁ e₂, x => eval e₁ x || eval e₂ x

/- A repair is a list of distinctions; the new observation is their tuple. -/
def observeWith (r : List BExpr) (x : Car3) : List Bool := r.map (fun d => eval d x)

/- K(ρ): separate the collapsed pair AND preserve every old distinction. -/
abbrev Separates (r : List BExpr) (ρ : Residual) : Prop :=
  observeWith r ρ.1 ≠ observeWith r ρ.2

def Preserves (r : List BExpr) : Prop :=
  ∀ x y : Car3, x.a ≠ y.a → observeWith r x ≠ observeWith r y

def SatisfiesK (r : List BExpr) (ρ : Residual) : Prop := Separates r ρ ∧ Preserves r

/- The finite carrier and executable (Bool-valued) constraint checks. -/
def allCar3 : List Car3 :=
  [⟨false,false,false⟩, ⟨false,false,true⟩, ⟨false,true,false⟩, ⟨false,true,true⟩,
   ⟨true,false,false⟩, ⟨true,false,true⟩, ⟨true,true,false⟩, ⟨true,true,true⟩]

def separatesB (r : List BExpr) (ρ : Residual) : Bool := observeWith r ρ.1 != observeWith r ρ.2

def preservesB (r : List BExpr) : Bool :=
  allCar3.all (fun x => allCar3.all (fun y => !((x.a != y.a) && (observeWith r x == observeWith r y))))

def satisfiesKB (r : List BExpr) (ρ : Residual) : Bool := separatesB r ρ && preservesB r

/- The version space of candidate distinctions (projections, constants, and a few composites
   for the wrong-repair controls). -/
def candidateDists : List BExpr := [.a, .b, .c, .t, .f, .not .b, .not .c, .and .b .c, .or .b .c]

def sublists : List α → List (List α)
  | [] => [[]]
  | x :: xs =>
      let rest := sublists xs
      rest ++ rest.map (fun s => x :: s)

def candidateRepairs : List (List BExpr) :=
  (sublists candidateDists).filter (fun r => 1 ≤ r.length && r.length ≤ 3)

/- Structural cost: fewest distinctions first (smallest codomain), then smallest total term
   size (least refinement among equal-codomain repairs). -/
def termSize : BExpr → Nat
  | .a => 1 | .b => 1 | .c => 1 | .t => 1 | .f => 1
  | .not e => 1 + termSize e
  | .and e₁ e₂ => 1 + termSize e₁ + termSize e₂
  | .or e₁ e₂ => 1 + termSize e₁ + termSize e₂

def cost (r : List BExpr) : Nat :=
  r.length * 1000 + r.foldl (fun s d => s + termSize d) 0

def listMin (l : List Nat) : Nat := l.foldl Nat.min 9999

/- Synthesize: the minimal-cost repairs (version space) satisfying K(ρ). -/
def synthesize (ρ : Residual) : List (List BExpr) :=
  let valid := candidateRepairs.filter (fun r => satisfiesKB r ρ)
  let m := listMin (valid.map cost)
  valid.filter (fun r => cost r = m)

def satisfiesAllB (r : List BExpr) (ρs : List Residual) : Bool :=
  ρs.all (fun ρ => satisfiesKB r ρ)

def synthesizeAll (ρs : List Residual) : List (List BExpr) :=
  let valid := candidateRepairs.filter (fun r => satisfiesAllB r ρs)
  let m := listMin (valid.map cost)
  valid.filter (fun r => cost r = m)

/- ── Kernels ───────────────────────────────────────────────────────────────── -/

theorem rho0_is_residual : IsResidual ρ0 := by
  constructor
  · rfl
  · intro h; cases h

theorem rho1_is_residual : IsResidual ρ1 := by
  constructor
  · rfl
  · intro h; cases h

/- The old observation alone (`[.a]`) does not separate ρ0. -/
theorem keep_fails : ¬ SatisfiesK [.a] ρ0 := by
  intro h
  rcases h with ⟨hsep, _⟩
  exact hsep rfl

/- The empty repair separates nothing. -/
theorem empty_fails : ¬ SatisfiesK [] ρ0 := by
  intro h
  rcases h with ⟨hsep, _⟩
  exact hsep rfl

/- THE KEY DERIVED CONSTRAINT: no single distinction can both preserve the first coordinate
   and separate the collapsed pair.  A single Bool-valued distinction has only two values,
   and preserving a two-way split already exhausts them. -/
theorem no_single_distinction (d : BExpr) : ¬ SatisfiesK [d] ρ0 := by
  intro hsat
  rcases hsat with ⟨hsep, hpres⟩
  let u : Car3 := ⟨false, false, false⟩
  let v : Car3 := ⟨false, true, false⟩
  let w : Car3 := ⟨true, false, false⟩
  have huw : eval d u ≠ eval d w := by
    have : u.a ≠ w.a := by native_decide
    simpa [observeWith] using (hpres u w this)
  have hvw : eval d v ≠ eval d w := by
    have : v.a ≠ w.a := by native_decide
    simpa [observeWith] using (hpres v w this)
  have huv : eval d u = eval d v := by
    cases hw : eval d w <;> cases hu : eval d u <;> cases hv : eval d v <;> simp_all
  have hsep' : eval d u ≠ eval d v := by
    intro heq
    have hlist : observeWith [d] ρ0.1 = observeWith [d] ρ0.2 := by
      simp [observeWith, ρ0, u, v, heq]
    exact hsep hlist
  exact hsep' huv

/- Minimality: any valid repair has at least two distinctions (a codomain of ≥ 4 values). -/
theorem minimal_cost_is_two : ∀ r : List BExpr, SatisfiesK r ρ0 → 2 ≤ r.length := by
  intro r h
  cases r with
  | nil => exfalso; exact empty_fails h
  | cons d rest =>
      cases rest with
      | nil => exfalso; exact no_single_distinction d h
      | cons _ _ => simp

/- The synthesized repair `[.a, .b]` satisfies K(ρ0). -/
theorem preserves_ab : Preserves [.a, .b] := by
  intro x y hxy hlist
  injection hlist with hx hb
  exact hxy hx

theorem synth_ab_satisfies : SatisfiesK [.a, .b] ρ0 := by
  constructor
  · native_decide
  · exact preserves_ab

/- Reconstruction of `split`: the synthesized observation is exactly the old coordinate plus
   the missing coordinate — the split operation is *discovered*, not supplied. -/
theorem synth_reconstructs_split (x : Car3) : observeWith [.a, .b] x = [x.a, x.b] := by
  rfl

/- The same machinery, given the other residual, produces a *different* repair. -/
theorem preserves_ac : Preserves [.a, .c] := by
  intro x y hxy hlist
  injection hlist with hx hc
  exact hxy hx

theorem synth_ac_satisfies : SatisfiesK [.a, .c] ρ1 := by
  constructor
  · native_decide
  · exact preserves_ac

/- Wrong-repair controls: these candidates are rejected for principled reasons. -/
theorem reject_b_alone : ¬ SatisfiesK [.b] ρ0 := by
  intro h
  exact no_single_distinction .b h

theorem reject_const : ¬ SatisfiesK [.t] ρ0 := by
  intro h
  rcases h with ⟨hsep, _⟩
  exact hsep rfl

theorem reject_composite : ¬ SatisfiesK [.or .b .c] ρ0 := by
  intro h
  rcases h with ⟨hsep, hpres⟩
  have this : observeWith [.or .b .c] (⟨false,false,false⟩ : Car3)
              = observeWith [.or .b .c] (⟨true,false,false⟩ : Car3) := by
    native_decide
  have hne : (⟨false,false,false⟩ : Car3).a ≠ (⟨true,false,false⟩ : Car3).a := by native_decide
  exact (hpres (⟨false,false,false⟩ : Car3) (⟨true,false,false⟩ : Car3) hne) this

/- The executable synthesis: exact results and the JOIN finding. -/
theorem synth_rho0_exact : synthesize ρ0 = [[.a, .b]] := by native_decide
theorem synth_rho1_exact : synthesize ρ1 = [[.a, .c]] := by native_decide
theorem synth_diff : synthesize ρ0 ≠ synthesize ρ1 := by native_decide
theorem synth_join_exact : synthesizeAll [ρ0, ρ1] = [[.a, .or .b .c]] := by native_decide

/- The executable synthesis discovers the missing-coordinate repairs. -/
#eval synthesize ρ0
#eval synthesize ρ1
#eval synthesizeAll [ρ0, ρ1]

end ResidualSynthesis

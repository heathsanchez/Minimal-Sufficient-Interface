import Std
import ResidualDerivedConstructorPrinciple

universe u v w z

namespace ResidualCompiledSyntaxGenesis

open ResidualInterfaceGenesis
open ResidualDerivedMetaLanguageGenesis
open ResidualDerivedConstructorPrinciple

variable {X : Type u} {Probe : Type v} {V : Type w} {Y : Type z}

/-- A fixed universal substrate with no pre-enumerated arity constructors.
    Arbitrary finite interface shapes are represented recursively. -/
inductive InterfaceSyntax (Probe : Type v) where
  | unit
  | atom (p : Probe)
  | join (head : Probe) (tail : InterfaceSyntax Probe)
  deriving DecidableEq

namespace InterfaceSyntax

/-- Compile a residual-selected basis into syntax.  The arity is determined by
    the basis itself; unary/binary/ternary/... constructors are not enumerated. -/
def compile : List Probe → InterfaceSyntax Probe
  | [] => .unit
  | p :: ps => .join p (compile ps)

/-- Number of primitive observation coordinates represented by the syntax. -/
def arity : InterfaceSyntax Probe → Nat
  | .unit => 0
  | .atom _ => 1
  | .join _ t => 1 + arity t

@[simp] theorem arity_compile (B : List Probe) :
    arity (compile B) = B.length := by
  induction B with
  | nil => rfl
  | cons p ps ih =>
      simp [compile, arity, ih, Nat.add_comm]

/-- Extensional semantics of generated interface syntax: two states have the
    same generated joint view exactly when every represented probe agrees. -/
def SameView
    (observe : Probe → X → V) : InterfaceSyntax Probe → X → X → Prop
  | .unit, _, _ => True
  | .atom p, x, y => observe p x = observe p y
  | .join p t, x, y => observe p x = observe p y ∧ SameView observe t x y

/-- The recursive compiler is semantically exact: compiling a basis introduces
    neither missing nor extra distinctions relative to that selected basis. -/
theorem sameView_compile_iff
    (observe : Probe → X → V)
    (B : List Probe)
    (x y : X) :
    SameView observe (compile B) x y ↔
      ∀ p, p ∈ B → observe p x = observe p y := by
  induction B with
  | nil =>
      simp [compile, SameView]
  | cons p ps ih =>
      simp [compile, SameView, ih]

end InterfaceSyntax

/-- A generated syntax term is sufficient when equality of its represented view
    forces equality of the protected consequence. -/
def SyntaxSufficient
    (observe : Probe → X → V)
    (target : X → Y)
    (s : InterfaceSyntax Probe) : Prop :=
  ∀ x y, InterfaceSyntax.SameView observe s x y → target x = target y

/-- Residual evidence compiles directly into a sufficient recursive syntax term. -/
theorem residuals_compile_sufficient_syntax
    (observe : Probe → X → V)
    (target : X → Y)
    (B : List Probe)
    (h : ResidualDeterminesArity observe target B) :
    SyntaxSufficient observe target (InterfaceSyntax.compile B) := by
  intro x y hsame
  apply h.1 x y
  exact (InterfaceSyntax.sameView_compile_iff observe B x y).mp hsame

/-- Every strictly smaller compiled syntax is residually impossible. -/
theorem every_smaller_compiled_syntax_is_obstructed
    (observe : Probe → X → V)
    (target : X → Y)
    (B : List Probe)
    (h : ResidualDeterminesArity observe target B) :
    ∀ B' : List Probe, B'.length < B.length →
      ¬ SyntaxSufficient observe target (InterfaceSyntax.compile B') := by
  intro B' hlen hs
  rcases h.2 B' hlen with ⟨x, y, hsame, hneq⟩
  have hsyntax : InterfaceSyntax.SameView observe (InterfaceSyntax.compile B') x y :=
    (InterfaceSyntax.sameView_compile_iff observe B' x y).mpr hsame
  exact hneq (hs x y hsyntax)

/-- An old finite syntax family is exhausted when none of its represented
    interfaces is sufficient for the protected consequence. -/
def SyntaxFamilyExhausted
    (old : List (InterfaceSyntax Probe))
    (observe : Probe → X → V)
    (target : X → Y) : Prop :=
  ∀ s, s ∈ old → ¬ SyntaxSufficient observe target s

/-- Crucial strict-genesis theorem: once residuals determine a sufficient basis,
    its compiled recursive syntax is automatically outside every exhausted old
    finite syntax family.  `newSyntax ∉ old` is derived, not assumed. -/
theorem residual_compiled_syntax_escapes_exhausted_family
    (old : List (InterfaceSyntax Probe))
    (observe : Probe → X → V)
    (target : X → Y)
    (B : List Probe)
    (hexh : SyntaxFamilyExhausted old observe target)
    (h : ResidualDeterminesArity observe target B) :
    InterfaceSyntax.compile B ∉ old := by
  intro hin
  exact (hexh (InterfaceSyntax.compile B) hin)
    (residuals_compile_sufficient_syntax observe target B h)

/-- End-to-end relative syntax-genesis certificate: old finite syntax is globally
    exhausted, residuals determine the minimal dependency arity, the recursive
    compiler creates a sufficient syntax term, and that term is provably novel
    relative to the old family. -/
def ResidualCompiledSyntaxGenesis
    (old : List (InterfaceSyntax Probe))
    (observe : Probe → X → V)
    (target : X → Y)
    (B : List Probe) : Prop :=
  SyntaxFamilyExhausted old observe target ∧
  ResidualDeterminesArity observe target B

/-- The certificate yields strict syntax gain and exact minimal-arity necessity. -/
theorem residual_compiled_syntax_genesis_gate
    (old : List (InterfaceSyntax Probe))
    (observe : Probe → X → V)
    (target : X → Y)
    (B : List Probe)
    (h : ResidualCompiledSyntaxGenesis old observe target B) :
    SyntaxSufficient observe target (InterfaceSyntax.compile B) ∧
    InterfaceSyntax.compile B ∉ old ∧
    InterfaceSyntax.arity (InterfaceSyntax.compile B) = B.length ∧
    ∀ B' : List Probe, B'.length < B.length →
      ¬ SyntaxSufficient observe target (InterfaceSyntax.compile B') := by
  refine ⟨residuals_compile_sufficient_syntax observe target B h.2, ?_, ?_, ?_⟩
  · exact residual_compiled_syntax_escapes_exhausted_family old observe target B h.1 h.2
  · exact InterfaceSyntax.arity_compile B
  · exact every_smaller_compiled_syntax_is_obstructed observe target B h.2

/-- Exact ancestral ablation: replacing the generated term by any compiled term
    of smaller residual-selected arity restores a protected obstruction. -/
theorem syntax_ablation_restores_verified_residual
    (observe : Probe → X → V)
    (target : X → Y)
    (B B' : List Probe)
    (h : ResidualDeterminesArity observe target B)
    (hlen : B'.length < B.length) :
    ∃ x y,
      InterfaceSyntax.SameView observe (InterfaceSyntax.compile B') x y ∧
      target x ≠ target y := by
  rcases h.2 B' hlen with ⟨x, y, hsame, hneq⟩
  exact ⟨x, y, (InterfaceSyntax.sameView_compile_iff observe B' x y).mpr hsame, hneq⟩

/-- Scientific boundary: syntax is now generated rather than selected from a
    finite arity menu, but computation still requires a fixed universal recursive
    substrate (`unit/join/atom`).  Ex-nihilo invention outside every possible
    metalanguage is not a coherent executable requirement. -/
def UniversalRecursiveSubstrateAssumed : Prop := True

theorem universal_substrate_boundary_explicit : UniversalRecursiveSubstrateAssumed := by
  trivial

end ResidualCompiledSyntaxGenesis

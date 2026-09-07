import Std

/-! Bounded construction from declared raw primitives. No unrestricted genesis claim. -/
namespace ConstructorRealization

inductive V where | x | y deriving DecidableEq, Repr

def select : V → Nat × Nat → Nat
  | .x, p => p.1
  | .y, p => p.2

inductive NTerm where
  | arg : V → NTerm
  | zero : NTerm
  | succ : NTerm → NTerm
  deriving DecidableEq, Repr

inductive BTerm where
  | eq : NTerm → NTerm → BTerm
  | lt : NTerm → NTerm → BTerm
  | neg : BTerm → BTerm
  | conj : BTerm → BTerm → BTerm
  deriving DecidableEq, Repr

def evalN : NTerm → Nat × Nat → Nat
  | .arg v, p => select v p
  | .zero, _ => 0
  | .succ e, p => evalN e p + 1

def evalB : BTerm → Nat × Nat → Bool
  | .eq a b, p => decide (evalN a p = evalN b p)
  | .lt a b, p => decide (evalN a p < evalN b p)
  | .neg e, p => !evalB e p
  | .conj a b, p => evalB a p && evalB b p

def separates (e : BTerm) : Bool :=
  evalB e (0, 1) && !evalB e (1, 0)

/- Build atoms from variables and primitive equality/order, not named relations. -/
def variables : List NTerm := [.arg .x, .arg .y]
def atoms : List BTerm :=
  variables.flatMap fun a =>
    variables.flatMap fun b => [.eq a b, .lt a b]

def compile : Option BTerm := atoms.find? separates

theorem compile_result :
    compile = some (.lt (.arg .x) (.arg .y)) := by native_decide

theorem compile_separates :
    separates (.lt (.arg .x) (.arg .y)) = true := by native_decide

def sizeN : NTerm → Nat
  | .arg _ => 1
  | .zero => 1
  | .succ e => 1 + sizeN e

def sizeB : BTerm → Nat
  | .eq a b => 1 + sizeN a + sizeN b
  | .lt a b => 1 + sizeN a + sizeN b
  | .neg e => 1 + sizeB e
  | .conj a b => 1 + sizeB a + sizeB b

private theorem sizeN_positive (e : NTerm) : 1 ≤ sizeN e := by
  induction e with
  | arg _ => simp [sizeN]
  | zero => simp [sizeN]
  | succ e ih => simp [sizeN] <;> omega

theorem sizeB_lower_bound (e : BTerm) : 3 ≤ sizeB e := by
  induction e with
  | eq a b =>
      have ha := sizeN_positive a
      have hb := sizeN_positive b
      simp [sizeB] <;> omega
  | lt a b =>
      have ha := sizeN_positive a
      have hb := sizeN_positive b
      simp [sizeB] <;> omega
  | neg e ih => simp [sizeB] <;> omega
  | conj a b ih1 ih2 => simp [sizeB] <;> omega

theorem generated_is_minimal :
    ∀ e : BTerm, separates e = true →
      sizeB (.lt (.arg .x) (.arg .y)) ≤ sizeB e := by
  intro e _
  simpa [sizeB, sizeN] using sizeB_lower_bound e

/- The residual does not uniquely determine the semantic realization. -/
def alternative : BTerm := .neg (.lt (.arg .y) (.arg .x))

theorem ambiguity :
    separates alternative = true ∧
    evalB alternative (2, 2) ≠ evalB (.lt (.arg .x) (.arg .y)) (2, 2) := by
  native_decide

theorem heldout_transfer :
    evalB (.lt (.arg .x) (.arg .y)) (2, 3) = true ∧
    evalB (.lt (.arg .x) (.arg .y)) (3, 2) = false := by
  native_decide

theorem ablation_loses_distinction :
    evalB (.eq (.arg .x) (.arg .y)) (2, 3) =
    evalB (.eq (.arg .x) (.arg .y)) (3, 2) := by
  native_decide

/- Exact order-free grammar: variable equality and Boolean connectives only.
   No constants, order, position tests, or arbitrary asymmetric predicates. -/
inductive SymTerm where
  | eq : V → V → SymTerm
  | neg : SymTerm → SymTerm
  | conj : SymTerm → SymTerm → SymTerm
  deriving DecidableEq, Repr

def evalSym : SymTerm → Nat × Nat → Bool
  | .eq i j, p => decide (select i p = select j p)
  | .neg e, p => !evalSym e p
  | .conj a b, p => evalSym a p && evalSym b p

theorem symmetric (e : SymTerm) (a b : Nat) :
    evalSym e (a, b) = evalSym e (b, a) := by
  induction e with
  | eq i j =>
      cases i <;> cases j <;> simp [evalSym, select, eq_comm]
  | neg e ih => simp [evalSym, ih]
  | conj a b ih1 ih2 => simp [evalSym, ih1, ih2]

theorem no_order_free_separator (e : SymTerm) :
    ¬ (evalSym e (0, 1) = true ∧ evalSym e (1, 0) = false) := by
  intro h
  have hs := symmetric e 0 1
  rw [h.1, h.2] at hs
  cases hs

end ConstructorRealization

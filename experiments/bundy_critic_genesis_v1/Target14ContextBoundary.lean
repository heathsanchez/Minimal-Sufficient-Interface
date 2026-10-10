import Std
import LemmaSynthesis.Target13Result
import ConstitutionalFailedFactorization

/-!
  Falsification of an overly broad reading of Target13's syntactic fixed point.
  Two proof situations have identical directed (Ctx,Source,Target) residuals,
  but different admitted hypothesis contexts and hence different provability.
  This DOES NOT refute Target13's actual claim within its syntactic tested seams.

  The proof checker here uses finite Boolean models as a counterexample authority.
  The positive case is separately demonstrated by a genuine Lean proof term.
-/
namespace BundyCriticGenesis

inductive Atom where | a | b | c
  deriving DecidableEq, Repr, Inhabited

abbrev Fact := Atom × Atom

structure Valuation where
  a : Bool
  b : Bool
  c : Bool
  deriving DecidableEq, Repr

def value (v : Valuation) : Atom → Bool
  | .a => v.a
  | .b => v.b
  | .c => v.c

def allValuations : List Valuation :=
  [⟨false,false,false⟩, ⟨false,false,true⟩,
   ⟨false,true,false⟩, ⟨false,true,true⟩,
   ⟨true,false,false⟩, ⟨true,false,true⟩,
   ⟨true,true,false⟩, ⟨true,true,true⟩]

def contextTrue (v : Valuation) (facts : List Fact) : Bool :=
  facts.all (fun f => value v f.1 == value v f.2)

def entailsAC (facts : List Fact) : Bool :=
  allValuations.all (fun v => !(contextTrue v facts) ||
    value v Atom.a == value v Atom.c)

structure ProofSituation where
  directed : Target13.Residual Target13.SigA
  assumptions : List Fact

def positive : ProofSituation :=
  ⟨Target13.indFlat, [(Atom.a, Atom.b), (Atom.b, Atom.c)]⟩

def negative : ProofSituation :=
  ⟨Target13.indFlat, [(Atom.a, Atom.b)]⟩

def oldResidual (p : ProofSituation) : Target13.Residual Target13.SigA :=
  p.directed

def protectedFuture (p : ProofSituation) : Bool := entailsAC p.assumptions

theorem old_directed_residual_collapses :
    oldResidual positive = oldResidual negative := rfl

theorem future_distinguishes :
    protectedFuture positive = true ∧ protectedFuture negative = false := by
  native_decide

/- The direct application of the existing MSI failed-factorization theorem. -/
theorem no_context_blind_critic_can_predict_future :
    ¬ ∃ critic : Target13.Residual Target13.SigA → Bool,
       ∀ p : ProofSituation, protectedFuture p = critic (oldResidual p) :=
  ConstitutionalFailedFactorization.failed_factorization
    oldResidual protectedFuture
    old_directed_residual_collapses
    (by native_decide)

/- One added, independently inspectable support distinction is enough for this pair. -/
def supportFeature (p : ProofSituation) : Bool :=
  decide ((Atom.b, Atom.c) ∈ p.assumptions)

def repairedView (p : ProofSituation) :
    Target13.Residual Target13.SigA × Bool :=
  (oldResidual p, supportFeature p)

theorem support_feature_separates :
    repairedView positive ≠ repairedView negative := by
  intro h
  have hSupport : supportFeature positive = supportFeature negative :=
    congrArg Prod.snd h
  have : supportFeature positive ≠ supportFeature negative := by
    native_decide
  exact this hSupport

/- Real proof obligations, not an untrusted classifier. -/
theorem proof_under_admitted_context (α : Type) (a b c : α)
    (h₀ : a = b) (h₁ : b = c) : a = c :=
  Eq.trans h₀ h₁

theorem no_proof_from_one_hypothesis_uniformly :
    ¬ (∀ a b c : Bool, a = b → a = c) := by
  intro h
  have impossible : false = true := h false false true rfl
  cases impossible

/- Scope caution: this is a CONTEXT counterexample; no claim of an
   autonomous proof-critic inventor or a globally inadequate proof language. -/

end BundyCriticGenesis

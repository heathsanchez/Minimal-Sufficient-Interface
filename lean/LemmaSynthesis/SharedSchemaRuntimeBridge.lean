import Std
import LemmaSynthesis.EndToEnd
import LemmaSynthesis.SearchPolicy
import LemmaSynthesis.DerivedSearchConstraint
import GeneratedStage
import LemmaSynthesis.SynthesisCore

/-!
# Shared developmental implementation with runtime policy attachment

This experiment does not change the established theorem files. It instantiates
`SynthesisCore.develop` twice: once for the established object residual and once
for the already-derived Target-4 policy residual. The latter discovers the
policy collapse, selects a policy program, and replays adequacy through the same
single implementation. The exact selected program is then adjoined to an actual
developmental stage and transferred to the held-out Target-5 residual. The
resulting developer's policy is consumed directly by `SearchPolicyAsState.search`.

The policy-program family is supplied by the meta-language. This proves
selection and retained installation inside that family, not grammar genesis.
-/

namespace SharedSchemaRuntimeBridge

open SearchPolicyAsState
open DerivedSearchConstraint
open DevelopmentalCategory
open GeneratedStage

/-! ## Object-level instantiation of the shared implementation -/

def objectCandidates : List
    (SynthesisCore.Candidate
      (EndToEnd.Term EndToEnd.SigA EndToEnd.ASrt.A)
      EndToEnd.DiscVal EndToEnd.DiscTag) :=
  [ ⟨.arity, 0, fun t => .nat (EndToEnd.arity t)⟩
  , ⟨.head, 1, fun t => .head (EndToEnd.headOf t)⟩
  , ⟨.left, 2, fun t => .term (EndToEnd.leftChild t)⟩
  , ⟨.full, 3, fun t => .term t⟩ ]

def objectDisc (tag : EndToEnd.DiscTag)
    (term : EndToEnd.Term EndToEnd.SigA EndToEnd.ASrt.A) : EndToEnd.DiscVal :=
  match tag with
  | .arity => .nat (EndToEnd.arity term)
  | .head => .head (EndToEnd.headOf term)
  | .left => .term (EndToEnd.leftChild term)
  | .full => .term term

def objectRepairQuotient (tag : EndToEnd.DiscTag)
    (term : EndToEnd.Term EndToEnd.SigA EndToEnd.ASrt.A) :
    Nat × EndToEnd.DiscVal :=
  (EndToEnd.Q0 term, objectDisc tag term)

def objectDevelopment : Option
    (SynthesisCore.DevelopmentOutcome
      (EndToEnd.Term EndToEnd.SigA EndToEnd.ASrt.A) EndToEnd.DiscTag) :=
  SynthesisCore.develop EndToEnd.univ EndToEnd.Q0 EndToEnd.FB
    objectCandidates objectRepairQuotient

theorem object_instance_selects_head :
    objectDevelopment.map (fun outcome => outcome.selected) =
      some EndToEnd.DiscTag.head := by
  native_decide

theorem object_instance_matches_established_result :
    objectDevelopment.map (fun outcome => outcome.selected) =
      EndToEnd.synthesize EndToEnd.fxa EndToEnd.gxa := by
  native_decide

theorem object_selected_repair_causes_adequate_replay :
    objectDevelopment.map (fun outcome => outcome.replayResiduals) = some [] := by
  native_decide

/-! ## Held-out Target 5 in the existing search implementation -/

inductive HSort where | Nat deriving DecidableEq, Repr, Inhabited
inductive HOp where | one | mul | pow | powAcc deriving DecidableEq, Repr, Inhabited

def HOpFam : HSort → Type := fun _ => HOp

def HOpDecEq (s : HSort) : DecidableEq (HOpFam s) := by
  unfold HOpFam
  infer_instance

def HArity : {s : HSort} → HOpFam s → List HSort
  | .Nat, .one => []
  | .Nat, .mul => [.Nat, .Nat]
  | .Nat, .pow => [.Nat, .Nat]
  | .Nat, .powAcc => [.Nat, .Nat, .Nat]

def SigPow : Signature :=
  ⟨HSort, HOpFam, HArity, inferInstance, HOpDecEq⟩

def powOps : (s : HSort) → List (HOpFam s) :=
  fun _ => [.one, .mul, .pow, .powAcc]

def bVar : Term SigPow HSort.Nat := @Term.var SigPow HSort.Nat 0

def eVar : Term SigPow HSort.Nat := @Term.var SigPow HSort.Nat 1

def accVar : Term SigPow HSort.Nat := @Term.var SigPow HSort.Nat 2

def heldOutInvariant : Term SigPow HSort.Nat :=
  .op HOp.mul
    (.cons (.op HOp.pow (.cons bVar (.cons eVar .nil)))
      (.cons accVar .nil))

/-- Both held-out policy fields are compiled from the held-out term. -/
def heldOutK : SearchConstraint := deriveConstraint heldOutInvariant

theorem held_out_constraint_is_structural :
    heldOutK = ⟨2, 2⟩ := by
  native_decide

/-! ## Meta-level instantiation of the same `develop` implementation -/

inductive PolicyProgram where
  | keepBaseline
  | deriveFromResidual
  deriving DecidableEq, Repr, Inhabited

/-- Executable semantics of the supplied policy-program language. -/
def interpretPolicyProgram (program : PolicyProgram) (k : SearchConstraint) : SearchPolicy :=
  match program with
  | .keepBaseline => baselineSearch
  | .deriveFromResidual =>
      { depthBound := k.requiredDepth, arityCap := k.safeArity, budget := 0 }

/-- Target-4 calibration probe: preserve the derived arity bound while retaining
old baseline depth. Selection is completed here, before Target 5 is applied. -/
def calibrationProbe : SearchConstraint :=
  { requiredDepth := baselineSearch.depthBound,
    safeArity := derivedKMeta4.safeArity }

def policyCandidates : List
    (SynthesisCore.Candidate SearchConstraint SearchPolicy PolicyProgram) :=
  [ ⟨.keepBaseline, 0, interpretPolicyProgram .keepBaseline⟩
  , ⟨.deriveFromResidual, 1, interpretPolicyProgram .deriveFromResidual⟩ ]

def policyUniv : List SearchConstraint := [calibrationProbe, derivedKMeta4]

def policyQ0 (_ : SearchConstraint) : Bool := false

def policyFB (k : SearchConstraint) : SearchConstraint := k

def policyRepairQuotient (program : PolicyProgram) (k : SearchConstraint) :
    Bool × SearchPolicy :=
  (policyQ0 k, interpretPolicyProgram program k)

def metaDevelopment : Option
    (SynthesisCore.DevelopmentOutcome SearchConstraint PolicyProgram) :=
  SynthesisCore.develop policyUniv policyQ0 policyFB
    policyCandidates policyRepairQuotient

def selectedProgram? : Option PolicyProgram :=
  SynthesisCore.promoteIfReplayAdequate
    policyUniv policyFB policyRepairQuotient metaDevelopment

def selectedProgram : PolicyProgram :=
  match selectedProgram? with
  | some program => program
  | none => .keepBaseline

theorem meta_instance_discovers_policy_residual :
    metaDevelopment.map (fun outcome => outcome.residual) =
      some (calibrationProbe, derivedKMeta4) := by
  native_decide

theorem meta_instance_selects_derived_program :
    selectedProgram? = some PolicyProgram.deriveFromResidual := by
  native_decide

theorem meta_selected_repair_causes_adequate_replay :
    metaDevelopment.map (fun outcome => outcome.replayResiduals) = some [] := by
  native_decide

theorem one_develop_implementation_is_instantiated_twice :
    objectDevelopment.map (fun outcome => outcome.selected) =
        some EndToEnd.DiscTag.head ∧
    metaDevelopment.map (fun outcome => outcome.selected) =
        some PolicyProgram.deriveFromResidual := by
  native_decide

/-! ## Retained installation through the existing `adjoinStage` -/

def composeProgram : PolicyProgram → PolicyProgram → PolicyProgram
  | .keepBaseline, program => program
  | .deriveFromResidual, _ => .deriveFromResidual

def PolicyCategory : SmallCategory where
  Obj := Unit
  Hom := fun _ _ => PolicyProgram
  id := fun _ => .keepBaseline
  comp := composeProgram
  id_comp := by intro X Y program; cases program <;> rfl
  comp_id := by intro X Y program; cases program <;> rfl
  assoc := by
    intro W X Y Z h g f
    cases h <;> cases g <;> cases f <;> rfl

def baselineStage : Stage PolicyCategory where
  allow := fun program => program = .keepBaseline
  id_allow := by intro X; rfl
  comp_allow := by
    intro X Y Z g f hg hf
    subst g
    subst f
    rfl

def installedStage : Stage PolicyCategory :=
  @adjoinStage PolicyCategory baselineStage () () selectedProgram

theorem synthesized_program_is_retained :
    @installedStage.allow () () selectedProgram := by
  exact @seed_allowed PolicyCategory baselineStage () () selectedProgram

/-! ## The installed program is the resulting developer's runtime policy -/

structure Developer where
  stage : Stage PolicyCategory
  activeProgram : PolicyProgram
  active_is_retained : @stage.allow () () activeProgram

def oldDeveloper : Developer where
  stage := baselineStage
  activeProgram := .keepBaseline
  active_is_retained := rfl

def repairedDeveloper : Developer where
  stage := installedStage
  activeProgram := selectedProgram
  active_is_retained := synthesized_program_is_retained

def developerPolicy (developer : Developer) (k : SearchConstraint) : SearchPolicy :=
  interpretPolicyProgram developer.activeProgram k

/-- The selected Target-4 program, not Target-5-specific selection, is applied to
Target 5's independently derived constraint. -/
def synthesizedPolicy : SearchPolicy :=
  developerPolicy repairedDeveloper heldOutK

theorem synthesized_policy_has_exact_ancestry :
    selectedProgram = PolicyProgram.deriveFromResidual ∧
    repairedDeveloper.activeProgram = selectedProgram ∧
    @repairedDeveloper.stage.allow () () repairedDeveloper.activeProgram ∧
    synthesizedPolicy = interpretPolicyProgram selectedProgram heldOutK := by
  constructor
  · native_decide
  · constructor
    · rfl
    · constructor
      · exact repairedDeveloper.active_is_retained
      · rfl

theorem old_developer_fails_held_out :
    containsTerm
      (search (developerPolicy oldDeveloper heldOutK)
        SigPow powOps (fun _ => [0, 1, 2]) HSort.Nat)
      heldOutInvariant = false := by
  native_decide

theorem synthesized_policy_drives_held_out_success :
    containsTerm
      (search synthesizedPolicy SigPow powOps (fun _ => [0, 1, 2]) HSort.Nat)
      heldOutInvariant = true := by
  native_decide

/-- Sham: install the held-out cap while retaining old depth. -/
def shamPolicy : SearchPolicy :=
  { depthBound := baselineSearch.depthBound, arityCap := heldOutK.safeArity, budget := 0 }

theorem sham_does_not_explain_gain :
    containsTerm
      (search shamPolicy SigPow powOps (fun _ => [0, 1, 2]) HSort.Nat)
      heldOutInvariant = false := by
  native_decide

/-- Exact ablation removes the acquired constructor from the supplied family. -/
def ablatedCandidates : List
    (SynthesisCore.Candidate SearchConstraint SearchPolicy PolicyProgram) :=
  [⟨.keepBaseline, 0, interpretPolicyProgram .keepBaseline⟩]

def ablatedDevelopment : Option
    (SynthesisCore.DevelopmentOutcome SearchConstraint PolicyProgram) :=
  SynthesisCore.develop policyUniv policyQ0 policyFB
    ablatedCandidates policyRepairQuotient

def ablatedProgram : PolicyProgram :=
  match SynthesisCore.promoteIfReplayAdequate
      policyUniv policyFB policyRepairQuotient ablatedDevelopment with
  | some program => program
  | none => .keepBaseline

def ablatedPolicy : SearchPolicy :=
  interpretPolicyProgram ablatedProgram heldOutK

theorem exact_ablation_removes_repair :
    SynthesisCore.promoteIfReplayAdequate
      policyUniv policyFB policyRepairQuotient ablatedDevelopment = none := by
  native_decide

theorem exact_ablation_restores_failure :
    containsTerm
      (search ablatedPolicy SigPow powOps (fun _ => [0, 1, 2]) HSort.Nat)
      heldOutInvariant = false := by
  native_decide

end SharedSchemaRuntimeBridge

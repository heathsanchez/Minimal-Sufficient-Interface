import CLC.Transport
import CLC.Support
import Mathlib.Data.Fintype.Pi
import Mathlib.Data.Fintype.Powerset
import Mathlib.Data.Fintype.Sigma

namespace CLC

universe u

structure FiniteUniverse where
  NodeId : Type u
  EdgeId : Type u
  InPort : Type u
  OutPort : Type u
  Token : Type u
  FormCode : Type u
  CertId : Type u
  nodeFinite : Fintype NodeId
  edgeFinite : Fintype EdgeId
  inPortFinite : Fintype InPort
  outPortFinite : Fintype OutPort
  tokenFinite : Fintype Token
  formCodeFinite : Fintype FormCode
  certFinite : Fintype CertId
  nodeDecEq : DecidableEq NodeId
  edgeDecEq : DecidableEq EdgeId
  inPortDecEq : DecidableEq InPort
  outPortDecEq : DecidableEq OutPort
  tokenDecEq : DecidableEq Token
  formCodeDecEq : DecidableEq FormCode
  certDecEq : DecidableEq CertId

attribute [instance] FiniteUniverse.nodeFinite FiniteUniverse.edgeFinite
  FiniteUniverse.inPortFinite FiniteUniverse.outPortFinite
  FiniteUniverse.tokenFinite FiniteUniverse.formCodeFinite FiniteUniverse.certFinite
  FiniteUniverse.nodeDecEq FiniteUniverse.edgeDecEq FiniteUniverse.inPortDecEq
  FiniteUniverse.outPortDecEq FiniteUniverse.tokenDecEq
  FiniteUniverse.formCodeDecEq FiniteUniverse.certDecEq

structure RawView (U : FiniteUniverse) (Label : Type u)
    [Fintype Label] [DecidableEq Label] where
  activeNodes : Finset Label
  activeEdges : Finset U.EdgeId
  rank : Label → Nat
  inOwner : U.InPort → U.EdgeId
  outOwner : U.OutPort → U.EdgeId
  inputNode : U.InPort → Label
  outputNode : U.OutPort → Label
  mask : U.OutPort → Finset U.InPort
  edgeToken : U.EdgeId → U.Token
  base : Label → SupportFamily U.Token
  sigma : TokenSnapshot U.Token

abbrev ActiveInPort {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (p : U.InPort) : Prop :=
  R.inOwner p ∈ R.activeEdges

abbrev ActiveOutPort {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (p : U.OutPort) : Prop :=
  R.outOwner p ∈ R.activeEdges

def Immediate {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (x y : Label) : Prop :=
  ∃ o, ActiveOutPort R o ∧ R.outputNode o = y ∧
    ∃ p ∈ R.mask o, R.inputNode p = x

instance instDecidableImmediate {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (x y : Label) : Decidable (Immediate R x y) := by
  unfold Immediate
  infer_instance

structure ValidRaw {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label] (R : RawView U Label) : Prop where
  activeEdgeHasInput : ∀ e ∈ R.activeEdges, ∃ p, R.inOwner p = e
  activeEdgeHasOutput : ∀ e ∈ R.activeEdges, ∃ o, R.outOwner o = e
  maskOwner : ∀ o, ActiveOutPort R o →
    ∀ p ∈ R.mask o, R.inOwner p = R.outOwner o
  activeInputNode : ∀ p, ActiveInPort R p → R.inputNode p ∈ R.activeNodes
  activeOutputNode : ∀ o, ActiveOutPort R o → R.outputNode o ∈ R.activeNodes
  rank_lt : ∀ o, ActiveOutPort R o →
    ∀ p ∈ R.mask o, R.rank (R.inputNode p) < R.rank (R.outputNode o)
  baseNormalized : ∀ n, Normalized (R.base n)
  snapshotDisjoint : Disjoint R.sigma.live R.sigma.revoked

def ruleSupports {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (F : Label → SupportFamily U.Token)
    (o : U.OutPort) : SupportFamily U.Token :=
  Finset.univ.filter fun s =>
    ∃ choose : {p : U.InPort // p ∈ R.mask o} → Support U.Token,
      (∀ p, choose p ∈ F (R.inputNode p.1)) ∧
      s = insert (R.edgeToken (R.outOwner o)) (Finset.univ.biUnion choose)

def rankStep {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (r : Nat)
    (F : Label → SupportFamily U.Token) : Label → SupportFamily U.Token :=
  fun z =>
    if z ∈ R.activeNodes ∧ R.rank z = r then
      normalize (F z ∪
        ((Finset.univ.filter fun o =>
          ActiveOutPort R o ∧ R.outputNode o = z).biUnion
            (ruleSupports R F)))
    else F z

def prefixFamilies {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) : Nat → Label → SupportFamily U.Token
  | 0 => R.base
  | n + 1 => rankStep R n (prefixFamilies R n)

def maxRank {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) : Nat :=
  Finset.univ.sup R.rank

namespace ComponentwiseBoundaryModel

/-- The V0 reference model assumes whole-boundary tests select one component.
This is an explicit restricted instance, not a generic factorization theorem. -/
noncomputable def form {I : Type u} [Fintype I] [DecidableEq I]
    (A : I → Form.{u}) : Form.{u} where
  State := ∀ i, (A i).State
  Test := Σ i, (A i).Test
  stateFinite := inferInstance
  testFinite := inferInstance
  decState := Classical.decEq _
  decTest := Classical.decEq _
  «protected» := fun d => (A d.1).protected d.2
  eval := fun x d => (A d.1).eval (x d.1) d.2

end ComponentwiseBoundaryModel

abbrev InputBoundary {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (e : U.EdgeId) :=
  {p : U.InPort // R.inOwner p = e}

abbrev OutputBoundary {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (e : U.EdgeId) :=
  {o : U.OutPort // R.outOwner o = e}

noncomputable def inputBoundaryForm {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (formAt : U.FormCode → Form.{u})
    (nodeCode : Label → U.FormCode) (e : U.EdgeId) : Form.{u} :=
  ComponentwiseBoundaryModel.form fun p : InputBoundary R e =>
    formAt (nodeCode (R.inputNode p.1))

noncomputable def outputBoundaryForm {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (formAt : U.FormCode → Form.{u})
    (nodeCode : Label → U.FormCode) (e : U.EdgeId) : Form.{u} :=
  ComponentwiseBoundaryModel.form fun o : OutputBoundary R e =>
    formAt (nodeCode (R.outputNode o.1))

def inputBoundaryState {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (formAt : U.FormCode → Form.{u})
    (nodeCode : Label → U.FormCode)
    (nodeState : ∀ n, (formAt (nodeCode n)).State) (e : U.EdgeId) :
    (inputBoundaryForm R formAt nodeCode e).State :=
  fun p => nodeState (R.inputNode p.1)

def outputBoundaryState {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (formAt : U.FormCode → Form.{u})
    (nodeCode : Label → U.FormCode)
    (nodeState : ∀ n, (formAt (nodeCode n)).State) (e : U.EdgeId) :
    (outputBoundaryForm R formAt nodeCode e).State :=
  fun o => nodeState (R.outputNode o.1)

structure CertifiedSource (U : FiniteUniverse)
    (Ωauth : AuthoritySnapshot U.CertId) where
  raw : RawView U U.NodeId
  valid : ValidRaw raw
  formAt : U.FormCode → Form.{u}
  nodeCode : U.NodeId → U.FormCode
  nodeState : ∀ n, (formAt (nodeCode n)).State
  edgeTransport : ∀ e,
    VerifiedTransport Ωauth (inputBoundaryForm raw formAt nodeCode e)
      (outputBoundaryForm raw formAt nodeCode e)
  edgeSound : ∀ e,
    (edgeTransport e).mapState
      (inputBoundaryState raw formAt nodeCode nodeState e) =
      outputBoundaryState raw formAt nodeCode nodeState e
  activeOccurrenceLive : ∀ e ∈ raw.activeEdges,
    raw.edgeToken e ∈ raw.sigma.live

end CLC

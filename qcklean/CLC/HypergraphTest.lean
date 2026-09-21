import CLC.Hypergraph

open CLC

inductive Node | a₁ | a₂ | b deriving DecidableEq, Repr
inductive Edge | merge | coalesce deriving DecidableEq, Repr
inductive InPort | left | right | source deriving DecidableEq, Repr
inductive OutPort | result | first | second deriving DecidableEq, Repr
inductive Token | merge | coalesce deriving DecidableEq, Repr
inductive FormCode | boolean deriving DecidableEq, Repr
inductive Cert | trusted deriving DecidableEq, Repr

instance : Fintype Node where
  elems := {.a₁, .a₂, .b}
  complete := by intro n; cases n <;> simp

instance : Fintype Edge where
  elems := {.merge, .coalesce}
  complete := by intro e; cases e <;> simp

instance : Fintype InPort where
  elems := {.left, .right, .source}
  complete := by intro p; cases p <;> simp

instance : Fintype OutPort where
  elems := {.result, .first, .second}
  complete := by intro p; cases p <;> simp

instance : Fintype Token where
  elems := {.merge, .coalesce}
  complete := by intro t; cases t <;> simp

instance : Fintype FormCode where
  elems := {.boolean}
  complete := by intro c; cases c; simp

instance : Fintype Cert where
  elems := {.trusted}
  complete := by intro c; cases c; simp

def boolForm : Form where
  State := Bool
  Test := Bool
  stateFinite := inferInstance
  testFinite := inferInstance
  decState := inferInstance
  decTest := inferInstance
  «protected» := fun _ => true
  eval := fun x d => if x = d then Verdict.eq else Verdict.unknown

def U : FiniteUniverse where
  NodeId := Node
  EdgeId := Edge
  InPort := InPort
  OutPort := OutPort
  Token := Token
  FormCode := FormCode
  CertId := Cert
  nodeFinite := inferInstance
  edgeFinite := inferInstance
  inPortFinite := inferInstance
  outPortFinite := inferInstance
  tokenFinite := inferInstance
  formCodeFinite := inferInstance
  certFinite := inferInstance
  nodeDecEq := inferInstance
  edgeDecEq := inferInstance
  inPortDecEq := inferInstance
  outPortDecEq := inferInstance
  tokenDecEq := inferInstance
  formCodeDecEq := inferInstance
  certDecEq := inferInstance

def raw : RawView U Node where
  activeNodes := {Node.a₁, Node.a₂, Node.b}
  activeEdges := {Edge.merge, Edge.coalesce}
  rank
    | .a₁ | .a₂ => 0
    | .b => 1
  inOwner
    | .left | .right => .merge
    | .source => .coalesce
  outOwner
    | .result => .merge
    | .first | .second => .coalesce
  inputNode
    | .left => .a₁
    | .right => .a₂
    | .source => .a₁
  outputNode := fun _ => .b
  mask
    | .result => {.left, .right}
    | .first => {.source}
    | .second => ∅
  edgeToken
    | .merge => .merge
    | .coalesce => .coalesce
  base := fun _ => ∅
  sigma := {
    live := {Token.merge, Token.coalesce}
    revoked := ∅
    disjoint := by decide
  }

#check FiniteUniverse
#check RawView
#check ValidRaw
#check ComponentwiseBoundaryModel.form
#check CertifiedSource
#check Immediate
#check ruleSupports
#check rankStep
#check prefixFamilies
#check maxRank

example :
    (ComponentwiseBoundaryModel.form (fun _ : Fin 2 => boolForm)).eval
      (fun | 0 => false | 1 => true) ⟨1, Bool.true⟩ = Verdict.eq := by
  rfl

example : raw.mask OutPort.result = {InPort.left, InPort.right} := by native_decide
example : Immediate raw Node.a₁ Node.b := by decide
example : Immediate raw Node.a₂ Node.b := by decide

example : ActiveOutPort raw OutPort.first := by decide
example : ActiveOutPort raw OutPort.second := by decide
example : raw.outputNode OutPort.first = raw.outputNode OutPort.second := rfl
example : raw.mask OutPort.first ≠ raw.mask OutPort.second := by native_decide

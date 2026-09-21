import CLC.Query

open CLC

inductive QNode | a | b | c | d deriving DecidableEq, Repr
inductive QEdge | ab | bc | ad | dc deriving DecidableEq, Repr
inductive QIn | ab | bc | ad | dc deriving DecidableEq, Repr
inductive QOut | ab | bc | ad | dc deriving DecidableEq, Repr
inductive QToken | left | right | edge deriving DecidableEq, Repr
inductive QCode | unit deriving DecidableEq, Repr
inductive QCert | unit deriving DecidableEq, Repr
inductive Collapse | joined | other deriving DecidableEq, Repr

instance : Fintype QNode where
  elems := {.a, .b, .c, .d}
  complete := by intro n; cases n <;> simp

instance : Fintype QEdge where
  elems := {.ab, .bc, .ad, .dc}
  complete := by intro e; cases e <;> simp

instance : Fintype QIn where
  elems := {.ab, .bc, .ad, .dc}
  complete := by intro p; cases p <;> simp

instance : Fintype QOut where
  elems := {.ab, .bc, .ad, .dc}
  complete := by intro p; cases p <;> simp

instance : Fintype QToken where
  elems := {.left, .right, .edge}
  complete := by intro t; cases t <;> simp

instance : Fintype QCode where
  elems := {.unit}
  complete := by intro c; cases c; simp

instance : Fintype QCert where
  elems := {.unit}
  complete := by intro c; cases c; simp

instance : Fintype Collapse where
  elems := {.joined, .other}
  complete := by intro c; cases c <;> simp

def queryU : FiniteUniverse where
  NodeId := QNode
  EdgeId := QEdge
  InPort := QIn
  OutPort := QOut
  Token := QToken
  FormCode := QCode
  CertId := QCert
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

def edgeOfIn : QIn → QEdge
  | .ab => .ab | .bc => .bc | .ad => .ad | .dc => .dc

def edgeOfOut : QOut → QEdge
  | .ab => .ab | .bc => .bc | .ad => .ad | .dc => .dc

def inputOf : QIn → QNode
  | .ab | .ad => .a
  | .bc => .b
  | .dc => .d

def outputOf : QOut → QNode
  | .ab => .b
  | .bc | .dc => .c
  | .ad => .d

def maskOf : QOut → Finset QIn
  | .ab => {.ab} | .bc => {.bc} | .ad => {.ad} | .dc => {.dc}

def chainRaw : RawView queryU QNode where
  activeNodes := {.a, .b, .c, .d}
  activeEdges := {.ab, .bc}
  rank
    | .a => 0 | .b => 1 | .c => 2 | .d => 0
  inOwner := edgeOfIn
  outOwner := edgeOfOut
  inputNode := inputOf
  outputNode := outputOf
  mask := maskOf
  edgeToken := fun _ => .edge
  base := fun _ => ∅
  sigma := {
    live := {.left, .right, .edge}
    revoked := ∅
    disjoint := by decide
  }

def chainFamilies : QNode → SupportFamily QToken
  | .a => {{.left}}
  | .b => {{.left, .edge}}
  | .c => {{.left, .edge}, {.right, .edge}}
  | .d => ∅

def diamondRaw : RawView queryU QNode :=
  { chainRaw with activeEdges := {.ab, .bc, .ad, .dc} }

def emptyRaw : RawView queryU QNode :=
  { chainRaw with activeNodes := ∅, activeEdges := ∅ }

def collapse : QNode → Collapse
  | .a | .b => .joined
  | .c | .d => .other

def splitFamilies : QNode → SupportFamily QToken
  | .a => {{.left}}
  | .b => {{.right}}
  | .c | .d => ∅

#check PathN
#check Reachable
#check ProtectedQuery
#check labelFamily
#check evalQuery
#check reachable_iff_eval_true
#check reachable_iff_transGen
#check dependsOn_iff_eval_true
#check currentlyWarranted_iff_eval_true
#check hasAlternativeSupport_iff_eval_true

example : evalQuery id chainRaw chainFamilies
    (.reachable QNode.a QNode.c) = true := by native_decide

example : evalQuery id chainRaw chainFamilies
    (.dependsOn QNode.a QNode.c) = false := by native_decide

example : evalQuery id chainRaw chainFamilies
    (.reachable QNode.a QNode.d) = false := by native_decide

example : evalQuery id emptyRaw chainFamilies
    (.reachable QNode.a QNode.c) = false := by native_decide

example : evalQuery id diamondRaw chainFamilies
    (.reachable QNode.a QNode.c) = true := by native_decide

example : evalQuery id chainRaw chainFamilies
    (.currentlyWarranted QNode.c) = true := by native_decide

example : evalQuery id chainRaw chainFamilies
    (.hasAlternativeSupport QNode.c) = true := by native_decide

example : labelFamily collapse chainRaw splitFamilies Collapse.joined =
    {{QToken.left}, {QToken.right}} := by native_decide

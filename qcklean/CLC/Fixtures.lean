import CLC.Grow

namespace CLC.Fixtures

inductive RawNode | a₁ | a₂ | b₁ | b₂ | c deriving DecidableEq, Repr
inductive QuotLabel | a | b | c deriving DecidableEq, Repr
inductive SpuriousEdge | ab | bc deriving DecidableEq, Repr
inductive SpuriousIn | fromA | fromB deriving DecidableEq, Repr
inductive SpuriousOut | toB | toC deriving DecidableEq, Repr
inductive SpuriousToken | ab | bc deriving DecidableEq, Repr

instance : Fintype RawNode where
  elems := {.a₁, .a₂, .b₁, .b₂, .c}
  complete := by intro n; cases n <;> simp

instance : Fintype QuotLabel where
  elems := {.a, .b, .c}
  complete := by intro n; cases n <;> simp

instance : Fintype SpuriousEdge where
  elems := {.ab, .bc}
  complete := by intro e; cases e <;> simp

instance : Fintype SpuriousIn where
  elems := {.fromA, .fromB}
  complete := by intro p; cases p <;> simp

instance : Fintype SpuriousOut where
  elems := {.toB, .toC}
  complete := by intro p; cases p <;> simp

instance : Fintype SpuriousToken where
  elems := {.ab, .bc}
  complete := by intro t; cases t <;> simp

def SpuriousUniverse : FiniteUniverse where
  NodeId := RawNode
  EdgeId := SpuriousEdge
  InPort := SpuriousIn
  OutPort := SpuriousOut
  Token := SpuriousToken
  FormCode := Unit
  CertId := Unit
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

def spuriousQ : RawNode → QuotLabel
  | .a₁ | .a₂ => .a
  | .b₁ | .b₂ => .b
  | .c => .c

def spuriousRank : RawNode → Nat
  | .a₁ | .a₂ => 0
  | .b₁ | .b₂ => 1
  | .c => 2

def spuriousRaw : RawView SpuriousUniverse RawNode where
  activeNodes := Finset.univ
  activeEdges := Finset.univ
  rank := spuriousRank
  inOwner
    | .fromA => .ab
    | .fromB => .bc
  outOwner
    | .toB => .ab
    | .toC => .bc
  inputNode
    | .fromA => .a₁
    | .fromB => .b₂
  outputNode
    | .toB => .b₁
    | .toC => .c
  mask
    | .toB => {.fromA}
    | .toC => {.fromB}
  edgeToken
    | .ab => .ab
    | .bc => .bc
  base := fun _ => ∅
  sigma := {
    live := Finset.univ
    revoked := ∅
    disjoint := by simp
  }

def spuriousProjected := projectRaw spuriousQ spuriousRaw

theorem spurious_lifting_fails :
    ¬ LocalPathLifting spuriousRaw spuriousQ := by
  intro h
  obtain ⟨y, _, hstep, hqy⟩ :=
    h RawNode.b₁ (by decide) QuotLabel.c (by decide)
  have hnone : ¬ ∃ y, Immediate spuriousRaw RawNode.b₁ y ∧
      spuriousQ y = QuotLabel.c := by decide
  exact hnone ⟨y, hstep, hqy⟩

theorem spuriousPath_not_admissible :
    ∀ (Ωauth : AuthoritySnapshot SpuriousUniverse.CertId)
      (S : CertifiedSource SpuriousUniverse Ωauth),
      S.raw = spuriousRaw → ¬ AdmissibleQuotient Ωauth S spuriousQ := by
  intro Ωauth S hraw h
  have hlift := h.pathLift
  rw [hraw] at hlift
  exact spurious_lifting_fails hlift

inductive PositiveNode | left | right | claim | isolated deriving DecidableEq, Repr
inductive PositiveLabel | evidence | claim | isolated deriving DecidableEq, Repr
inductive PositiveEdge | leftRule | rightRule deriving DecidableEq, Repr
inductive PositiveIn | left | right deriving DecidableEq, Repr
inductive PositiveOut | leftRule | rightRule deriving DecidableEq, Repr
inductive PositiveToken | left | right | edge | dormant deriving DecidableEq, Repr

instance : Fintype PositiveNode where
  elems := {.left, .right, .claim, .isolated}
  complete := by intro n; cases n <;> simp

instance : Fintype PositiveLabel where
  elems := {.evidence, .claim, .isolated}
  complete := by intro n; cases n <;> simp

instance : Fintype PositiveEdge where
  elems := {.leftRule, .rightRule}
  complete := by intro e; cases e <;> simp

instance : Fintype PositiveIn where
  elems := {.left, .right}
  complete := by intro p; cases p <;> simp

instance : Fintype PositiveOut where
  elems := {.leftRule, .rightRule}
  complete := by intro p; cases p <;> simp

instance : Fintype PositiveToken where
  elems := {.left, .right, .edge, .dormant}
  complete := by intro t; cases t <;> simp

def PositiveUniverse : FiniteUniverse where
  NodeId := PositiveNode
  EdgeId := PositiveEdge
  InPort := PositiveIn
  OutPort := PositiveOut
  Token := PositiveToken
  FormCode := Unit
  CertId := Unit
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

def positiveQ : PositiveNode → PositiveLabel
  | .left | .right => .evidence
  | .claim => .claim
  | .isolated => .isolated

def positiveRaw : RawView PositiveUniverse PositiveNode where
  activeNodes := Finset.univ
  activeEdges := Finset.univ
  rank
    | .left | .right | .isolated => 0
    | .claim => 1
  inOwner
    | .left => .leftRule
    | .right => .rightRule
  outOwner
    | .leftRule => .leftRule
    | .rightRule => .rightRule
  inputNode
    | .left => .left
    | .right => .right
  outputNode := fun _ => .claim
  mask
    | .leftRule => {.left}
    | .rightRule => {.right}
  edgeToken := fun _ => .edge
  base
    | .left => {{.left}}
    | .right => {{.right}}
    | .claim => ∅
    | .isolated => {{.right}}
  sigma := {
    live := {.left, .right, .edge}
    revoked := ∅
    disjoint := by simp
  }

theorem positiveValid : ValidRaw positiveRaw where
  activeEdgeHasInput := by
    intro e _
    cases e
    · exact ⟨PositiveIn.left, rfl⟩
    · exact ⟨PositiveIn.right, rfl⟩
  activeEdgeHasOutput := by
    intro e _
    cases e
    · exact ⟨PositiveOut.leftRule, rfl⟩
    · exact ⟨PositiveOut.rightRule, rfl⟩
  maskOwner := by
    intro o _ p hp
    cases o <;> cases p
    · rfl
    · have heq := Finset.mem_singleton.mp hp; contradiction
    · have heq := Finset.mem_singleton.mp hp; contradiction
    · rfl
  activeInputNode := by intro p _; cases p <;> simp [positiveRaw]
  activeOutputNode := by intro o _; cases o <;> simp [positiveRaw]
  rank_lt := by
    intro o _ p hp
    cases o <;> cases p <;> simp_all [positiveRaw]
  baseNormalized := by
    intro n
    cases n <;> change normalize _ = _ <;> native_decide
  snapshotDisjoint := positiveRaw.sigma.disjoint

def closed0 : ClosedView PositiveUniverse PositiveNode :=
  batchClose positiveRaw positiveValid

def addSupportChecked : CheckedViewEvent closed0.raw :=
  checkedAddBaseSupport positiveRaw positiveValid PositiveNode.left
    {PositiveToken.left} (by native_decide)

def enableDormantChecked : CheckedViewEvent closed0.raw :=
  checkedEnable positiveRaw positiveValid PositiveToken.dormant (by
    change PositiveToken.dormant ∉ ({.left, .right, .edge} : Finset PositiveToken) ∧
      PositiveToken.dormant ∉ (∅ : Finset PositiveToken)
    native_decide)

def revokeLeftChecked : CheckedViewEvent closed0.raw :=
  checkedRevoke positiveRaw positiveValid PositiveToken.left (by
    change PositiveToken.left ∈ ({.left, .right, .edge} : Finset PositiveToken)
    native_decide)

def absorbChecked : CheckedViewEvent closed0.raw :=
  checkedAbsorbNodes positiveRaw positiveValid {PositiveNode.left}
    positiveRaw.rank (by intro z _; rfl)

inductive CrossNode | a₁ | a₂ | b₁ | b₂ | claim deriving DecidableEq, Repr
inductive CrossLabel | a | b | claim deriving DecidableEq, Repr
inductive CrossEdge | first | second deriving DecidableEq, Repr
inductive CrossIn | a₁ | b₁ | a₂ | b₂ deriving DecidableEq, Repr
inductive CrossOut | first | second deriving DecidableEq, Repr
inductive CrossToken | a₁ | a₂ | first | second
  deriving DecidableEq, Repr

instance : Fintype CrossNode where
  elems := {.a₁, .a₂, .b₁, .b₂, .claim}
  complete := by intro n; cases n <;> simp

instance : Fintype CrossLabel where
  elems := {.a, .b, .claim}
  complete := by intro n; cases n <;> simp

instance : Fintype CrossEdge where
  elems := {.first, .second}
  complete := by intro e; cases e <;> simp

instance : Fintype CrossIn where
  elems := {.a₁, .b₁, .a₂, .b₂}
  complete := by intro p; cases p <;> simp

instance : Fintype CrossOut where
  elems := {.first, .second}
  complete := by intro p; cases p <;> simp

instance : Fintype CrossToken where
  elems := {.a₁, .a₂, .first, .second}
  complete := by intro t; cases t <;> simp

def CrossUniverse : FiniteUniverse where
  NodeId := CrossNode
  EdgeId := CrossEdge
  InPort := CrossIn
  OutPort := CrossOut
  Token := CrossToken
  FormCode := Unit
  CertId := Unit
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

def crossMixingQ : CrossNode → CrossLabel
  | .a₁ | .a₂ => .a
  | .b₁ | .b₂ => .b
  | .claim => .claim

def crossMixingRaw : RawView CrossUniverse CrossNode where
  activeNodes := Finset.univ
  activeEdges := Finset.univ
  rank
    | .a₁ | .a₂ | .b₁ | .b₂ => 0
    | .claim => 1
  inOwner
    | .a₁ | .b₁ => .first
    | .a₂ | .b₂ => .second
  outOwner
    | .first => .first
    | .second => .second
  inputNode
    | .a₁ => .a₁
    | .a₂ => .a₂
    | .b₁ => .b₁
    | .b₂ => .b₂
  outputNode := fun _ => .claim
  mask
    | .first => {.a₁, .b₁}
    | .second => {.a₂, .b₂}
  edgeToken
    | .first => .first
    | .second => .second
  base
    | .a₁ => {{.a₁}}
    | .a₂ => {{.a₂}}
    | .b₁ | .b₂ => {(∅ : Support CrossToken)}
    | .claim => ∅
  sigma := {
    live := Finset.univ
    revoked := ∅
    disjoint := by simp
  }

theorem positiveSupportCompatible :
    SupportCompatible positiveRaw positiveQ :=
  supportCompatibleB_eq_true_iff.mp (by native_decide)

theorem crossMixing_path_lifts :
    LocalPathLifting crossMixingRaw crossMixingQ := by native_decide

theorem crossMixing_support_incompatible :
    ¬ SupportCompatible crossMixingRaw crossMixingQ := by
  intro h
  have : supportCompatibleB crossMixingRaw crossMixingQ = true :=
    supportCompatibleB_eq_true_iff.mpr h
  have hfalse : supportCompatibleB crossMixingRaw crossMixingQ = false := by
    native_decide
  rw [hfalse] at this
  exact Bool.noConfusion this

def positiveAuthority : AuthoritySnapshot Unit where
  accepts := fun _ => true
  live := fun _ => true
  idCert := ()
  compCert := fun _ _ => ()
  accepts_id := rfl
  live_id := rfl
  accepts_comp := by intros; rfl
  live_comp := by intros; rfl
  certEq := Eq
  certEq_refl := fun _ => rfl
  certEq_symm := Eq.symm
  certEq_trans := Eq.trans
  accepts_congr := by intro _ _ _; rfl
  live_congr := by intro _ _ _; rfl
  comp_congr := by intros; rfl
  comp_assoc := by intros; rfl
  id_left := by intros; rfl
  id_right := by intros; rfl

def positiveForm : Form where
  State := Unit
  Test := Unit
  stateFinite := inferInstance
  testFinite := inferInstance
  decState := inferInstance
  decTest := inferInstance
  «protected» := fun _ => true
  eval := fun _ _ => Verdict.eq

def positiveInputPort (e : PositiveEdge) :
    InputBoundary positiveRaw e :=
  match e with
  | .leftRule => ⟨.left, rfl⟩
  | .rightRule => ⟨.right, rfl⟩

def positiveOutputPort (e : PositiveEdge) :
    OutputBoundary positiveRaw e :=
  match e with
  | .leftRule => ⟨.leftRule, rfl⟩
  | .rightRule => ⟨.rightRule, rfl⟩

instance positiveInputBoundarySubsingleton (e : PositiveEdge) :
    Subsingleton (InputBoundary positiveRaw e) where
  allEq := by
    rintro ⟨a, ha⟩ ⟨b, hb⟩
    apply Subtype.ext
    have howner : positiveRaw.inOwner a = positiveRaw.inOwner b := ha.trans hb.symm
    cases a <;> cases b <;> simp_all [positiveRaw] <;> rfl

instance positiveOutputBoundarySubsingleton (e : PositiveEdge) :
    Subsingleton (OutputBoundary positiveRaw e) where
  allEq := by
    rintro ⟨a, ha⟩ ⟨b, hb⟩
    apply Subtype.ext
    have howner : positiveRaw.outOwner a = positiveRaw.outOwner b := ha.trans hb.symm
    cases a <;> cases b <;> simp_all [positiveRaw] <;> rfl

noncomputable def positiveEdgeTransport (e : PositiveEdge) :
    VerifiedTransport positiveAuthority
      (inputBoundaryForm positiveRaw (fun _ => positiveForm) (fun _ => ()) e)
      (outputBoundaryForm positiveRaw (fun _ => positiveForm) (fun _ => ()) e) where
  mapState := fun _ _ => ()
  pullTest := fun _ => ⟨positiveInputPort e, ()⟩
  pullProtected := by intros; rfl
  liftProtected := fun _ => ⟨⟨positiveOutputPort e, ()⟩, rfl⟩
  refine := by intros; exact le_rfl
  split := by
    intro p
    apply Sigma.ext
    · exact Subsingleton.elim _ _
    · rfl
  cert := ()
  checked := rfl
  liveAt := rfl

noncomputable def positiveSource :
    CertifiedSource PositiveUniverse positiveAuthority where
  raw := positiveRaw
  valid := positiveValid
  formAt := fun _ => positiveForm
  nodeCode := fun _ => ()
  nodeState := fun _ => ()
  edgeTransport := positiveEdgeTransport
  edgeSound := by intro e; funext o; rfl
  activeOccurrenceLive := by
    intro e _
    cases e <;> native_decide

theorem positiveHQ :
    AdmissibleQuotient (U := PositiveUniverse) (Label := PositiveLabel)
      positiveAuthority positiveSource positiveQ where
  typed := by intros; rfl
  ranked := by
    intro x y _ _ hxy
    change positiveRaw.rank x = positiveRaw.rank y
    cases x <;> cases y <;> simp_all [positiveQ, positiveRaw]
  continuation := by
    intro x y hx hy hxy B a p
    have hstate : positiveSource.nodeState x =
        cast
          (congrArg (fun code => (positiveSource.formAt code).State)
            (by rfl : positiveSource.nodeCode y = positiveSource.nodeCode x))
          (positiveSource.nodeState y) := by
      change () = cast _ ()
      rfl
    rw [hstate]
  pathLift := by
    change LocalPathLifting positiveRaw positiveQ
    native_decide
  supportCompatible := positiveSupportCompatible

noncomputable def positiveClosed :
    ClosedSource PositiveUniverse positiveAuthority where
  source := positiveSource
  closed := closed0
  raw_eq := rfl

noncomputable def positiveProjected :
    ClosedView PositiveUniverse PositiveLabel :=
  canonicalProjected positiveClosed positiveHQ

theorem positiveProjected_raw :
    positiveProjected.raw = projectRaw positiveQ positiveRaw := by
  rfl

def positiveReplayProjected : ClosedView PositiveUniverse PositiveLabel :=
  projectClosed positiveQ closed0 positiveSupportCompatible
    (projectedValid positiveHQ)

noncomputable def positiveTraceNil :
    AllowedTrace (U := PositiveUniverse) (Label := PositiveLabel)
      positiveAuthority positiveQ positiveClosed positiveHQ [] :=
  .nil _ _

noncomputable def positiveProjectedTraceNil :
    ProjectedTrace positiveProjected := .nil _

def dormantToken : PositiveUniverse.Token := PositiveToken.dormant

def dormantSupport : Support PositiveUniverse.Token :=
  {dormantToken, PositiveToken.edge}

theorem dormant_mem_dormantSupport :
    dormantToken ∈ dormantSupport := by
  exact Finset.mem_insert_self _ _

theorem positiveProjected_revoked :
    positiveProjected.raw.sigma.revoked = ∅ := by
  rw [positiveProjected_raw]
  rfl

def projectedFirstEvent :
    CheckedViewEvent positiveReplayProjected.raw :=
  checkedAbsorbNodes positiveReplayProjected.raw positiveReplayProjected.valid
    {PositiveLabel.evidence} positiveReplayProjected.raw.rank (by intros; rfl)

def projectedAddDormant :
    CheckedViewEvent positiveReplayProjected.raw :=
  checkedAddBaseSupport positiveReplayProjected.raw positiveReplayProjected.valid
    PositiveLabel.claim dormantSupport (by
      refine ⟨?_, ?_, ?_⟩
      · native_decide
      · exact ⟨dormantToken, dormant_mem_dormantSupport⟩
      · intro t ht
        change t ∉ (∅ : Finset PositiveUniverse.Token)
        simp)

def projectedAfterDormant :
    ClosedView PositiveUniverse PositiveLabel :=
  flashStep positiveReplayProjected projectedAddDormant

theorem projectedAfterDormant_sigma :
    projectedAfterDormant.raw.sigma = positiveReplayProjected.raw.sigma := by
  rfl

def projectedEnableDormant :
    CheckedViewEvent projectedAfterDormant.raw :=
  checkedEnable projectedAfterDormant.raw projectedAfterDormant.valid
    dormantToken (by
      rw [projectedAfterDormant_sigma]
      change dormantToken ∉ ({.left, .right, .edge} : Finset PositiveUniverse.Token) ∧
        dormantToken ∉ (∅ : Finset PositiveUniverse.Token)
      native_decide)

def positiveProjectedTrace : ProjectedTrace positiveReplayProjected :=
  .cons projectedAddDormant
    (.cons projectedEnableDormant (.nil _))

end CLC.Fixtures

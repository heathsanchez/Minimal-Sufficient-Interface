import CLC.Continuation
import CLC.Query

namespace CLC

universe u

def fibreMin {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [DecidableEq Label]
    (q : Node → Label) (R : RawView U Node)
    (F : Node → SupportFamily U.Token) (z : Label) : SupportFamily U.Token :=
  normalize <| (Finset.univ.filter fun x =>
    x ∈ R.activeNodes ∧ q x = z).biUnion F

def fibreRank {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [DecidableEq Label]
    (q : Node → Label) (R : RawView U Node) (z : Label) : Nat :=
  (Finset.univ.filter fun x => x ∈ R.activeNodes ∧ q x = z).sup R.rank

def projectRaw {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [Fintype Label] [DecidableEq Label]
    (q : Node → Label) (R : RawView U Node) : RawView U Label where
  activeNodes := R.activeNodes.image q
  activeEdges := R.activeEdges
  rank := fibreRank q R
  inOwner := R.inOwner
  outOwner := R.outOwner
  inputNode := q ∘ R.inputNode
  outputNode := q ∘ R.outputNode
  mask := R.mask
  edgeToken := R.edgeToken
  base := fibreMin q R R.base
  sigma := R.sigma

structure ViewEq {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R S : RawView U Label) : Prop where
  activeNodes_eq : R.activeNodes = S.activeNodes
  activeEdges_eq : R.activeEdges = S.activeEdges
  rank_eq : ∀ x, R.rank x = S.rank x
  inOwner_eq : ∀ p, R.inOwner p = S.inOwner p
  outOwner_eq : ∀ o, R.outOwner o = S.outOwner o
  inputNode_eq : ∀ p, R.inputNode p = S.inputNode p
  outputNode_eq : ∀ o, R.outputNode o = S.outputNode o
  mask_eq : ∀ o, R.mask o = S.mask o
  edgeToken_eq : ∀ e, R.edgeToken e = S.edgeToken e
  base_eq : ∀ x, R.base x = S.base x
  snapshot_eq : R.sigma = S.sigma

namespace RawView

@[ext] theorem ext {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label] {R S : RawView U Label}
    (activeNodes : R.activeNodes = S.activeNodes)
    (activeEdges : R.activeEdges = S.activeEdges)
    (rank : R.rank = S.rank)
    (inOwner : R.inOwner = S.inOwner)
    (outOwner : R.outOwner = S.outOwner)
    (inputNode : R.inputNode = S.inputNode)
    (outputNode : R.outputNode = S.outputNode)
    (mask : R.mask = S.mask)
    (edgeToken : R.edgeToken = S.edgeToken)
    (base : R.base = S.base)
    (sigma : R.sigma = S.sigma) : R = S := by
  cases R
  cases S
  simp_all only

end RawView

namespace ViewEq

theorem refl {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label] (R : RawView U Label) : ViewEq R R where
  activeNodes_eq := rfl
  activeEdges_eq := rfl
  rank_eq := fun _ => rfl
  inOwner_eq := fun _ => rfl
  outOwner_eq := fun _ => rfl
  inputNode_eq := fun _ => rfl
  outputNode_eq := fun _ => rfl
  mask_eq := fun _ => rfl
  edgeToken_eq := fun _ => rfl
  base_eq := fun _ => rfl
  snapshot_eq := rfl

theorem symm {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label] {R S : RawView U Label}
    (h : ViewEq R S) : ViewEq S R where
  activeNodes_eq := h.activeNodes_eq.symm
  activeEdges_eq := h.activeEdges_eq.symm
  rank_eq := fun x => (h.rank_eq x).symm
  inOwner_eq := fun p => (h.inOwner_eq p).symm
  outOwner_eq := fun o => (h.outOwner_eq o).symm
  inputNode_eq := fun p => (h.inputNode_eq p).symm
  outputNode_eq := fun o => (h.outputNode_eq o).symm
  mask_eq := fun o => (h.mask_eq o).symm
  edgeToken_eq := fun e => (h.edgeToken_eq e).symm
  base_eq := fun x => (h.base_eq x).symm
  snapshot_eq := h.snapshot_eq.symm

theorem trans {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label] {R S T : RawView U Label}
    (hRS : ViewEq R S) (hST : ViewEq S T) : ViewEq R T where
  activeNodes_eq := hRS.activeNodes_eq.trans hST.activeNodes_eq
  activeEdges_eq := hRS.activeEdges_eq.trans hST.activeEdges_eq
  rank_eq := fun x => (hRS.rank_eq x).trans (hST.rank_eq x)
  inOwner_eq := fun p => (hRS.inOwner_eq p).trans (hST.inOwner_eq p)
  outOwner_eq := fun o => (hRS.outOwner_eq o).trans (hST.outOwner_eq o)
  inputNode_eq := fun p => (hRS.inputNode_eq p).trans (hST.inputNode_eq p)
  outputNode_eq := fun o => (hRS.outputNode_eq o).trans (hST.outputNode_eq o)
  mask_eq := fun o => (hRS.mask_eq o).trans (hST.mask_eq o)
  edgeToken_eq := fun e => (hRS.edgeToken_eq e).trans (hST.edgeToken_eq e)
  base_eq := fun x => (hRS.base_eq x).trans (hST.base_eq x)
  snapshot_eq := hRS.snapshot_eq.trans hST.snapshot_eq

theorem toEq {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label] {R S : RawView U Label}
    (h : ViewEq R S) : R = S := by
  apply RawView.ext
  · exact h.activeNodes_eq
  · exact h.activeEdges_eq
  · exact funext h.rank_eq
  · exact funext h.inOwner_eq
  · exact funext h.outOwner_eq
  · exact funext h.inputNode_eq
  · exact funext h.outputNode_eq
  · exact funext h.mask_eq
  · exact funext h.edgeToken_eq
  · exact funext h.base_eq
  · exact h.snapshot_eq

end ViewEq

def LocalPathLifting {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [Fintype Label] [DecidableEq Label]
    (R : RawView U Node) (q : Node → Label) : Prop :=
  ∀ x, x ∈ R.activeNodes → ∀ z,
    Immediate (projectRaw q R) (q x) z →
      ∃ y, y ∈ R.activeNodes ∧ Immediate R x y ∧ q y = z

instance instDecidableLocalPathLifting
    {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [Fintype Label] [DecidableEq Label]
    (R : RawView U Node) (q : Node → Label) :
    Decidable (LocalPathLifting R q) := by
  unfold LocalPathLifting
  infer_instance

structure SupportCompatible {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [Fintype Label] [DecidableEq Label]
    (R : RawView U Node) (q : Node → Label) : Prop where
  base_commutes : ∀ z, (projectRaw q R).base z = fibreMin q R R.base z
  maxRank_commutes : maxRank (projectRaw q R) = maxRank R
  step_commutes : ∀ r, r < maxRank R + 1 → ∀ z,
    fibreMin q R (rankStep R r (prefixFamilies R r)) z =
      rankStep (projectRaw q R) r
        (fibreMin q R (prefixFamilies R r)) z
  same_snapshot : (projectRaw q R).sigma = R.sigma

structure AdmissibleQuotient {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (Ωauth : AuthoritySnapshot U.CertId)
    (S : CertifiedSource U Ωauth) (q : U.NodeId → Label) : Prop where
  typed : ∀ {x y}, x ∈ S.raw.activeNodes → y ∈ S.raw.activeNodes →
    q x = q y → S.nodeCode x = S.nodeCode y
  ranked : ∀ {x y}, x ∈ S.raw.activeNodes → y ∈ S.raw.activeNodes →
    q x = q y → S.raw.rank x = S.raw.rank y
  continuation : ∀ {x y} (hx : x ∈ S.raw.activeNodes)
      (hy : y ∈ S.raw.activeNodes) (hxy : q x = q y),
    ContinuationSafe Ωauth (S.formAt (S.nodeCode x))
      (S.nodeState x)
      (cast
        (congrArg (fun code => (S.formAt code).State)
          (typed hx hy hxy).symm)
        (S.nodeState y))
  pathLift : LocalPathLifting S.raw q
  supportCompatible : SupportCompatible S.raw q

theorem quotient_immediate_forward {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [Fintype Label] [DecidableEq Label]
    (q : Node → Label) {R : RawView U Node} {x y : Node}
    (h : Immediate R x y) : Immediate (projectRaw q R) (q x) (q y) := by
  rcases h with ⟨o, ho, hout, p, hp, hin⟩
  exact ⟨o, ho, congrArg q hout, p, hp, congrArg q hin⟩

private theorem quotient_path_forward {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [Fintype Label] [DecidableEq Label]
    (q : Node → Label) {R : RawView U Node} {n : Nat} {x y : Node}
    (h : PathN R n x y) : PathN (projectRaw q R) n (q x) (q y) := by
  induction n generalizing x with
  | zero => exact h.elim
  | succ n ih =>
      rcases h with hxy | ⟨z, hxz, hzy⟩
      · exact Or.inl (quotient_immediate_forward q hxy)
      · exact Or.inr ⟨q z, quotient_immediate_forward q hxz, ih hzy⟩

theorem quotient_path_lift {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [Fintype Label] [DecidableEq Label]
    {q : Node → Label} {R : RawView U Node}
    (hlift : LocalPathLifting R q) {n : Nat} {x : Node} {z : Label}
    (hx : x ∈ R.activeNodes) (h : PathN (projectRaw q R) n (q x) z) :
    ∃ y, y ∈ R.activeNodes ∧ PathN R n x y ∧ q y = z := by
  induction n generalizing x z with
  | zero => exact h.elim
  | succ n ih =>
      rcases h with hxz | ⟨w, hxw, hwz⟩
      · obtain ⟨y, hy, hxy, hqy⟩ := hlift x hx z hxz
        exact ⟨y, hy, Or.inl hxy, hqy⟩
      · obtain ⟨y, hy, hxy, hqy⟩ := hlift x hx w hxw
        obtain ⟨v, hv, hyv, hqv⟩ := ih hy (hqy ▸ hwz)
        exact ⟨v, hv, Or.inr ⟨y, hxy, hyv⟩, hqv⟩

private theorem fibreRank_eq {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [DecidableEq Label]
    {q : Node → Label} {R : RawView U Node}
    (ranked : ∀ {x y}, x ∈ R.activeNodes → y ∈ R.activeNodes →
      q x = q y → R.rank x = R.rank y)
    {x : Node} (hx : x ∈ R.activeNodes) : fibreRank q R (q x) = R.rank x := by
  let s := Finset.univ.filter fun y => y ∈ R.activeNodes ∧ q y = q x
  have hs : s.Nonempty := ⟨x, Finset.mem_filter.mpr ⟨Finset.mem_univ _, hx, rfl⟩⟩
  change s.sup R.rank = R.rank x
  rw [← Finset.sup'_eq_sup hs]
  apply Finset.sup'_eq_of_forall
  intro y hy
  have hy' := Finset.mem_filter.mp hy
  exact ranked hy'.2.1 hx hy'.2.2

theorem projectedValid {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {Ωauth : AuthoritySnapshot U.CertId} {S : CertifiedSource U Ωauth}
    {q : U.NodeId → Label} (hq : AdmissibleQuotient Ωauth S q) :
    ValidRaw (projectRaw q S.raw) where
  activeEdgeHasInput := S.valid.activeEdgeHasInput
  activeEdgeHasOutput := S.valid.activeEdgeHasOutput
  maskOwner := S.valid.maskOwner
  activeInputNode := by
    intro p hp
    exact Finset.mem_image.mpr ⟨S.raw.inputNode p,
      S.valid.activeInputNode p hp, rfl⟩
  activeOutputNode := by
    intro o ho
    exact Finset.mem_image.mpr ⟨S.raw.outputNode o,
      S.valid.activeOutputNode o ho, rfl⟩
  rank_lt := by
    intro o ho p hp
    change S.raw.outOwner o ∈ S.raw.activeEdges at ho
    change p ∈ S.raw.mask o at hp
    have hpActive : ActiveInPort S.raw p := by
      change S.raw.inOwner p ∈ S.raw.activeEdges
      rw [S.valid.maskOwner o ho p hp]
      exact ho
    have hin := S.valid.activeInputNode p hpActive
    have hout := S.valid.activeOutputNode o ho
    change fibreRank q S.raw (q (S.raw.inputNode p)) <
      fibreRank q S.raw (q (S.raw.outputNode o))
    rw [fibreRank_eq hq.ranked hin, fibreRank_eq hq.ranked hout]
    exact S.valid.rank_lt o ho p hp
  baseNormalized := by
    intro z
    exact normalize_idempotent _
  snapshotDisjoint := S.raw.sigma.disjoint

private theorem quotient_transGen_forward
    {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [Fintype Label] [DecidableEq Label]
    (q : Node → Label) {R : RawView U Node} {x y : Node}
    (h : Relation.TransGen (Immediate R) x y) :
    Relation.TransGen (Immediate (projectRaw q R)) (q x) (q y) := by
  induction h with
  | single hxy => exact Relation.TransGen.single (quotient_immediate_forward q hxy)
  | tail _ hyz ih =>
      exact Relation.TransGen.tail ih (quotient_immediate_forward q hyz)

private theorem reachable_labels_iff
    {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {Ωauth : AuthoritySnapshot U.CertId} {S : CertifiedSource U Ωauth}
    {q : U.NodeId → Label} (hq : AdmissibleQuotient Ωauth S q)
    (a b : Label) :
    (∃ x ∈ S.raw.activeNodes, q x = a ∧
      ∃ y ∈ S.raw.activeNodes, q y = b ∧ Reachable S.raw x y) ↔
    a ∈ (projectRaw q S.raw).activeNodes ∧
      b ∈ (projectRaw q S.raw).activeNodes ∧
      Reachable (projectRaw q S.raw) a b := by
  constructor
  · rintro ⟨x, hx, hqx, y, hy, hqy, hreach⟩
    refine ⟨Finset.mem_image.mpr ⟨x, hx, hqx⟩,
      Finset.mem_image.mpr ⟨y, hy, hqy⟩, ?_⟩
    rw [← hqx, ← hqy]
    apply transGen_to_reachable (projectedValid hq)
    exact quotient_transGen_forward q
      ((reachable_iff_transGen S.valid).mp hreach)
  · rintro ⟨ha, _hb, hreach⟩
    obtain ⟨x, hx, hqx⟩ := Finset.mem_image.mp ha
    obtain ⟨n, hn, hpath⟩ := hreach
    have hpath' : PathN (projectRaw q S.raw) (n + 1) (q x) b := by
      rwa [hqx]
    obtain ⟨y, hy, hsource, hqy⟩ :=
      quotient_path_lift hq.pathLift hx hpath'
    refine ⟨x, hx, hqx, y, hy, hqy, ?_⟩
    exact transGen_to_reachable S.valid (pathN_to_transGen hsource)

private theorem depends_labels_iff
    {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {Ωauth : AuthoritySnapshot U.CertId} {S : CertifiedSource U Ωauth}
    {q : U.NodeId → Label} (hq : AdmissibleQuotient Ωauth S q)
    (a b : Label) :
    (∃ x ∈ S.raw.activeNodes, q x = a ∧
      ∃ y ∈ S.raw.activeNodes, q y = b ∧ Immediate S.raw x y) ↔
    a ∈ (projectRaw q S.raw).activeNodes ∧
      b ∈ (projectRaw q S.raw).activeNodes ∧
      Immediate (projectRaw q S.raw) a b := by
  constructor
  · rintro ⟨x, hx, hqx, y, hy, hqy, hstep⟩
    refine ⟨Finset.mem_image.mpr ⟨x, hx, hqx⟩,
      Finset.mem_image.mpr ⟨y, hy, hqy⟩, ?_⟩
    rw [← hqx, ← hqy]
    exact quotient_immediate_forward q hstep
  · rintro ⟨ha, _hb, hstep⟩
    obtain ⟨x, hx, hqx⟩ := Finset.mem_image.mp ha
    have hstep' : Immediate (projectRaw q S.raw) (q x) b := by
      rwa [hqx]
    obtain ⟨y, hy, hxy, hqy⟩ := hq.pathLift x hx b hstep'
    exact ⟨x, hx, hqx, y, hy, hqy, hxy⟩

theorem labelFamily_fibreMin
    {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [Fintype Label] [DecidableEq Label]
    (q : Node → Label) (R : RawView U Node)
    (F : Node → SupportFamily U.Token) (z : Label) :
    labelFamily q R F z =
      labelFamily id (projectRaw q R) (fibreMin q R F) z := by
  let sourceFibre := Finset.univ.filter fun x : Node =>
    x ∈ R.activeNodes ∧ q x = z
  by_cases hz : z ∈ R.activeNodes.image q
  · have hquot : (Finset.univ.filter fun a : Label =>
        a ∈ (projectRaw q R).activeNodes ∧ id a = z) = {z} := by
      apply Finset.ext
      intro a
      rw [Finset.mem_filter, Finset.mem_singleton]
      simp only [Finset.mem_univ, true_and]
      change (a ∈ R.activeNodes.image q ∧ a = z) ↔ a = z
      constructor
      · exact fun h => h.2
      · intro h
        subst a
        exact ⟨hz, rfl⟩
    change normalize (sourceFibre.biUnion F) =
      normalize ((Finset.univ.filter fun a : Label =>
        a ∈ (projectRaw q R).activeNodes ∧ id a = z).biUnion
          (fibreMin q R F))
    rw [hquot]
    rw [Finset.singleton_biUnion]
    change normalize (sourceFibre.biUnion F) =
      normalize (normalize (sourceFibre.biUnion F))
    exact (normalize_idempotent _).symm
  · have hsource : sourceFibre = ∅ := by
      apply Finset.eq_empty_iff_forall_notMem.mpr
      intro x hx
      have hx' := Finset.mem_filter.mp hx
      exact hz (Finset.mem_image.mpr ⟨x, hx'.2.1, hx'.2.2⟩)
    have hquot : (Finset.univ.filter fun a : Label =>
        a ∈ (projectRaw q R).activeNodes ∧ id a = z) = ∅ := by
      apply Finset.eq_empty_iff_forall_notMem.mpr
      intro a ha
      have ha' := Finset.mem_filter.mp ha
      exact hz (ha'.2.2 ▸ ha'.2.1)
    change normalize (sourceFibre.biUnion F) =
      normalize ((Finset.univ.filter fun a : Label =>
        a ∈ (projectRaw q R).activeNodes ∧ id a = z).biUnion
          (fibreMin q R F))
    rw [hsource, hquot]
    rfl

theorem reachable_preserved
    {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {Ωauth : AuthoritySnapshot U.CertId} {S : CertifiedSource U Ωauth}
    {q : U.NodeId → Label} (hq : AdmissibleQuotient Ωauth S q)
    (F : U.NodeId → SupportFamily U.Token) (a b : Label) :
    evalQuery q S.raw F (.reachable a b) =
      evalQuery id (projectRaw q S.raw) (fibreMin q S.raw F) (.reachable a b) := by
  rw [Bool.eq_iff_iff, reachable_iff_eval_true, reachable_iff_eval_true]
  simpa using reachable_labels_iff hq a b

theorem dependsOn_preserved
    {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {Ωauth : AuthoritySnapshot U.CertId} {S : CertifiedSource U Ωauth}
    {q : U.NodeId → Label} (hq : AdmissibleQuotient Ωauth S q)
    (F : U.NodeId → SupportFamily U.Token) (a b : Label) :
    evalQuery q S.raw F (.dependsOn a b) =
      evalQuery id (projectRaw q S.raw) (fibreMin q S.raw F) (.dependsOn a b) := by
  rw [Bool.eq_iff_iff, dependsOn_iff_eval_true, dependsOn_iff_eval_true]
  simpa using depends_labels_iff hq a b

theorem currentlyWarranted_preserved
    {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [Fintype Label] [DecidableEq Label]
    (q : Node → Label) (R : RawView U Node)
    (F : Node → SupportFamily U.Token) (a : Label) :
    evalQuery q R F (.currentlyWarranted a) =
      evalQuery id (projectRaw q R) (fibreMin q R F)
        (.currentlyWarranted a) := by
  rw [Bool.eq_iff_iff, currentlyWarranted_iff_eval_true,
    currentlyWarranted_iff_eval_true, ← labelFamily_fibreMin q R F a]
  rfl

theorem hasAlternativeSupport_preserved
    {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [Fintype Label] [DecidableEq Label]
    (q : Node → Label) (R : RawView U Node)
    (F : Node → SupportFamily U.Token) (a : Label) :
    evalQuery q R F (.hasAlternativeSupport a) =
      evalQuery id (projectRaw q R) (fibreMin q R F)
        (.hasAlternativeSupport a) := by
  rw [Bool.eq_iff_iff, hasAlternativeSupport_iff_eval_true,
    hasAlternativeSupport_iff_eval_true, ← labelFamily_fibreMin q R F a]

end CLC

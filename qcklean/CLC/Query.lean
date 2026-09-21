import CLC.Hypergraph
import Mathlib.Data.Fintype.Card
import Mathlib.Data.List.Sort
import Mathlib.Logic.Relation

namespace CLC

universe u

def PathN {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) : Nat → Label → Label → Prop
  | 0, _, _ => False
  | n + 1, x, y => Immediate R x y ∨
      ∃ z, Immediate R x z ∧ PathN R n z y

instance instDecidablePathN {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (n : Nat) (x y : Label) :
    Decidable (PathN R n x y) := by
  induction n generalizing x y with
  | zero => exact isFalse id
  | succ n ih =>
      letI : ∀ z, Decidable (PathN R n z y) := fun z => ih z y
      simp only [PathN]
      infer_instance

def Reachable {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (x y : Label) : Prop :=
  ∃ n ∈ Finset.range (Fintype.card Label), PathN R (n + 1) x y

instance instDecidableReachable {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    (R : RawView U Label) (x y : Label) : Decidable (Reachable R x y) := by
  unfold Reachable
  infer_instance

theorem pathN_to_transGen {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {R : RawView U Label} {n : Nat} {x y : Label}
    (h : PathN R (n + 1) x y) : Relation.TransGen (Immediate R) x y := by
  induction n generalizing x with
  | zero =>
      simpa [PathN] using Relation.TransGen.single h
  | succ n ih =>
      rcases h with hxy | ⟨z, hxz, hzy⟩
      · exact Relation.TransGen.single hxy
      · exact Relation.TransGen.head hxz (ih hzy)

theorem reachable_to_transGen {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {R : RawView U Label} {x y : Label} (h : Reachable R x y) :
    Relation.TransGen (Immediate R) x y := by
  rcases h with ⟨n, _hn, hpath⟩
  exact pathN_to_transGen hpath

theorem immediate_rank_lt {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {R : RawView U Label} (valid : ValidRaw R) {x y : Label}
    (h : Immediate R x y) : R.rank x < R.rank y := by
  rcases h with ⟨o, ho, hout, p, hp, hin⟩
  rw [← hin, ← hout]
  exact valid.rank_lt o ho p hp

theorem transGen_rank_lt {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {R : RawView U Label} (valid : ValidRaw R) {x y : Label}
    (h : Relation.TransGen (Immediate R) x y) : R.rank x < R.rank y := by
  induction h with
  | single hxy => exact immediate_rank_lt valid hxy
  | tail _ hyz ih => exact ih.trans (immediate_rank_lt valid hyz)

private theorem pathN_of_chain {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {R : RawView U Label} {x y : Label} {l : List Label}
    (hne : l ≠ []) (hchain : (x :: l).IsChain (Immediate R))
    (hlast : (x :: l).getLast (by simp) = y) :
    PathN R l.length x y := by
  induction l generalizing x y with
  | nil => exact (hne rfl).elim
  | cons a rest ih =>
      have hxa : Immediate R x a := (List.isChain_cons_cons.mp hchain).1
      cases rest with
      | nil =>
          have hay : a = y := by simpa using hlast
          subst y
          exact Or.inl hxa
      | cons b tail =>
          apply Or.inr
          refine ⟨a, hxa, ?_⟩
          apply ih (by simp) (List.isChain_cons_cons.mp hchain).2
          simpa using hlast

theorem transGen_to_reachable {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {R : RawView U Label} (valid : ValidRaw R) {x y : Label}
    (h : Relation.TransGen (Immediate R) x y) : Reachable R x y := by
  obtain ⟨l, hchain, hlast⟩ :=
    List.exists_isChain_cons_of_relationReflTransGen h.to_reflTransGen
  have hne : l ≠ [] := by
    intro hl
    subst l
    have hxy : x = y := by simpa using hlast
    have hrankEq : R.rank x = R.rank y := congrArg R.rank hxy
    exact (transGen_rank_lt valid h).ne hrankEq
  cases l with
  | nil => exact (hne rfl).elim
  | cons a rest =>
      have hrankChain :
          (List.map R.rank (x :: a :: rest)).IsChain (fun m n => m < n) :=
        List.isChain_map_of_isChain R.rank
          (fun _ _ himm => immediate_rank_lt valid himm) hchain
      have hrankNodup : (List.map R.rank (x :: a :: rest)).Nodup :=
        hrankChain.sortedLT.nodup
      have hnodup : (x :: a :: rest).Nodup := hrankNodup.of_map R.rank
      have hcard : (x :: a :: rest).length ≤ Fintype.card Label :=
        hnodup.length_le_card
      have hcard' : rest.length + 2 ≤ Fintype.card Label := by
        simpa using hcard
      refine ⟨rest.length, Finset.mem_range.mpr (by omega), ?_⟩
      exact pathN_of_chain (by simp) hchain hlast

theorem reachable_iff_transGen {U : FiniteUniverse} {Label : Type u}
    [Fintype Label] [DecidableEq Label]
    {R : RawView U Label} (valid : ValidRaw R) {x y : Label} :
    Reachable R x y ↔ Relation.TransGen (Immediate R) x y :=
  ⟨reachable_to_transGen, transGen_to_reachable valid⟩

inductive ProtectedQuery (Label : Type u)
  | reachable (source target : Label)
  | dependsOn (parent child : Label)
  | currentlyWarranted (node : Label)
  | hasAlternativeSupport (node : Label)
  deriving DecidableEq

def labelFamily {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [DecidableEq Label]
    (label : Node → Label) (R : RawView U Node)
    (closed : Node → SupportFamily U.Token) (a : Label) :
    SupportFamily U.Token :=
  normalize <| (Finset.univ.filter fun x =>
    x ∈ R.activeNodes ∧ label x = a).biUnion closed

def evalQuery {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [DecidableEq Label]
    (label : Node → Label) (R : RawView U Node)
    (closed : Node → SupportFamily U.Token) : ProtectedQuery Label → Bool
  | .reachable a b => decide (∃ x ∈ R.activeNodes, label x = a ∧
      ∃ y ∈ R.activeNodes, label y = b ∧ Reachable R x y)
  | .dependsOn a b => decide (∃ x ∈ R.activeNodes, label x = a ∧
      ∃ y ∈ R.activeNodes, label y = b ∧ Immediate R x y)
  | .currentlyWarranted a =>
      decide (liveView R.sigma (labelFamily label R closed a)).Nonempty
  | .hasAlternativeSupport a =>
      decide (2 ≤ (labelFamily label R closed a).card)

theorem reachable_iff_eval_true {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [DecidableEq Label]
    (label : Node → Label) (R : RawView U Node)
    (closed : Node → SupportFamily U.Token) (a b : Label) :
    evalQuery label R closed (.reachable a b) = true ↔
      ∃ x ∈ R.activeNodes, label x = a ∧
        ∃ y ∈ R.activeNodes, label y = b ∧ Reachable R x y := by
  simp [evalQuery]

theorem dependsOn_iff_eval_true {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [DecidableEq Label]
    (label : Node → Label) (R : RawView U Node)
    (closed : Node → SupportFamily U.Token) (a b : Label) :
    evalQuery label R closed (.dependsOn a b) = true ↔
      ∃ x ∈ R.activeNodes, label x = a ∧
        ∃ y ∈ R.activeNodes, label y = b ∧ Immediate R x y := by
  simp [evalQuery]

theorem currentlyWarranted_iff_eval_true
    {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [DecidableEq Label]
    (label : Node → Label) (R : RawView U Node)
    (closed : Node → SupportFamily U.Token) (a : Label) :
    evalQuery label R closed (.currentlyWarranted a) = true ↔
      (liveView R.sigma (labelFamily label R closed a)).Nonempty := by
  simp [evalQuery]

theorem hasAlternativeSupport_iff_eval_true
    {U : FiniteUniverse} {Node Label : Type u}
    [Fintype Node] [DecidableEq Node] [DecidableEq Label]
    (label : Node → Label) (R : RawView U Node)
    (closed : Node → SupportFamily U.Token) (a : Label) :
    evalQuery label R closed (.hasAlternativeSupport a) = true ↔
      2 ≤ (labelFamily label R closed a).card := by
  simp [evalQuery]

end CLC

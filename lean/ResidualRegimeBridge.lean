import Std
import BehaviouralCongruence

universe u v w

namespace ResidualRegimeBridge

open BehaviouralCongruence

variable {M : Type u} {X : Type v} {O : Type w}
variable (A : ActionMonoid M X) (obs : X → O)

/-- The verifier-visible consequence contributed by one continuation. -/
def KernelOf (c : M) (x y : X) : Prop :=
  obs (A.act c x) = obs (A.act c y)

/-- A live residual is a pair still identified by the current interface that a
    newly verified continuation distinguishes. -/
def Residual (B : List M) (c : M) : Prop :=
  ∃ x y, EqBy A obs B x y ∧ ¬ KernelOf A obs c x y

/-- A candidate repaired relation is justified exactly when it forgets no
    distinction forbidden by the old interface and makes the new continuation
    well defined observationally. -/
def AdmissibleRepair (B : List M) (c : M) (R : X → X → Prop) : Prop :=
  (∀ x y, R x y → EqBy A obs B x y) ∧
  (∀ x y, R x y → KernelOf A obs c x y)

/-- Exact intersection law for adjoining one verified continuation. -/
theorem eqBy_cons (B : List M) (c : M) (x y : X) :
    EqBy A obs (c :: B) x y ↔
      EqBy A obs B x y ∧ KernelOf A obs c x y := by
  constructor
  · intro h
    constructor
    · intro m hm
      exact h m (by simp [hm])
    · exact h c (by simp [KernelOf])
  · intro h m hm
    simp only [List.mem_cons] at hm
    rcases hm with rfl | hm
    · exact h.2
    · exact h.1 m hm

/-- The intersection repair is admissible. -/
theorem refined_admissible (B : List M) (c : M) :
    AdmissibleRepair A obs B c (EqBy A obs (c :: B)) := by
  constructor
  · intro x y h
    exact (eqBy_cons A obs B c x y).mp h |>.1
  · intro x y h
    exact (eqBy_cons A obs B c x y).mp h |>.2

/-- Universal property: every admissible repair refines the intersection
    repair. Thus adjoining the verified kernel is the coarsest justified
    change, with no coordinate choices or search heuristic involved. -/
theorem refined_is_coarsest (B : List M) (c : M)
    (R : X → X → Prop) (hR : AdmissibleRepair A obs B c R) :
    ∀ x y, R x y → EqBy A obs (c :: B) x y := by
  intro x y hxy
  exact (eqBy_cons A obs B c x y).mpr ⟨hR.1 x y hxy, hR.2 x y hxy⟩

/-- Any relation with the same universal property is extensionally identical
    to the canonical repair. This is uniqueness up to behavioural relation,
    rather than syntax or presentation. -/
theorem unique_coarsest_repair (B : List M) (c : M)
    (R : X → X → Prop)
    (hR : AdmissibleRepair A obs B c R)
    (hGreatest : ∀ S : X → X → Prop,
      AdmissibleRepair A obs B c S →
      ∀ x y, S x y → R x y) :
    ∀ x y, R x y ↔ EqBy A obs (c :: B) x y := by
  intro x y
  constructor
  · exact refined_is_coarsest A obs B c R hR x y
  · intro h
    exact hGreatest (EqBy A obs (c :: B))
      (refined_admissible A obs B c) x y h

/-- A live residual makes the canonical repair strict: at least one old
    identification is necessarily withdrawn. -/
theorem residual_forces_strict_refinement (B : List M) (c : M)
    (hρ : Residual A obs B c) :
    ∃ x y, EqBy A obs B x y ∧ ¬ EqBy A obs (c :: B) x y := by
  rcases hρ with ⟨x, y, hold, hsep⟩
  refine ⟨x, y, hold, ?_⟩
  intro href
  exact hsep ((eqBy_cons A obs B c x y).mp href).2

/-- The current retained continuation list always induces a setoid. -/
def eqBySetoid (B : List M) : Setoid X where
  r := EqBy A obs B
  iseqv := {
    refl := by
      intro x m hm
      rfl
    symm := by
      intro x y h m hm
      exact (h m hm).symm
    trans := by
      intro x y z hxy hyz m hm
      exact (hxy m hm).trans (hyz m hm)
  }

abbrev Interface (B : List M) := Quotient (eqBySetoid A obs B)

/-- Operational capability criterion: the consequence of continuation `c` can
    be executed on the quotient without recovering the discarded raw state. -/
def CanDescend (B : List M) (c : M) : Prop :=
  ∃ F : Interface A obs B → O,
    ∀ x : X,
      F (Quotient.mk (eqBySetoid A obs B) x) = obs (A.act c x)

/-- Descent is equivalent to respecting the current behavioural interface. -/
theorem canDescend_iff_respects (B : List M) (c : M) :
    CanDescend A obs B c ↔
      ∀ x y, EqBy A obs B x y → KernelOf A obs c x y := by
  constructor
  · rintro ⟨F, hF⟩ x y hxy
    have hq :
        Quotient.mk (eqBySetoid A obs B) x =
          Quotient.mk (eqBySetoid A obs B) y := Quotient.sound hxy
    calc
      obs (A.act c x) = F (Quotient.mk (eqBySetoid A obs B) x) := (hF x).symm
      _ = F (Quotient.mk (eqBySetoid A obs B) y) := congrArg F hq
      _ = obs (A.act c y) := hF y
  · intro h
    refine ⟨Quotient.lift (fun x : X => obs (A.act c x)) ?_, ?_⟩
    · intro x y hxy
      exact h x y hxy
    · intro x
      rfl

/-- A verifier residual is a certificate that the new continuation cannot
    lawfully descend through the old quotient. -/
theorem residual_blocks_old_capability (B : List M) (c : M)
    (hρ : Residual A obs B c) :
    ¬ CanDescend A obs B c := by
  intro hcap
  have hrespect := (canDescend_iff_respects A obs B c).mp hcap
  rcases hρ with ⟨x, y, hold, hsep⟩
  exact hsep (hrespect x y hold)

/-- After the unique coarsest repair, the formerly impossible continuation
    becomes lawful on the new quotient. -/
theorem repaired_enables_capability (B : List M) (c : M) :
    CanDescend A obs (c :: B) c := by
  apply (canDescend_iff_respects A obs (c :: B) c).mpr
  intro x y hxy
  exact (eqBy_cons A obs B c x y).mp hxy |>.2

/-- Single mechanized residual-to-regime bridge.

A certified residual simultaneously establishes:
1. the old quotient is too coarse;
2. intersection with the new verified kernel is a strict change;
3. that repair is the unique coarsest justified relation extension;
4. the continuation cannot descend before the repair;
5. it can descend after the repair;
6. exact ablation restores the old obstruction (the final conjunct repeats
   the old impossibility intentionally as the causal ablation statement).
-/
theorem residual_to_minimal_regime_and_capability
    (B : List M) (c : M) (hρ : Residual A obs B c) :
    (∃ x y, EqBy A obs B x y ∧ ¬ EqBy A obs (c :: B) x y) ∧
    (∀ R : X → X → Prop,
      AdmissibleRepair A obs B c R →
      ∀ x y, R x y → EqBy A obs (c :: B) x y) ∧
    (¬ CanDescend A obs B c) ∧
    CanDescend A obs (c :: B) c ∧
    (¬ CanDescend A obs B c) := by
  refine ⟨residual_forces_strict_refinement A obs B c hρ, ?_,
    residual_blocks_old_capability A obs B c hρ,
    repaired_enables_capability A obs B c,
    residual_blocks_old_capability A obs B c hρ⟩
  intro R hR
  exact refined_is_coarsest A obs B c R hR

end ResidualRegimeBridge

import Std

namespace FailureGeneratedOmegaPlusOne

/-- Worlds have an open finite observation stream and one operational mode that
    is not named by any finite coordinate. -/
abbrev World := Nat × Bool
abbrev Probe := World → Prop

def coord (k : Nat) : Probe := fun w => w.1.testBit k = true

/-- A stage retains coordinate probes and any probes generated from certified
    failures.  The latter are arbitrary semantic probes, not ordinal tags. -/
structure Stage where
  coords : Nat → Prop
  generated : Probe → Prop

@[ext] theorem Stage.ext {A B : Stage}
    (hcoords : A.coords = B.coords)
    (hgenerated : A.generated = B.generated) : A = B := by
  cases A
  cases B
  simp_all

def observes (C : Stage) (p : Probe) : Prop :=
  (∃ k, C.coords k ∧ p = coord k) ∨ C.generated p

def agrees (C : Stage) (x y : World) : Prop :=
  ∀ p, observes C p → (p x ↔ p y)

/-- A verifier-certified representation failure: the current observations
    identify two genuinely distinct worlds. -/
structure Failure (C : Stage) where
  left : World
  right : World
  distinct : left ≠ right
  invisible : agrees C left right

/-- Generic failure-to-consequence genesis.  The probe is computed from the
    runtime failure endpoint; no post-limit constructor or ordinal coordinate
    occurs in the probe language. -/
def generatedProbe {C : Stage} (r : Failure C) : Probe :=
  fun z => z = r.right

def reachable (C : Stage) (k : Nat) : Prop :=
  ∀ j, j < k → C.coords j

def coordinateResidual (C : Stage) (k : Nat) : Prop :=
  ∃ x y, agrees C x y ∧ (coord k x ↔ ¬ coord k y)

def completeCoordinateFamily (C : Stage) : Prop :=
  ∀ k, C.coords k

/-- One frozen developmental law.  Its finite clause is the existing
    residual-gated coordinate refinement.  Its semantic-closure clause does
    not name a successor of omega: once the generated family is complete, it
    converts every verifier-certified invisible distinction into its canonical
    singleton consequence. -/
def develop (C : Stage) : Stage where
  coords := fun k => C.coords k ∨
    (reachable C k ∧ coordinateResidual C k)
  generated := fun p => C.generated p ∨
    (completeCoordinateFamily C ∧ ∃ r : Failure C, p = generatedProbe r)

def finiteStage (n : Nat) : Stage where
  coords := fun k => k < n
  generated := fun _ => False

def omegaStage : Stage where
  coords := fun _ => True
  generated := fun _ => False

def omegaPlusOneStage : Stage := develop omegaStage

theorem finite_agrees_of_same_value {n a : Nat} (x y : Bool) :
    agrees (finiteStage n) (a, x) (a, y) := by
  intro p hp
  rcases hp with ⟨k, _, rfl⟩ | h
  · simp [coord]
  · exact False.elim h

theorem finite_coordinate_residual (n : Nat) :
    coordinateResidual (finiteStage n) n := by
  refine ⟨(0, false), (2 ^ n, false), ?_, ?_⟩
  · intro p hp
    rcases hp with ⟨k, hk, rfl⟩ | h
    · have hne : n ≠ k := (Nat.ne_of_lt hk).symm
      simp [coord, Nat.testBit_two_pow_of_ne hne]
    · exact False.elim h
  · simp [coord]

theorem reachable_finite_le {n k : Nat}
    (h : reachable (finiteStage n) k) : k ≤ n := by
  apply Nat.le_of_not_gt
  intro hnk
  exact (Nat.lt_irrefl n) (h n hnk)

theorem finite_not_complete (n : Nat) :
    ¬ completeCoordinateFamily (finiteStage n) := by
  intro h
  exact (Nat.lt_irrefl n) (h n)

theorem develop_finite_step (n : Nat) :
    develop (finiteStage n) = finiteStage (n + 1) := by
  cases n with
  | zero =>
      apply Stage.ext
      · funext k
        apply propext
        constructor
        · intro h
          rcases h with h | ⟨hr, _⟩
          · exact False.elim h
          · have hk : k ≤ 0 := reachable_finite_le hr
            simpa using hk
        · intro hk
          have : k = 0 := Nat.eq_zero_of_le_zero (Nat.lt_one_iff.mp hk)
          subst k
          exact Or.inr ⟨fun j hj => False.elim (Nat.not_lt_zero j hj),
            finite_coordinate_residual 0⟩
      · funext p
        apply propext
        simp [develop, finiteStage, finite_not_complete]
  | succ n =>
      apply Stage.ext
      · funext k
        apply propext
        constructor
        · intro h
          rcases h with hk | ⟨hr, _⟩
          · exact Nat.lt_succ_of_lt hk
          · exact Nat.lt_succ_iff.mpr (reachable_finite_le hr)
        · intro hk
          have hle : k ≤ n + 1 := Nat.lt_succ_iff.mp hk
          rcases Nat.lt_or_eq_of_le hle with hlt | rfl
          · exact Or.inl hlt
          · exact Or.inr ⟨fun j hj => hj, finite_coordinate_residual (n + 1)⟩
      · funext p
        apply propext
        simp [develop, finiteStage, finite_not_complete]

def iterate : Nat → Stage
  | 0 => finiteStage 0
  | n + 1 => develop (iterate n)

theorem iterate_eq_finiteStage (n : Nat) : iterate n = finiteStage n := by
  induction n with
  | zero => rfl
  | succ n ih => rw [iterate, ih, develop_finite_step]

def finiteSup : Stage where
  coords := fun k => ∃ n, (iterate n).coords k
  generated := fun p => ∃ n, (iterate n).generated p

theorem finiteSup_eq_omega : finiteSup = omegaStage := by
  apply Stage.ext
  · funext k
    apply propext
    constructor
    · intro _; trivial
    · intro _
      refine ⟨k + 1, ?_⟩
      rw [iterate_eq_finiteStage]
      simp [finiteStage]
  · funext p
    apply propext
    constructor
    · rintro ⟨n, hn⟩
      rw [iterate_eq_finiteStage] at hn
      exact False.elim hn
    · intro h
      exact False.elim h

def toggle (w : World) : World := (w.1, !w.2)

theorem toggle_ne (w : World) : toggle w ≠ w := by
  intro h
  have hb := congrArg Prod.snd h
  simp [toggle] at hb

def omegaFailure (w : World) : Failure omegaStage where
  left := toggle w
  right := w
  distinct := toggle_ne w
  invisible := by
    intro p hp
    rcases hp with ⟨k, _, rfl⟩ | h
    · simp [coord, toggle]
    · exact False.elim h

theorem omega_failure_for_every_target (w : World) :
    Nonempty (Failure omegaStage) := ⟨omegaFailure w⟩

theorem omega_generates_every_singleton (w : World) :
    (omegaPlusOneStage.generated (fun z => z = w)) := by
  exact Or.inr ⟨fun _ => trivial, ⟨omegaFailure w, rfl⟩⟩

theorem omega_not_fixed : develop omegaStage ≠ omegaStage := by
  intro h
  have hp := congrArg (fun C => C.generated (fun z => z = (0, false))) h
  have hnew := omega_generates_every_singleton (0, false)
  have : ¬ omegaStage.generated (fun z => z = (0, false)) := by
    simp [omegaStage]
  exact this (hp ▸ hnew)

theorem omegaPlusOne_agrees_implies_eq {x y : World}
    (h : agrees omegaPlusOneStage x y) : x = y := by
  have hs := h (fun z => z = y)
    (Or.inr (omega_generates_every_singleton y))
  exact (hs.mpr rfl)

theorem no_failure_after_omegaPlusOne :
    ¬ Nonempty (Failure omegaPlusOneStage) := by
  rintro ⟨r⟩
  exact r.distinct (omegaPlusOne_agrees_implies_eq r.invisible)

theorem omegaPlusOne_fixed :
    develop omegaPlusOneStage = omegaPlusOneStage := by
  apply Stage.ext
  · funext k
    apply propext
    simp [develop, omegaPlusOneStage, omegaStage]
  · funext p
    apply propext
    constructor
    · intro h
      rcases h with h | ⟨_, ⟨r⟩⟩
      · exact h
      · exact False.elim (no_failure_after_omegaPlusOne ⟨r⟩)
    · exact Or.inl

def developWithoutFailureGenesis (C : Stage) : Stage where
  coords := (develop C).coords
  generated := C.generated

theorem generation_ablation_restores_omega_fixed :
    developWithoutFailureGenesis omegaStage = omegaStage := by
  apply Stage.ext
  · funext k
    apply propext
    simp [developWithoutFailureGenesis, develop, omegaStage]
  · rfl

theorem no_post_limit_probe_at_finite_stage (n : Nat) (p : Probe) :
    ¬ (iterate n).generated p := by
  rw [iterate_eq_finiteStage]
  exact id

def ClosureExactlyOneBeyondFiniteSup : Prop :=
  (∀ n, develop (iterate n) ≠ iterate n) ∧
  finiteSup = omegaStage ∧
  develop omegaStage ≠ omegaStage ∧
  develop (develop omegaStage) = develop omegaStage

theorem failure_generated_closure_exactly_one_beyond_finite_sup :
    ClosureExactlyOneBeyondFiniteSup := by
  refine ⟨?_, finiteSup_eq_omega, omega_not_fixed, omegaPlusOne_fixed⟩
  intro n
  rw [iterate_eq_finiteStage, develop_finite_step]
  intro h
  have hk := congrArg (fun C => C.coords n) h
  simp [finiteStage] at hk

#check develop_finite_step
#check iterate_eq_finiteStage
#check finiteSup_eq_omega
#check no_post_limit_probe_at_finite_stage
#check omega_generates_every_singleton
#check omega_not_fixed
#check no_failure_after_omegaPlusOne
#check omegaPlusOne_fixed
#check generation_ablation_restores_omega_fixed
#check failure_generated_closure_exactly_one_beyond_finite_sup

end FailureGeneratedOmegaPlusOne

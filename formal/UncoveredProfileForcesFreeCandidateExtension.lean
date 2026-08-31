namespace UncoveredProfileForcesFreeCandidateExtension

universe u v w

/-- A verifier profile is realized when some current raw candidate has exactly
    that operational behavior. -/
def Realized {H : Type u} {C : Type v}
    (V : H → C → Bool) (p : C → Bool) : Prop :=
  ∃ h : H, V h = p

/-- Certified residual: the required operational profile has no representative
    in the current raw candidate carrier. -/
structure CoverageGap {H : Type u} {C : Type v} (V : H → C → Bool) where
  target : C → Bool
  uncovered : ¬ Realized V target

/-- Free one-witness extension of the raw candidate carrier.  The new point has
    no privileged syntax beyond being the unique newly adjoined generator. -/
abbrev Extend (H : Type u) := Sum H Unit

/-- Old candidates retain their exact verifier behavior; the one new witness
    realizes precisely the residual-required profile. -/
def extendVerifier {H : Type u} {C : Type v}
    (V : H → C → Bool) (target : C → Bool) : Extend H → C → Bool
  | .inl h => V h
  | .inr _ => target

def newWitness {H : Type u} : Extend H := Sum.inr ()

theorem old_behavior_preserved {H : Type u} {C : Type v}
    (V : H → C → Bool) (target : C → Bool) (h : H) :
    extendVerifier V target (.inl h) = V h := by
  rfl

theorem new_witness_realizes_target {H : Type u} {C : Type v}
    (V : H → C → Bool) (target : C → Bool) :
    extendVerifier V target (newWitness : Extend H) = target := by
  rfl

/-- Exact operational image law: the extension adds no behavioral profile other
    than the demanded one. -/
theorem realized_after_extension_iff {H : Type u} {C : Type v}
    (V : H → C → Bool) (target p : C → Bool) :
    Realized (extendVerifier V target) p ↔ Realized V p ∨ p = target := by
  constructor
  · rintro ⟨x, hx⟩
    cases x with
    | inl h =>
        exact Or.inl ⟨h, hx⟩
    | inr unit =>
        cases unit
        exact Or.inr hx.symm
  · intro h
    rcases h with ⟨h, hp⟩ | hp
    · exact ⟨Sum.inl h, hp⟩
    · exact ⟨newWitness, hp.symm⟩

/-- If the profile was uncovered before, the newly adjoined witness is genuinely
    necessary: no old candidate realizes it. -/
theorem no_old_candidate_realizes_gap {H : Type u} {C : Type v}
    {V : H → C → Bool} (r : CoverageGap V) :
    ¬ Realized V r.target := by
  exact r.uncovered

/-- The gap is repaired by exactly one-point carrier extension. -/
theorem gap_repaired_by_free_witness {H : Type u} {C : Type v}
    {V : H → C → Bool} (r : CoverageGap V) :
    Realized (extendVerifier V r.target) r.target := by
  exact ⟨newWitness, rfl⟩

/-- Canonical lift from the free extension into any carrier supplied with an
    interpretation of all old candidates and one chosen realization of the new
    generator. -/
def lift {H : Type u} {K : Type w} (f : H → K) (knew : K) : Extend H → K
  | .inl h => f h
  | .inr _ => knew

theorem lift_old {H : Type u} {K : Type w}
    (f : H → K) (knew : K) (h : H) :
    lift f knew (.inl h) = f h := by
  rfl

theorem lift_new {H : Type u} {K : Type w}
    (f : H → K) (knew : K) :
    lift f knew (newWitness : Extend H) = knew := by
  rfl

/-- Uniqueness part of the free one-point extension. -/
theorem lift_unique {H : Type u} {K : Type w}
    (f : H → K) (knew : K) (g : Extend H → K)
    (hold : ∀ h, g (.inl h) = f h)
    (hnew : g newWitness = knew) :
    g = lift f knew := by
  funext x
  cases x with
  | inl h => exact hold h
  | inr unit =>
      cases unit
      exact hnew

/-- Semantic universal property: any alternative carrier that preserves every
    old verifier profile and contains a witness for the required profile receives
    the canonical behavior-preserving map from the free extension. -/
theorem lift_preserves_verifier {H : Type u} {C : Type v} {K : Type w}
    (V : H → C → Bool) (target : C → Bool)
    (W : K → C → Bool) (f : H → K) (knew : K)
    (hold : ∀ h, W (f h) = V h)
    (hnew : W knew = target) :
    ∀ x : Extend H,
      W (lift f knew x) = extendVerifier V target x := by
  intro x
  cases x with
  | inl h => exact hold h
  | inr unit =>
      cases unit
      exact hnew

/-- Concrete coverage collapse: a raw carrier with only constant Boolean
    candidates cannot realize negation. -/
def currentVerifier : Bool → Bool → Bool
  | false, _ => false
  | true, _ => true

def requiredProfile : Bool → Bool := fun b => !b

theorem required_profile_uncovered :
    ¬ Realized currentVerifier requiredProfile := by
  rintro ⟨h, hh⟩
  cases h with
  | false =>
      have hp := congrFun hh false
      simp [currentVerifier, requiredProfile] at hp
  | true =>
      have hp := congrFun hh true
      simp [currentVerifier, requiredProfile] at hp

def coverageGap : CoverageGap currentVerifier where
  target := requiredProfile
  uncovered := required_profile_uncovered

/-- Main result: exact hidden raw syntax is not reconstructed.  An uncovered
    verifier profile instead forces the canonical free one-witness carrier
    extension.  Its operational image is exactly the old image plus the required
    profile, and it is universal among all one-witness repairs.

    Remaining scaffold: the one-point-extension meta-constructor and verifier
    context family are supplied. -/
theorem uncovered_profile_forces_free_candidate_extension :
    (¬ Realized currentVerifier coverageGap.target) ∧
    Realized (extendVerifier currentVerifier coverageGap.target) coverageGap.target ∧
    (∀ p : Bool → Bool,
      Realized (extendVerifier currentVerifier coverageGap.target) p ↔
        Realized currentVerifier p ∨ p = coverageGap.target) := by
  exact ⟨
    coverageGap.uncovered,
    gap_repaired_by_free_witness coverageGap,
    realized_after_extension_iff currentVerifier coverageGap.target⟩

#check realized_after_extension_iff
#check no_old_candidate_realizes_gap
#check gap_repaired_by_free_witness
#check lift_unique
#check lift_preserves_verifier
#check required_profile_uncovered
#check uncovered_profile_forces_free_candidate_extension

end UncoveredProfileForcesFreeCandidateExtension

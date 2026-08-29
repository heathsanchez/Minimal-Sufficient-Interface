import Std
import VerifiedConstructorFamilyGenesis

universe u v w z

namespace FiniteMetaLanguageExhaustion

open VerifiedConstructorFamilyGenesis

variable {X : Type u} {Ctor : Type v} {View : Type w} {Y : Type z}

/-- A finite executable meta-language is represented extensionally by the list of
    constructors it can generate in the frozen regime. -/
def GeneratedBy (G : List Ctor) (c : Ctor) : Prop := c ∈ G

/-- The supplied generated family is exhausted when every constructor it can emit
    is residually rejected by the protected verifier. -/
def MetaLanguageExhausted
    (G : List Ctor)
    (view : Ctor → X → View)
    (target : X → Y) : Prop :=
  ∀ c, c ∈ G → ResidualRejects view target c

/-- Exhaustion is stronger than search failure: no constructor in the entire frozen
    generated family can be sufficient for the protected consequence. -/
theorem exhausted_family_has_no_sufficient_constructor
    (G : List Ctor)
    (view : Ctor → X → View)
    (target : X → Y)
    (hexh : MetaLanguageExhausted G view target) :
    ∀ c, c ∈ G → ¬ FamilySufficient view target c := by
  intro c hc
  exact (not_sufficient_iff_residual_rejects view target c).2 (hexh c hc)

/-- Any meta-generator whose outputs are all contained in an exhausted finite family
    inherits the impossibility certificate. -/
theorem generated_candidate_cannot_solve_after_exhaustion
    {Seed : Type u}
    (generate : Seed → Ctor)
    (G : List Ctor)
    (view : Ctor → X → View)
    (target : X → Y)
    (hcovered : ∀ s, generate s ∈ G)
    (hexh : MetaLanguageExhausted G view target) :
    ∀ s, ¬ FamilySufficient view target (generate s) := by
  intro s
  exact exhausted_family_has_no_sufficient_constructor G view target hexh (generate s) (hcovered s)

/-- Conversely, a generated constructor that is sufficient witnesses strict failure
    of the exhaustion certificate. -/
theorem sufficient_generated_constructor_refutes_exhaustion
    (G : List Ctor)
    (view : Ctor → X → View)
    (target : X → Y)
    (c : Ctor)
    (hc : c ∈ G)
    (hs : FamilySufficient view target c) :
    ¬ MetaLanguageExhausted G view target := by
  intro hexh
  have hnot : ¬ FamilySufficient view target c :=
    exhausted_family_has_no_sufficient_constructor G view target hexh c hc
  exact hnot hs

/-- A one-step generated-family extension is verifier-licensed when the old generated
    family is exhausted and the new constructor is sufficient. The theorem does not
    claim how the new constructor was invented; it certifies why remaining inside the
    old meta-language is no longer an information-gaining move. -/
def LicensedBeyondMetaLanguage
    (G : List Ctor)
    (view : Ctor → X → View)
    (target : X → Y)
    (newCtor : Ctor) : Prop :=
  MetaLanguageExhausted G view target ∧
  FamilySufficient view target newCtor ∧
  newCtor ∉ G

/-- Under a licensed beyond-meta-language witness, old search is globally blocked
    relative to the frozen generated family while the admitted new constructor solves
    the protected sufficiency obligation. -/
theorem licensed_extension_is_strict_meta_language_gain
    (G : List Ctor)
    (view : Ctor → X → View)
    (target : X → Y)
    (newCtor : Ctor)
    (h : LicensedBeyondMetaLanguage G view target newCtor) :
    (∀ c, c ∈ G → ¬ FamilySufficient view target c) ∧
    FamilySufficient view target newCtor ∧
    newCtor ∉ G := by
  exact ⟨exhausted_family_has_no_sufficient_constructor G view target h.1,
    h.2.1, h.2.2⟩

/-- Exact ablation statement: deleting the only admitted beyond-family constructor
    leaves the system inside the exhausted old family, where every available generated
    constructor remains residually inadequate. -/
theorem meta_language_ablation_restores_exhaustion
    (G : List Ctor)
    (view : Ctor → X → View)
    (target : X → Y)
    (newCtor : Ctor)
    (h : LicensedBeyondMetaLanguage G view target newCtor) :
    MetaLanguageExhausted G view target := by
  exact h.1

end FiniteMetaLanguageExhaustion

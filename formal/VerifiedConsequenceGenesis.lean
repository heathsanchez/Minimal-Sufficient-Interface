namespace VerifiedConsequenceGenesis

universe u v w

/-- A family of protected consequences. `C c` means consequence `c` is protected. -/
def ConseqEq {X : Type u} {Y : Type v}
    (C : (X → Y) → Prop) (x y : X) : Prop :=
  ∀ c : X → Y, C c → c x = c y

/-- Consequential identity is always reflexive. -/
theorem conseqEq_refl {X : Type u} {Y : Type v}
    (C : (X → Y) → Prop) (x : X) : ConseqEq C x x := by
  intro c hc
  rfl

/-- Consequential identity is symmetric. -/
theorem conseqEq_symm {X : Type u} {Y : Type v}
    (C : (X → Y) → Prop) {x y : X} :
    ConseqEq C x y → ConseqEq C y x := by
  intro h c hc
  exact (h c hc).symm

/-- Consequential identity is transitive. -/
theorem conseqEq_trans {X : Type u} {Y : Type v}
    (C : (X → Y) → Prop) {x y z : X} :
    ConseqEq C x y → ConseqEq C y z → ConseqEq C x z := by
  intro hxy hyz c hc
  exact (hxy c hc).trans (hyz c hc)

/-- A representation preserves protected consequences when equality in the
representation never identifies states with different protected futures. -/
def Preserves {X : Type u} {Y : Type v} {R : Type w}
    (C : (X → Y) → Prop) (q : X → R) : Prop :=
  ∀ x y : X, q x = q y → ConseqEq C x y

/-- Coarsest-preserving law.

Any representation preserving all protected consequences must refine
consequential identity: whenever it identifies x and y, x and y are
consequentially identical. Thus `ConseqEq C` is the largest/coarsest
admissible identification relation. -/
theorem consequential_identity_is_coarsest
    {X : Type u} {Y : Type v} {R : Type w}
    (C : (X → Y) → Prop) (q : X → R) (hq : Preserves C q) :
    ∀ x y : X, q x = q y → ConseqEq C x y := by
  exact hq

/-- A separator is a constructive certificate that the current relation is
strictly too coarse for a newly protected consequence. -/
theorem separator_refutes_identification
    {X : Type u} {Y : Type v}
    (C : (X → Y) → Prop) (c : X → Y) {x y : X}
    (_hold : ConseqEq C x y) (hsep : c x ≠ c y) :
    ¬ ConseqEq (fun d => C d ∨ d = c) x y := by
  intro h
  exact hsep (h c (Or.inr rfl))

/-- Golden refinement law: adding one protected consequence refines the old
identity by intersecting it with the kernel of that consequence. -/
theorem golden_refinement
    {X : Type u} {Y : Type v}
    (C : (X → Y) → Prop) (c : X → Y) (x y : X) :
    ConseqEq (fun d => C d ∨ d = c) x y ↔
      ConseqEq C x y ∧ c x = c y := by
  constructor
  · intro h
    constructor
    · intro d hd
      exact h d (Or.inl hd)
    · exact h c (Or.inr rfl)
  · rintro ⟨hC, hc⟩ d hd
    cases hd with
    | inl hCd => exact hC d hCd
    | inr hdc => simpa [hdc] using hc

/-- A consequence factors through a representation `q` when it can be computed
from the representation alone. -/
def FactorsThrough {X : Type u} {Y : Type v} {R : Type w}
    (q : X → R) (c : X → Y) : Prop :=
  ∃ cbar : R → Y, ∀ x : X, c x = cbar (q x)

/-- Any factorized consequence is constant on every fiber of the representation. -/
theorem factorsThrough_implies_fiber_constancy
    {X : Type u} {Y : Type v} {R : Type w}
    (q : X → R) (c : X → Y) :
    FactorsThrough q c → ∀ x y : X, q x = q y → c x = c y := by
  rintro ⟨cbar, hfactor⟩ x y hq
  calc
    c x = cbar (q x) := hfactor x
    _ = cbar (q y) := by rw [hq]
    _ = c y := (hfactor y).symm

/-- A single consequential separator inside a fiber certifies non-factorization. -/
theorem separator_implies_nonfactorization
    {X : Type u} {Y : Type v} {R : Type w}
    (q : X → R) (c : X → Y) {x y : X}
    (hcollapse : q x = q y) (hsep : c x ≠ c y) :
    ¬ FactorsThrough q c := by
  intro hf
  exact hsep (factorsThrough_implies_fiber_constancy q c hf x y hcollapse)

/-- Converse factorization theorem on the actually represented states.

If every fiber of `q` is consequence-constant and every representation state
has a chosen preimage, then the consequence factors through `q`.
The explicit section assumption isolates the only choice/surjectivity content. -/
theorem fiber_constancy_implies_factorsThrough_of_section
    {X : Type u} {Y : Type v} {R : Type w}
    (q : X → R) (c : X → Y)
    (s : R → X) (hs : ∀ r : R, q (s r) = r)
    (hconst : ∀ x y : X, q x = q y → c x = c y) :
    FactorsThrough q c := by
  refine ⟨fun r => c (s r), ?_⟩
  intro x
  exact hconst x (s (q x)) (hs (q x)).symm

/-- Exact factorization criterion when a section of the representation is available. -/
theorem factorsThrough_iff_fiber_constancy_of_section
    {X : Type u} {Y : Type v} {R : Type w}
    (q : X → R) (c : X → Y)
    (s : R → X) (hs : ∀ r : R, q (s r) = r) :
    FactorsThrough q c ↔
      ∀ x y : X, q x = q y → c x = c y := by
  constructor
  · exact factorsThrough_implies_fiber_constancy q c
  · exact fiber_constancy_implies_factorsThrough_of_section q c s hs

/-- Canonical consequential refinement: retain the old representation and add
exactly the newly required consequence as one extra coordinate. -/
def RefineWith {X : Type u} {Y : Type v} {R : Type w}
    (q : X → R) (c : X → Y) : X → R × Y :=
  fun x => (q x, c x)

/-- The newly protected consequence factors through the canonical refinement. -/
theorem consequence_factors_through_refinement
    {X : Type u} {Y : Type v} {R : Type w}
    (q : X → R) (c : X → Y) :
    FactorsThrough (RefineWith q c) c := by
  refine ⟨Prod.snd, ?_⟩
  intro x
  rfl

/-- The canonical refinement never forgets distinctions already present in q. -/
theorem refinement_preserves_old_representation
    {X : Type u} {Y : Type v} {R : Type w}
    (q : X → R) (c : X → Y) :
    ∀ x y : X, RefineWith q c x = RefineWith q c y → q x = q y := by
  intro x y h
  exact congrArg Prod.fst h

/-- The canonical refinement separates any previously collapsed pair whose
new consequence differs. -/
theorem refinement_separates_witness
    {X : Type u} {Y : Type v} {R : Type w}
    (q : X → R) (c : X → Y) {x y : X}
    (_hcollapse : q x = q y) (hsep : c x ≠ c y) :
    RefineWith q c x ≠ RefineWith q c y := by
  intro h
  exact hsep (congrArg Prod.snd h)

/-- Central developmental theorem.

A verified separator proves that the new consequence cannot factor through the
current representation. The canonical one-coordinate refinement preserves the
old representation, strictly separates the witness pair, and restores
factorization of the failed consequence. -/
theorem factorization_failure_forces_and_refinement_restores
    {X : Type u} {Y : Type v} {R : Type w}
    (q : X → R) (c : X → Y) {x y : X}
    (hcollapse : q x = q y) (hsep : c x ≠ c y) :
    (¬ FactorsThrough q c) ∧
    FactorsThrough (RefineWith q c) c ∧
    (∀ a b : X, RefineWith q c a = RefineWith q c b → q a = q b) ∧
    RefineWith q c x ≠ RefineWith q c y := by
  constructor
  · exact separator_implies_nonfactorization q c hcollapse hsep
  constructor
  · exact consequence_factors_through_refinement q c
  constructor
  · exact refinement_preserves_old_representation q c
  · exact refinement_separates_witness q c hcollapse hsep

/-- A minimal language model for recursive promotion. `L a` says atom `a` is
currently available. -/
abbrev Lang (A : Type u) := A → Prop

def Promote {A : Type u} (L : Lang A) (a : A) : Lang A :=
  fun x => L x ∨ x = a

/-- Generic expressions constructed from available atoms. -/
inductive Expr (A : Type u) where
  | atom : A → Expr A
  | op : Expr A → Expr A
  deriving Repr

/-- Expressibility is structural: an atom must already be in the language;
operators can only act on expressible subexpressions. -/
inductive Expressible {A : Type u} (L : Lang A) : Expr A → Prop where
  | atom {a : A} : L a → Expressible L (.atom a)
  | op {e : Expr A} : Expressible L e → Expressible L (.op e)

/-- Promotion immediately makes the verified object available as a new atom. -/
theorem promoted_atom_expressible {A : Type u} (L : Lang A) (o1 : A) :
    Expressible (Promote L o1) (.atom o1) := by
  apply Expressible.atom
  exact Or.inr rfl

/-- Recursive promotion law: once O1 is promoted, a genuinely new expression
built from O1 becomes expressible. -/
theorem promotion_enables_descendant {A : Type u} (L : Lang A) (o1 : A) :
    Expressible (Promote L o1) (.op (.atom o1)) := by
  apply Expressible.op
  exact promoted_atom_expressible L o1

/-- Exact ancestral ablation: if O1 was not already available, removing its
promotion makes the descendant expression impossible to express. -/
theorem ancestral_ablation_blocks_descendant
    {A : Type u} (L : Lang A) (o1 : A) (hmissing : ¬ L o1) :
    ¬ Expressible L (.op (.atom o1)) := by
  intro h
  cases h with
  | op hatom =>
      cases hatom with
      | atom hL => exact hmissing hL

/-- Strict promotion corollary: under the ancestral-missing hypothesis, the
same descendant is unreachable before promotion and reachable after it. -/
theorem strict_promotion_changes_expressible_frontier
    {A : Type u} (L : Lang A) (o1 : A) (hmissing : ¬ L o1) :
    (¬ Expressible L (.op (.atom o1))) ∧
      Expressible (Promote L o1) (.op (.atom o1)) := by
  constructor
  · exact ancestral_ablation_blocks_descendant L o1 hmissing
  · exact promotion_enables_descendant L o1

/-- Two-stage causal lineage theorem. If O1 is absent initially, then a
verified promotion of O1 strictly enlarges the expressible frontier by making
a descendant O2 := op(O1) available; exact removal of the ancestor removes O2.
This is the theorem-level core instantiated by V12's O1→O2 lineage. -/
theorem verified_promotion_has_ancestral_necessity
    {A : Type u} (L : Lang A) (o1 : A) (hmissing : ¬ L o1) :
    let O2 : Expr A := .op (.atom o1)
    Expressible (Promote L o1) O2 ∧ ¬ Expressible L O2 := by
  dsimp
  constructor
  · exact promotion_enables_descendant L o1
  · exact ancestral_ablation_blocks_descendant L o1 hmissing

end VerifiedConsequenceGenesis

#check VerifiedConsequenceGenesis.consequential_identity_is_coarsest
#check VerifiedConsequenceGenesis.separator_refutes_identification
#check VerifiedConsequenceGenesis.golden_refinement
#check VerifiedConsequenceGenesis.factorsThrough_implies_fiber_constancy
#check VerifiedConsequenceGenesis.separator_implies_nonfactorization
#check VerifiedConsequenceGenesis.factorsThrough_iff_fiber_constancy_of_section
#check VerifiedConsequenceGenesis.consequence_factors_through_refinement
#check VerifiedConsequenceGenesis.factorization_failure_forces_and_refinement_restores
#check VerifiedConsequenceGenesis.strict_promotion_changes_expressible_frontier
#check VerifiedConsequenceGenesis.verified_promotion_has_ancestral_necessity

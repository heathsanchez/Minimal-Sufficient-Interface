namespace MinimalBipartiteConsequenceInterface

/-- A completely generic interaction table.  `I` and `O` are raw context/outcome
    carriers and `V` is an arbitrary observable result type. -/
structure Interaction (I O V : Type) where
  eval : I → O → V

/-- A context is retained only by its complete action profile on current outcomes. -/
def RowProfile {I O V : Type} (M : Interaction I O V) (i : I) : O → V :=
  fun o => M.eval i o

/-- An outcome is retained only by its complete response profile across current contexts. -/
def ColProfile {I O V : Type} (M : Interaction I O V) (o : O) : I → V :=
  fun i => M.eval i o

/-- Realized row profiles: the operational context carrier. -/
def RowImage {I O V : Type} (M : Interaction I O V) : (O → V) → Prop :=
  fun p => ∃ i : I, RowProfile M i = p

def RowCarrier {I O V : Type} (M : Interaction I O V) :=
  {p : O → V // RowImage M p}

/-- Realized column profiles: the operational outcome carrier. -/
def ColImage {I O V : Type} (M : Interaction I O V) : (I → V) → Prop :=
  fun p => ∃ o : O, ColProfile M o = p

def ColCarrier {I O V : Type} (M : Interaction I O V) :=
  {p : I → V // ColImage M p}

/-- Canonical maps discard raw labels and retain only consequence profiles. -/
def induceRow {I O V : Type} (M : Interaction I O V) (i : I) : RowCarrier M :=
  ⟨RowProfile M i, ⟨i, rfl⟩⟩

def induceCol {I O V : Type} (M : Interaction I O V) (o : O) : ColCarrier M :=
  ⟨ColProfile M o, ⟨o, rfl⟩⟩

/-- The induced row representation reproduces every current interaction result. -/
def rowEval {I O V : Type} {M : Interaction I O V}
    (r : RowCarrier M) (o : O) : V := r.1 o

theorem row_carrier_sufficient {I O V : Type} (M : Interaction I O V)
    (i : I) (o : O) :
    rowEval (induceRow M i) o = M.eval i o := by
  rfl

/-- The induced column representation reproduces every current interaction result. -/
def colEval {I O V : Type} {M : Interaction I O V}
    (c : ColCarrier M) (i : I) : V := c.1 i

theorem col_carrier_sufficient {I O V : Type} (M : Interaction I O V)
    (i : I) (o : O) :
    colEval (induceCol M o) i = M.eval i o := by
  rfl

/-- Operational row identity is exactly observational equivalence on all outcomes. -/
theorem row_eq_iff_observationally_equal {I O V : Type}
    (M : Interaction I O V) (i j : I) :
    induceRow M i = induceRow M j ↔ ∀ o : O, M.eval i o = M.eval j o := by
  constructor
  · intro h o
    have hp : RowProfile M i = RowProfile M j := congrArg Subtype.val h
    exact congrFun hp o
  · intro h
    apply Subtype.ext
    funext o
    exact h o

/-- Operational column identity is exactly observational equivalence across all contexts. -/
theorem col_eq_iff_observationally_equal {I O V : Type}
    (M : Interaction I O V) (a b : O) :
    induceCol M a = induceCol M b ↔ ∀ i : I, M.eval i a = M.eval i b := by
  constructor
  · intro h i
    have hp : ColProfile M a = ColProfile M b := congrArg Subtype.val h
    exact congrFun hp i
  · intro h
    apply Subtype.ext
    funext i
    exact h i

/-- No realized operational row is lost. -/
theorem induce_row_surjective {I O V : Type} (M : Interaction I O V) :
    ∀ r : RowCarrier M, ∃ i : I, induceRow M i = r := by
  intro r
  rcases r.2 with ⟨i, hi⟩
  refine ⟨i, ?_⟩
  apply Subtype.ext
  exact hi

/-- No realized operational column is lost. -/
theorem induce_col_surjective {I O V : Type} (M : Interaction I O V) :
    ∀ c : ColCarrier M, ∃ o : O, induceCol M o = c := by
  intro c
  rcases c.2 with ⟨o, ho⟩
  refine ⟨o, ?_⟩
  apply Subtype.ext
  exact ho

/-- Any encoding sufficient to reproduce every interaction must preserve every
    consequence-visible context distinction. -/
theorem every_row_sufficient_encoding_preserves_visible_distinctions
    {I O V E : Type} (M : Interaction I O V)
    (encode : I → E) (decode : E → O → V)
    (sufficient : ∀ i o, decode (encode i) o = M.eval i o)
    {i j : I} (o : O) (hdiff : M.eval i o ≠ M.eval j o) :
    encode i ≠ encode j := by
  intro h
  apply hdiff
  calc
    M.eval i o = decode (encode i) o := (sufficient i o).symm
    _ = decode (encode j) o := by rw [h]
    _ = M.eval j o := sufficient j o

/-- Dually, every sufficient outcome encoding must preserve every visible outcome distinction. -/
theorem every_col_sufficient_encoding_preserves_visible_distinctions
    {I O V E : Type} (M : Interaction I O V)
    (encode : O → E) (decode : E → I → V)
    (sufficient : ∀ o i, decode (encode o) i = M.eval i o)
    {a b : O} (i : I) (hdiff : M.eval i a ≠ M.eval i b) :
    encode a ≠ encode b := by
  intro h
  apply hdiff
  calc
    M.eval i a = decode (encode a) i := (sufficient a i).symm
    _ = decode (encode b) i := by rw [h]
    _ = M.eval i b := sufficient b i

/-- Generic minimal-interface theorem: row and column profile images jointly
    discard all raw labels invisible to current consequence, lose no realized
    operational role, reproduce the full current interaction, and every other
    sufficient encoding must retain every distinction they expose. -/
theorem bipartite_consequence_induces_minimal_operational_interface
    {I O V : Type} (M : Interaction I O V) :
    (∀ i o, rowEval (induceRow M i) o = M.eval i o) ∧
    (∀ i o, colEval (induceCol M o) i = M.eval i o) ∧
    (∀ r : RowCarrier M, ∃ i : I, induceRow M i = r) ∧
    (∀ c : ColCarrier M, ∃ o : O, induceCol M o = c) := by
  exact ⟨row_carrier_sufficient M, col_carrier_sufficient M,
    induce_row_surjective M, induce_col_surjective M⟩

#check row_carrier_sufficient
#check col_carrier_sufficient
#check row_eq_iff_observationally_equal
#check col_eq_iff_observationally_equal
#check induce_row_surjective
#check induce_col_surjective
#check every_row_sufficient_encoding_preserves_visible_distinctions
#check every_col_sufficient_encoding_preserves_visible_distinctions
#check bipartite_consequence_induces_minimal_operational_interface

end MinimalBipartiteConsequenceInterface

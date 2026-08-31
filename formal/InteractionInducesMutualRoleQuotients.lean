namespace InteractionInducesMutualRoleQuotients

/-- A single undifferentiated carrier.  There are no separate caller, callee,
    key, response, object, arrow, or grammar types. -/
inductive Node where
  | a
  | b
  | c
  deriving DecidableEq

/-- The only primitive observational structure is a directed Boolean
    interaction on the one carrier. -/
abbrev Interaction := Node → Node → Bool

/-- Two nodes are equivalent in the first interaction coordinate exactly when
    no possible counterpart can distinguish them there. -/
def RowEq (R : Interaction) (x y : Node) : Prop :=
  ∀ z, R x z = R y z

/-- Two nodes are equivalent in the second interaction coordinate exactly when
    no possible counterpart can distinguish them there. -/
def ColEq (R : Interaction) (x y : Node) : Prop :=
  ∀ z, R z x = R z y

/-- Before any consequential interaction is retained, every node has the same
    operational profile in both coordinates. -/
def emptyInteraction : Interaction := fun _ _ => false

/-- One verified interaction fact is retained.  No role labels accompany it. -/
def oneFactInteraction : Interaction := fun x y =>
  x = Node.a && y = Node.b

/-- Initially the first-coordinate quotient is indiscrete. -/
theorem empty_rows_indistinguishable (x y : Node) :
    RowEq emptyInteraction x y := by
  intro z
  rfl

/-- Initially the second-coordinate quotient is indiscrete. -/
theorem empty_cols_indistinguishable (x y : Node) :
    ColEq emptyInteraction x y := by
  intro z
  rfl

/-- The single retained fact makes `a` distinguishable from `c` in the first
    coordinate, witnessed by interaction with `b`. -/
theorem one_fact_refines_row_quotient :
    ¬ RowEq oneFactInteraction Node.a Node.c := by
  intro h
  have hab := h Node.b
  simp [oneFactInteraction] at hab

/-- The same retained fact makes `b` distinguishable from `c` in the second
    coordinate, witnessed by interaction with `a`. -/
theorem one_fact_refines_col_quotient :
    ¬ ColEq oneFactInteraction Node.b Node.c := by
  intro h
  have hab := h Node.a
  simp [oneFactInteraction] at hab

/-- No primitive role partition is needed: one directed consequential fact on a
    single carrier simultaneously creates nontrivial observational structure in
    both interaction coordinates. -/
theorem one_interaction_fact_induces_two_operational_role_distinctions :
    RowEq emptyInteraction Node.a Node.c ∧
    ColEq emptyInteraction Node.b Node.c ∧
    ¬ RowEq oneFactInteraction Node.a Node.c ∧
    ¬ ColEq oneFactInteraction Node.b Node.c := by
  exact ⟨
    empty_rows_indistinguishable _ _,
    empty_cols_indistinguishable _ _,
    one_fact_refines_row_quotient,
    one_fact_refines_col_quotient⟩

/-- The first- and second-coordinate roles are not merely renamed copies in the
    witness: `a` and `c` remain equivalent in the second coordinate while they
    are separated in the first. -/
theorem induced_roles_are_directionally_asymmetric :
    ColEq oneFactInteraction Node.a Node.c ∧
    ¬ RowEq oneFactInteraction Node.a Node.c := by
  constructor
  · intro z
    cases z <;> simp [oneFactInteraction]
  · exact one_fact_refines_row_quotient

/-- Dually, `b` and `c` remain equivalent in the first coordinate while they
    are separated in the second. -/
theorem induced_roles_have_dual_asymmetry :
    RowEq oneFactInteraction Node.b Node.c ∧
    ¬ ColEq oneFactInteraction Node.b Node.c := by
  constructor
  · intro z
    cases z <;> simp [oneFactInteraction]
  · exact one_fact_refines_col_quotient

/-- Relation-first boundary theorem: the same raw node carrier supports two
    consequence-induced role quotients, and a single verified interaction can
    refine both without any supplied classification of nodes into role types. -/
theorem interaction_induces_mutual_role_quotients :
    (∀ x y, RowEq emptyInteraction x y) ∧
    (∀ x y, ColEq emptyInteraction x y) ∧
    ¬ RowEq oneFactInteraction Node.a Node.c ∧
    ¬ ColEq oneFactInteraction Node.b Node.c ∧
    ColEq oneFactInteraction Node.a Node.c ∧
    RowEq oneFactInteraction Node.b Node.c := by
  exact ⟨
    empty_rows_indistinguishable,
    empty_cols_indistinguishable,
    one_fact_refines_row_quotient,
    one_fact_refines_col_quotient,
    induced_roles_are_directionally_asymmetric.1,
    induced_roles_have_dual_asymmetry.1⟩

#check empty_rows_indistinguishable
#check empty_cols_indistinguishable
#check one_fact_refines_row_quotient
#check one_fact_refines_col_quotient
#check one_interaction_fact_induces_two_operational_role_distinctions
#check induced_roles_are_directionally_asymmetric
#check induced_roles_have_dual_asymmetry
#check interaction_induces_mutual_role_quotients

end InteractionInducesMutualRoleQuotients

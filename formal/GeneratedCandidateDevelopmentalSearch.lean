import MultiCandidateDevelopmentalSearch

universe u

namespace GeneratedCandidateDevelopmentalSearch

open VerifiedConsequenceGenesis
open MultiCandidateDevelopmentalSearch

/-- Frozen generic depth-one grammar generator.  Its input is only a universe
    of primitive atoms.  For every primitive currently licensed by `L`, it
    mechanically emits the atom and its immediate unary descendant.

    Crucially, no compound candidate is supplied by the caller. -/
noncomputable def generateDepthOne
    {A : Type u} (L : Lang A) : List A → List (Expr A)
  | [] => []
  | a :: rest => by
      classical
      exact if L a then
        [.atom a, .op (.atom a)] ++ generateDepthOne L rest
      else
        generateDepthOne L rest

/-- Before promotion, the generic generator cannot emit any expression whose
    required primitive is absent. -/
theorem cold_generator_excludes_missing_seed
    {A : Type u}
    (L : Lang A) (decoy seed : A)
    (hdecoyPresent : L decoy)
    (hseedMissing : ¬ L seed) :
    generateDepthOne L [decoy, seed] =
      [.atom decoy, .op (.atom decoy)] := by
  classical
  simp [generateDepthOne, hdecoyPresent, hseedMissing]

/-- Promotion changes the output of the same generic generator: the newly
    licensed seed is expanded mechanically, so its descendant is generated
    rather than preinserted into a search list. -/
theorem warm_generator_creates_descendant
    {A : Type u}
    (L : Lang A) (decoy seed : A)
    (hdecoyPresent : L decoy) :
    generateDepthOne (Promote L seed) [decoy, seed] =
      [.atom decoy, .op (.atom decoy),
       .atom seed, .op (.atom seed)] := by
  classical
  simp [generateDepthOne, Promote, hdecoyPresent]

/-- Endogenous-candidate bounded capability theorem.

    Cold and warm systems share:
    * the same primitive universe `[decoy, seed]`;
    * the same generic grammar generator;
    * the same left-to-right search algorithm;
    * the same verifier;
    * the same maximum verifier budget of four.

    The verifier rejects the three earlier generated expressions and accepts
    only `op(atom seed)`.  The winning compound expression is not supplied to
    the controller.  It is generated only after verified promotion makes
    `seed` a licensed grammar atom.  Exact ancestor ablation removes it from
    the generated candidate set and the identical bounded search returns
    failure. -/
theorem promotion_changes_generated_multicandidate_capability
    {A : Type u}
    (L : Lang A) (decoy seed : A)
    (verify : Expr A → Prop)
    (hdecoyPresent : L decoy)
    (hseedMissing : ¬ L seed)
    (hrejectDecoyAtom : ¬ verify (.atom decoy))
    (hrejectDecoyOp : ¬ verify (.op (.atom decoy)))
    (hrejectSeedAtom : ¬ verify (.atom seed))
    (hacceptDescendant : verify (.op (.atom seed))) :
    boundedSearch (Promote L seed) verify 4
        (generateDepthOne (Promote L seed) [decoy, seed]) =
          some (.op (.atom seed)) ∧
    boundedSearch L verify 4
        (generateDepthOne L [decoy, seed]) = none := by
  have hwarmGen := warm_generator_creates_descendant L decoy seed hdecoyPresent
  have hcoldGen := cold_generator_excludes_missing_seed
    L decoy seed hdecoyPresent hseedMissing

  have hdecoyAtomWarm : Expressible (Promote L seed) (.atom decoy) := by
    exact Expressible.atom (Or.inl hdecoyPresent)
  have hdecoyOpWarm : Expressible (Promote L seed) (.op (.atom decoy)) := by
    exact Expressible.op hdecoyAtomWarm
  have hseedAtomWarm : Expressible (Promote L seed) (.atom seed) :=
    promoted_atom_expressible L seed
  have hdescWarm : Expressible (Promote L seed) (.op (.atom seed)) :=
    promotion_enables_descendant L seed

  have hdecoyAtomCold : Expressible L (.atom decoy) := by
    exact Expressible.atom hdecoyPresent
  have hdecoyOpCold : Expressible L (.op (.atom decoy)) := by
    exact Expressible.op hdecoyAtomCold

  constructor
  · rw [hwarmGen]
    simp [boundedSearch, hdecoyAtomWarm, hdecoyOpWarm,
      hseedAtomWarm, hdescWarm, hrejectDecoyAtom, hrejectDecoyOp,
      hrejectSeedAtom, hacceptDescendant]
  · rw [hcoldGen]
    simp [boundedSearch, hdecoyAtomCold, hdecoyOpCold,
      hrejectDecoyAtom, hrejectDecoyOp]

end GeneratedCandidateDevelopmentalSearch

#check GeneratedCandidateDevelopmentalSearch.generateDepthOne
#check GeneratedCandidateDevelopmentalSearch.cold_generator_excludes_missing_seed
#check GeneratedCandidateDevelopmentalSearch.warm_generator_creates_descendant
#check GeneratedCandidateDevelopmentalSearch.promotion_changes_generated_multicandidate_capability

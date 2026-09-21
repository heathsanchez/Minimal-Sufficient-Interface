import Nucleus.PathBehavior
import Nucleus.Fixtures

open CategoryTheory
open Nucleus
open Nucleus.Fixtures

#check PathAction
#check PathBehEq
#check pathHomRel
#check pathBehEq_refl
#check pathBehEq_symm
#check pathBehEq_trans
#check pathBehEq_precomp
#check pathBehEq_postcomp
#check pathBehEq_congruence

example : ImmediateObsEq futureFixtureAction futureFixtureObs futureObserve
    futureP futureQ :=
  futureImmediateWeakness.1

example : ¬ PathBehEq futureFixtureAction futureFixtureObs futureObserve
    futureP futureQ :=
  futureImmediateWeakness.2

example : OneStateEq sourceFixtureAction sourceFixtureObs sourceObserve
    sourceChosen sourceP sourceQ :=
  sourceStateWeakness.1

example : ¬ PathBehEq sourceFixtureAction sourceFixtureObs sourceObserve
    sourceP sourceQ :=
  sourceStateWeakness.2

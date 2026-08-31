import ConsequenceSelectedResidualForcesOperationalJoin

namespace ConsequenceDeterminesQuestionNotAnswer

open VerifierOutcomeCannotIdentifyExactContextGrammar
open NewConsequenceSeparatesContextGrammar
open VersionSpaceInducesDecidingContext
open DevelopmentAsOperationalJoin

/-- The observable object retained from a verifier interaction is its outcome
    profile, not the hidden grammar that produced it. -/
abbrev Profile := Bool → Prop

/-- Two possible worlds produce exactly the same retained consequence at the
    current observation site. -/
def currentObservationNeg : Profile :=
  OutcomeProfile grammarNeg verifier true

def currentObservationConst : Profile :=
  OutcomeProfile grammarConst verifier true

theorem same_current_observation :
    currentObservationNeg = currentObservationConst := by
  exact same_outcome_profile

/-- The next question is not chosen from knowledge of which world is actual.
    It is the context induced by disagreement inside the current version space. -/
def selectedQuestion : Bool :=
  generatedDecidingContext.1

theorem selected_question_is_false : selectedQuestion = false := by
  rfl

/-- Current ambiguity forces the same deciding question before either world's
    next answer is known. -/
theorem current_consequence_forces_question :
    (∃ G₁ G₂ : VersionSpace, G₁.1 ≠ G₂.1) ∧
    (∀ d : DecidingContext, d.1 = selectedQuestion) := by
  constructor
  · exact ⟨negVersion, constVersion, version_space_contains_distinct_grammars⟩
  · intro d
    exact deciding_context_is_unique d

/-- The two worlds' answers to that same endogenously selected question. -/
def nextAnswerNeg : Profile :=
  OutcomeProfile grammarNeg verifier selectedQuestion

def nextAnswerConst : Profile :=
  OutcomeProfile grammarConst verifier selectedQuestion

/-- Although the worlds were observationally identical before the query, their
    answers at the consequence-selected question are different. -/
theorem next_answers_differ : nextAnswerNeg ≠ nextAnswerConst := by
  intro h
  have hpoint : nextAnswerNeg true = nextAnswerConst true := congrFun h true
  have hneg : nextAnswerNeg true := by
    simpa [nextAnswerNeg, selectedQuestion,
      VersionSpaceInducesDecidingContext.generatedDecidingContext] using
      neg_grammar_reaches_true_from_false
  have hconst : nextAnswerConst true := hpoint.mp hneg
  have : OutcomeProfile grammarConst verifier false true := by
    simpa [nextAnswerConst, selectedQuestion,
      VersionSpaceInducesDecidingContext.generatedDecidingContext] using hconst
  exact const_grammar_cannot_reach_true_from_false this

/-- Information-theoretic grounding boundary.  No deterministic procedure whose
    only input is the currently retained consequence can correctly manufacture
    the next verifier answer in both possible worlds. -/
theorem no_current_consequence_predictor_recovers_both_answers :
    ¬ ∃ predict : Profile → Profile,
      predict currentObservationNeg = nextAnswerNeg ∧
      predict currentObservationConst = nextAnswerConst := by
  rintro ⟨predict, hNeg, hConst⟩
  apply next_answers_differ
  calc
    nextAnswerNeg = predict currentObservationNeg := hNeg.symm
    _ = predict currentObservationConst := by rw [same_current_observation]
    _ = nextAnswerConst := hConst

/-- Operational evidence records both the generated question and the external
    answer returned there. -/
abbrev Evidence := Bool × Profile

def retainedEvidence : Evidence :=
  (true, currentObservationNeg)

def currentImage : Image Evidence :=
  fun e => e = retainedEvidence

def negEvidence : Evidence :=
  (selectedQuestion, nextAnswerNeg)

def constEvidence : Evidence :=
  (selectedQuestion, nextAnswerConst)

theorem neg_evidence_absent_before : ¬ currentImage negEvidence := by
  intro h
  have hctx : negEvidence.1 = retainedEvidence.1 := congrArg Prod.fst h
  simp [negEvidence, retainedEvidence, selectedQuestion,
    VersionSpaceInducesDecidingContext.generatedDecidingContext] at hctx

theorem const_evidence_absent_before : ¬ currentImage constEvidence := by
  intro h
  have hctx : constEvidence.1 = retainedEvidence.1 := congrArg Prod.fst h
  simp [constEvidence, retainedEvidence, selectedQuestion,
    VersionSpaceInducesDecidingContext.generatedDecidingContext] at hctx

theorem world_answers_induce_distinct_evidence : negEvidence ≠ constEvidence := by
  intro h
  have hprofile : negEvidence.2 = constEvidence.2 := congrArg Prod.snd h
  exact next_answers_differ hprofile

/-- The same answer-agnostic residual compiler is used in either world: once an
    externally returned evidence item is supplied, require it exactly while it
    remains absent. -/
def requireEvidence (target : Evidence) (I : Image Evidence) : Image Evidence :=
  fun e => ¬ I target ∧ e = target

/-- The developmental law itself is unchanged between worlds. -/
def successor (target : Evidence) : Image Evidence :=
  develop (requireEvidence target) currentImage

theorem neg_successor_realizes_answer : successor negEvidence negEvidence := by
  exact Or.inr ⟨neg_evidence_absent_before, rfl⟩

theorem const_successor_realizes_answer : successor constEvidence constEvidence := by
  exact Or.inr ⟨const_evidence_absent_before, rfl⟩

/-- For either external answer, operational join is the least state preserving
    the current consequence and satisfying the answer-derived residual. -/
theorem successor_is_least_for_any_answer (target : Evidence) :
    AdmissibleSuccessor currentImage (requireEvidence target currentImage)
      (successor target) ∧
    (∀ J, AdmissibleSuccessor currentImage (requireEvidence target currentImage) J →
      ImageLe (successor target) J) := by
  exact join_is_least_admissible_successor
    currentImage (requireEvidence target currentImage)

/-- Different external answers force genuinely different least successors. -/
theorem different_answers_force_different_successors :
    successor negEvidence ≠ successor constEvidence := by
  intro hEq
  have hIn : successor constEvidence negEvidence := by
    rw [← hEq]
    exact neg_successor_realizes_answer
  change currentImage negEvidence ∨
    requireEvidence constEvidence currentImage negEvidence at hIn
  rcases hIn with hOld | hReq
  · exact neg_evidence_absent_before hOld
  · exact world_answers_induce_distinct_evidence hReq.2

/-- Consequently the current consequence cannot choose the correct repaired
    successor either: the same current state is compatible with two worlds whose
    same generated question receives different answers and therefore requires
    different least completions. -/
theorem no_current_consequence_selector_recovers_both_successors :
    ¬ ∃ choose : Profile → Image Evidence,
      choose currentObservationNeg = successor negEvidence ∧
      choose currentObservationConst = successor constEvidence := by
  rintro ⟨choose, hNeg, hConst⟩
  apply different_answers_force_different_successors
  calc
    successor negEvidence = choose currentObservationNeg := hNeg.symm
    _ = choose currentObservationConst := by rw [same_current_observation]
    _ = successor constEvidence := hConst

/-- Endogenous-question / exogenous-answer / canonical-completion theorem for
    the concrete Bool witness.

    The current consequence determines where missing information can be exposed,
    but cannot determine what the world will answer there.  Once that answer is
    externally supplied, the same generic operational-join law determines its
    least successor. -/
theorem consequence_determines_question_not_world_answer :
    currentObservationNeg = currentObservationConst ∧
    (∃ G₁ G₂ : VersionSpace, G₁.1 ≠ G₂.1) ∧
    (∀ d : DecidingContext, d.1 = selectedQuestion) ∧
    nextAnswerNeg ≠ nextAnswerConst ∧
    (¬ ∃ predict : Profile → Profile,
      predict currentObservationNeg = nextAnswerNeg ∧
      predict currentObservationConst = nextAnswerConst) ∧
    (∀ target : Evidence,
      AdmissibleSuccessor currentImage (requireEvidence target currentImage)
        (successor target) ∧
      (∀ J, AdmissibleSuccessor currentImage
        (requireEvidence target currentImage) J → ImageLe (successor target) J)) ∧
    successor negEvidence ≠ successor constEvidence ∧
    (¬ ∃ choose : Profile → Image Evidence,
      choose currentObservationNeg = successor negEvidence ∧
      choose currentObservationConst = successor constEvidence) := by
  exact ⟨
    same_current_observation,
    current_consequence_forces_question.1,
    current_consequence_forces_question.2,
    next_answers_differ,
    no_current_consequence_predictor_recovers_both_answers,
    successor_is_least_for_any_answer,
    different_answers_force_different_successors,
    no_current_consequence_selector_recovers_both_successors⟩

#check same_current_observation
#check current_consequence_forces_question
#check next_answers_differ
#check no_current_consequence_predictor_recovers_both_answers
#check neg_successor_realizes_answer
#check const_successor_realizes_answer
#check successor_is_least_for_any_answer
#check different_answers_force_different_successors
#check no_current_consequence_selector_recovers_both_successors
#check consequence_determines_question_not_world_answer

end ConsequenceDeterminesQuestionNotAnswer

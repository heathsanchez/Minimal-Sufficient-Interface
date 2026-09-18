import QCKAPI

/-!
# QCK v1 Axiom Audit

This file is intentionally executable documentation for the bounded QCK v1
public surface. CI compiles it after rejecting local placeholders/axioms.
The expected foundational dependencies are Lean/Mathlib quotient/extensionality
principles such as propext, Classical.choice, and Quot.sound; no sorryAx or
project-local axiom is permitted.
-/

#print axioms QCK.allWordSubstitution
#print axioms QCK.ker_le_contextNullspace
#print axioms QCK.canonicalFactor_surjective
#print axioms QCK.Certificate.comp
#print axioms QCK.operation_descends_iff
#print axioms QCK.operation_defect_witness

#print axioms QCK.closureIter_stabilizes
#print axioms QCK.futureObservableSpan_eq_dualAnnihilator
#print axioms QCK.finitePresentation_ker
#print axioms QCK.canonicalEquivFinitePresentation
#print axioms QCK.sufficient_rank_ge_canonical
#print axioms QCK.operationDefect_eq_zero_iff
#print axioms QCK.snapshotReserve_lower_bound
#print axioms QCK.ker_prod_active_snapshotReserveMap
#print axioms QCK.le_maintainedNullspace
#print axioms QCK.maintainedReserveFinrank_eq_sub
#print axioms QCK.ker_prod_active_maintainedReserveMap
#print axioms QCK.maintainedReserveUpdate_mkQ
#print axioms QCK.maintainedState_block_law
#print axioms QCK.observableVocabularyRank_submodular
#print axioms QCK.uvGeneratedContextRank_not_submodular

#print axioms QCK.assessOperation

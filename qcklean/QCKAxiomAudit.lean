import QCKAPI

/-!
# QCK v1 postulate Audit

This file is intentionally executable documentation for the bounded QCK v1
public surface. CI compiles it after rejecting local placeholders/postulates.
The expected foundational dependencies are Lean/Mathlib quotient/extensionality
principles such as propext, Classical.choice, and Quot.sound; no placeholderMarker or
project-local postulate is permitted.
-/

#print postulates QCK.allWordSubstitution
#print postulates QCK.ker_le_contextNullspace
#print postulates QCK.canonicalFactor_surjective
#print postulates QCK.Certificate.comp
#print postulates QCK.operation_descends_iff
#print postulates QCK.operation_defect_witness

#print postulates QCK.closureIter_stabilizes
#print postulates QCK.futureObservableSpan_eq_dualAnnihilator
#print postulates QCK.finitePresentation_ker
#print postulates QCK.canonicalEquivFinitePresentation
#print postulates QCK.sufficient_rank_ge_canonical
#print postulates QCK.operationDefect_eq_zero_iff
#print postulates QCK.snapshotReserve_lower_bound
#print postulates QCK.ker_prod_active_snapshotReserveMap
#print postulates QCK.le_maintainedNullspace
#print postulates QCK.maintainedReserveFinrank_eq_sub
#print postulates QCK.ker_prod_active_maintainedReserveMap
#print postulates QCK.maintainedReserveUpdate_mkQ
#print postulates QCK.maintainedState_block_law
#print postulates QCK.observableVocabularyRank_submodular
#print postulates QCK.uvGeneratedContextRank_not_submodular

#print postulates QCK.assessOperation

import QCKFiniteLinear

/-!
# QCK API v1

Thin typed boundary between the formal QCK mathematics and developmental control.

The API does not choose interventions. It exposes what the formal layer has
certified, what new context has invalidated, what reserve is required, and
which failures remain outside the current formal contract.
-/

namespace QCK

open Module Submodule LinearMap

noncomputable section

universe u v r e s

variable {𝕜 : Type u} [Field 𝕜]
variable {V : Type v} [AddCommGroup V] [Module 𝕜 V]
variable {R : Type r} [AddCommGroup R] [Module 𝕜 R]

/-- A proposed source operation has earned the right to descend through the
current representation. -/
structure CertifiedSubstitution
    (q : V →ₗ[𝕜] R) (Aop : V →ₗ[𝕜] V) : Type (max u v r) where
  stable : KernelStable q Aop

/-- A newly admitted operation exposes a distinction erased by the current
representation. The witness is executable evidence of the failed substitution. -/
structure NewContextDefect
    [FiniteDimensional 𝕜 V] [FiniteDimensional 𝕜 R]
    (q : V →ₗ[𝕜] R) (Aop : V →ₗ[𝕜] V) : Type (max u v r) where
  rank : ℕ
  rank_eq : rank = operationDefect q Aop
  positive : 0 < rank
  witness : ∃ v : V, q v = 0 ∧ q (Aop v) ≠ 0

/-- Quantified optionality obligation exported to the developmental layer. -/
structure ReserveRequired where
  snapshotRank : ℕ
  maintainedRank : ℕ

/-- The current active state and provenance are insufficient to reconstruct a
requested distinction. The payload is supplied by the calling domain. -/
structure RecoveryUnavailable (Evidence : Type e) where
  evidence : Evidence

/-- The mathematical contract may be sound while a concrete implementation
fails to realize it. -/
structure ImplementationMismatch (Evidence : Type e) where
  evidence : Evidence

/-- A purported certificate failed independent checking. -/
structure CertificateInvalid (Evidence : Type e) where
  evidence : Evidence

/-- The request falls outside the currently declared consequence contract. -/
structure OutOfScope (Scope : Type s) where
  scope : Scope

/-- Evidence is presently insufficient to classify the request further. -/
structure Unknown (Evidence : Type e) where
  evidence : Evidence

/-- Stable public result vocabulary for QCKN developmental control. -/
inductive Outcome
    (q : V →ₗ[𝕜] R) (Aop : V →ₗ[𝕜] V)
    [FiniteDimensional 𝕜 V] [FiniteDimensional 𝕜 R]
    (RecoveryEvidence MismatchEvidence InvalidEvidence Scope UnknownEvidence : Type*) where
  | certifiedSubstitution :
      CertifiedSubstitution q Aop →
      Outcome q Aop RecoveryEvidence MismatchEvidence InvalidEvidence Scope UnknownEvidence
  | newContextDefect :
      NewContextDefect q Aop →
      Outcome q Aop RecoveryEvidence MismatchEvidence InvalidEvidence Scope UnknownEvidence
  | reserveRequired :
      ReserveRequired →
      Outcome q Aop RecoveryEvidence MismatchEvidence InvalidEvidence Scope UnknownEvidence
  | recoveryUnavailable :
      RecoveryUnavailable RecoveryEvidence →
      Outcome q Aop RecoveryEvidence MismatchEvidence InvalidEvidence Scope UnknownEvidence
  | implementationMismatch :
      ImplementationMismatch MismatchEvidence →
      Outcome q Aop RecoveryEvidence MismatchEvidence InvalidEvidence Scope UnknownEvidence
  | certificateInvalid :
      CertificateInvalid InvalidEvidence →
      Outcome q Aop RecoveryEvidence MismatchEvidence InvalidEvidence Scope UnknownEvidence
  | outOfScope :
      OutOfScope Scope →
      Outcome q Aop RecoveryEvidence MismatchEvidence InvalidEvidence Scope UnknownEvidence
  | unknown :
      Unknown UnknownEvidence →
      Outcome q Aop RecoveryEvidence MismatchEvidence InvalidEvidence Scope UnknownEvidence

/-- Formal operation assessment: either the operation descends through the
representation or QCK returns a positive defect with a separating witness. -/
inductive OperationAssessment
    [FiniteDimensional 𝕜 V] [FiniteDimensional 𝕜 R]
    (q : V →ₗ[𝕜] R) (Aop : V →ₗ[𝕜] V) where
  | certified : CertifiedSubstitution q Aop → OperationAssessment q Aop
  | defect : NewContextDefect q Aop → OperationAssessment q Aop

/-- Total classifier for the finite-linear operation interface. -/
noncomputable def assessOperation
    [FiniteDimensional 𝕜 V] [FiniteDimensional 𝕜 R]
    (q : V →ₗ[𝕜] R) (Aop : V →ₗ[𝕜] V) :
    OperationAssessment q Aop := by
  classical
  by_cases hz : operationDefect q Aop = 0
  · exact OperationAssessment.certified
      ⟨(operationDefect_eq_zero_iff q Aop).1 hz⟩
  · have hp : 0 < operationDefect q Aop := Nat.pos_of_ne_zero hz
    exact OperationAssessment.defect
      ⟨operationDefect q Aop, rfl, hp,
        operationDefect_positive_witness q Aop hp⟩

end

end QCK

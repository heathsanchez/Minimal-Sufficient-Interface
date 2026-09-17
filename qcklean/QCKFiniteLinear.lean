import QCKCore
import Mathlib.LinearAlgebra.Dimension.Finite
import Mathlib.LinearAlgebra.Quotient.Basic

/-!
# QCK Finite Linear v1

Finite-dimensional consequences of the quotient-first QCK core.

This layer keeps the semantic quotient canonical and treats reserves as quotients
of information currently forgotten by the active representation.
-/

namespace QCK

universe u v
variable {𝕜 : Type u} [Field 𝕜]
variable {V : Type v} [AddCommGroup V] [Module 𝕜 V]

/-- Snapshot-safe forgetting: distinctions forgotten now and also irrelevant
to every declared future interface. -/
def snapshotNullspace
    {I : Type*} (N₀ : Submodule 𝕜 V) (future : I → V →ₗ[𝕜] 𝕜) : Submodule 𝕜 V :=
  N₀ ⊓ ⨅ i, LinearMap.ker (future i)

/-- The canonical snapshot reserve is the part of the current kernel that a
future contract may split. -/
abbrev SnapshotReserve
    {I : Type*} (N₀ : Submodule 𝕜 V) (future : I → V →ₗ[𝕜] 𝕜) :=
  N₀ ⧸ (snapshotNullspace N₀ future).comap N₀.subtype

theorem snapshotNullspace_le
    {I : Type*} (N₀ : Submodule 𝕜 V) (future : I → V →ₗ[𝕜] 𝕜) :
    snapshotNullspace N₀ future ≤ N₀ := by
  intro x hx
  exact hx.1

/-- Differences safely forgettable while waiting: they remain snapshot-safe
after every finite waiting-action word. -/
def maintainedNullspace
    {A I : Type*} (S : A → V →ₗ[𝕜] V)
    (N₀ : Submodule 𝕜 V) (future : I → V →ₗ[𝕜] 𝕜) : Submodule 𝕜 V :=
  ⨅ w : List A, (snapshotNullspace N₀ future).comap (wordMap S w)

/-- Maintained-safe forgetting is contained in snapshot-safe forgetting. -/
theorem maintainedNullspace_le_snapshot
    {A I : Type*} (S : A → V →ₗ[𝕜] V)
    (N₀ : Submodule 𝕜 V) (future : I → V →ₗ[𝕜] 𝕜) :
    maintainedNullspace S N₀ future ≤ snapshotNullspace N₀ future := by
  intro x hx
  have h := show ∀ w : List A, x ∈ (snapshotNullspace N₀ future).comap (wordMap S w) by
    simpa only [Submodule.mem_iInf] using hx
  simpa [wordMap] using h []

/-- Maintained-safe forgetting is invariant under every waiting generator. -/
theorem maintainedNullspace_invariant
    {A I : Type*} (S : A → V →ₗ[𝕜] V)
    (N₀ : Submodule 𝕜 V) (future : I → V →ₗ[𝕜] 𝕜) (a : A) :
    maintainedNullspace S N₀ future ≤
      (maintainedNullspace S N₀ future).comap (S a) := by
  intro x hx
  have hall := show ∀ w : List A, x ∈ (snapshotNullspace N₀ future).comap (wordMap S w) by
    simpa only [Submodule.mem_iInf] using hx
  apply (show ∀ w : List A, S a x ∈ (snapshotNullspace N₀ future).comap (wordMap S w) by
    intro w
    simpa [wordMap] using hall (a :: w))

/-- Universal property: maintainedNullspace is the greatest generator-invariant
subspace contained in the snapshot-safe forgetting space. -/
theorem le_maintainedNullspace
    {A I : Type*} (S : A → V →ₗ[𝕜] V)
    (N₀ : Submodule 𝕜 V) (future : I → V →ₗ[𝕜] 𝕜)
    (W : Submodule 𝕜 V)
    (hWsafe : W ≤ snapshotNullspace N₀ future)
    (hWinv : ∀ a, W ≤ W.comap (S a)) :
    W ≤ maintainedNullspace S N₀ future := by
  intro x hx
  apply (show ∀ w : List A, x ∈ (snapshotNullspace N₀ future).comap (wordMap S w) by
    intro w
    induction w generalizing x with
  | nil =>
      simpa [wordMap] using hWsafe hx
    | cons a w ih =>
        change wordMap S w (S a x) ∈ snapshotNullspace N₀ future
        exact ih (hWinv a hx))

/-- The canonical maintained reserve is the quotient of distinctions forgotten
by the active representation by those still safely forgettable while waiting.
The inclusion hypothesis records that the active kernel itself is stable under
the waiting contract. -/
abbrev MaintainedReserve
    {A I : Type*} (S : A → V →ₗ[𝕜] V)
    (N₀ : Submodule 𝕜 V) (future : I → V →ₗ[𝕜] 𝕜)
    (_h : maintainedNullspace S N₀ future ≤ N₀) :=
  N₀ ⧸ (maintainedNullspace S N₀ future).comap N₀.subtype

end QCK

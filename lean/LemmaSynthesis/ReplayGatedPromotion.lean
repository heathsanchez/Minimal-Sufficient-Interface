import LemmaSynthesis.SharedSchemaRuntimeBridge

/-!
# Replay-gated promotion qualification

A selected repair is promotable exactly when independently recomputed replay
leaves no residual. The negative control carries a forged empty stored replay
but its selected repair still leaves a real residual, so promotion must be
refused. The positive control carries a stale nonempty stored replay but its
selected repair actually passes recomputation, so the exact selected tag is
promoted. The shared object and policy developments pass this same gate.
-/

namespace ReplayGatedPromotion

open SynthesisCore
open SharedSchemaRuntimeBridge


def failingReplay : DevelopmentOutcome Nat Bool :=
  { residual := (0, 1)
    selected := true
    replayResiduals := [] }

def adequateReplay : DevelopmentOutcome Nat Bool :=
  { residual := (0, 1)
    selected := true
    replayResiduals := [(0, 1)] }

def constantRepair (_ : Bool) (_ : Nat) : Bool := false

def identityRepair (_ : Bool) (n : Nat) : Nat := n

theorem selected_repair_with_real_residual_refuses_promotion :
    promoteIfReplayAdequate [0, 1] id constantRepair (some failingReplay) = none := by
  native_decide

theorem independently_adequate_repair_promotes_exact_selected_tag :
    promoteIfReplayAdequate [0, 1] id identityRepair (some adequateReplay) =
      some true := by
  native_decide

theorem absent_development_refuses_promotion :
    promoteIfReplayAdequate [0, 1] id identityRepair
      (none : Option (DevelopmentOutcome Nat Bool)) = none := by
  native_decide

theorem object_development_passes_promotion_gate :
    promoteIfReplayAdequate EndToEnd.univ EndToEnd.FB
      objectRepairQuotient objectDevelopment = some EndToEnd.DiscTag.head := by
  native_decide

theorem policy_development_passes_promotion_gate :
    promoteIfReplayAdequate policyUniv policyFB
      policyRepairQuotient metaDevelopment =
      some PolicyProgram.deriveFromResidual := by
  native_decide

theorem bridge_uses_replay_gated_program :
    selectedProgram? = promoteIfReplayAdequate
      policyUniv policyFB policyRepairQuotient metaDevelopment := by
  rfl

end ReplayGatedPromotion

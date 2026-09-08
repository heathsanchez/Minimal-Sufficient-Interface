"""Generate a finite Lean qualification for the exact selected repair.

The generated source imports the existing SynthesisCore gate. Its input is a
certificate already accepted by the independent finite verifier; the theorem
proves adequacy on the recorded acquisition universe, not unseen-game truth.
"""
import hashlib
import json
from pathlib import Path
import verify_composite_repair as V

def render(cert, data):
    V.verify(cert, data)
    spec=cert["payload"]["spec"]
    old_spec={"kind":"state","words":[]}
    old_keys=[V.observe(old_spec,r) for r in data]
    repaired_keys=[V.observe(spec,r) for r in data]
    def ids(values):
        table={}
        return [table.setdefault(tuple(v) if isinstance(v,(tuple,list)) else v,len(table))
                for v in values]
    old=ids(old_keys)
    repaired=ids(repaired_keys)
    protected=[r[3] for r in data]
    residual=next((i,j) for i in range(len(data)) for j in range(i)
                  if old[i]==old[j] and protected[i]!=protected[j])
    i,j=residual
    def lit(xs):
        return "["+", ".join(map(str,xs))+"]"
    identity=json.dumps(cert["identity"])
    return f"""import LemmaSynthesis.SynthesisCore

/-! Generated finite replay certificate.
Selected certificate: {cert["identity"]}
Scope: {len(data)} externally acquired rows, not the hidden world's full domain.
-/
namespace UnifiedQualification
open SynthesisCore

private def certificateId : String := {identity}
private def univ : List Nat := List.range {len(data)}
private def oldValues : List Nat := {lit(old)}
private def repairedValues : List Nat := {lit(repaired)}
private def protectedValues : List Nat := {lit(protected)}
private def lookup (xs : List Nat) (i : Nat) : Nat := xs[i]!
private def oldQ : Nat → Nat := lookup oldValues
private def protectedObs : Nat → Nat := lookup protectedValues
private def repairQ (tag : String) (i : Nat) : Nat :=
  if tag = certificateId then lookup repairedValues i else 0

private def actualResidual : Nat × Nat := ({i}, {j})
private def selected : DevelopmentOutcome Nat String :=
  {{ residual := actualResidual, selected := certificateId, replayResiduals := [] }}
private def forged : DevelopmentOutcome Nat String :=
  {{ residual := actualResidual, selected := "forged", replayResiduals := [] }}
private def stale : DevelopmentOutcome Nat String :=
  {{ residual := actualResidual, selected := certificateId,
     replayResiduals := [actualResidual] }}

theorem old_representation_has_residual :
    oldQ {i} = oldQ {j} ∧ protectedObs {i} ≠ protectedObs {j} := by decide

theorem exact_selected_repair_promotes :
    promoteIfReplayAdequate univ protectedObs repairQ (some selected) =
      some certificateId := by native_decide

theorem forged_empty_replay_refuses :
    promoteIfReplayAdequate univ protectedObs repairQ (some forged) = none := by native_decide

theorem stale_stored_replay_does_not_block :
    promoteIfReplayAdequate univ protectedObs repairQ (some stale) =
      some certificateId := by native_decide

theorem absent_development_refuses :
    promoteIfReplayAdequate univ protectedObs repairQ
      (none : Option (DevelopmentOutcome Nat String)) = none := by native_decide

end UnifiedQualification
"""

def write(cert, data, path):
    source=render(cert,data)
    Path(path).write_text(source)
    return hashlib.sha256(source.encode()).hexdigest()

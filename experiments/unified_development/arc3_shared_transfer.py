"""One-stage ARC3 transfer through the existing shared developmental gate.

The frozen controller proposes a witnessed option. It is not shared-retained
until fresh public-API replay and the actual Lean SynthesisCore gate accept it.
This is a bounded policy-attachment test, not general world-model genesis.
"""
import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import closed_feedback_v2 as F

FROZEN = "68e37033f3ae1e86e992dfe8d982aef9133612aa"
UPSTREAM = "f12822c4d550121c35a275008d964afbbed47d2f"
SOURCE_BLOBS = {
    "agent.py": "00e9d5059aa21bc6a3c47d46a829ecef58a29bea",
    "finite_consequence.py": "6c9831358dabb33ba1323ebcbc85f683b6587248",
    "restart_development.py": "9ee7e56721309205ae86da9edb762376296dcf5b",
    "multi_level_development.py": "6f7a9728d195c224c572caeb526b55b9c03a0c22",
    "compositional_development.py": "e4092ca1f1c00a71595d75b6e42ce11933d1d6db",
    "parameterized_actions.py": "d8fd45375e538bd9cf59b2b3f0a477ba1d1f134c",
}

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()

def source_blob(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def load_frozen(directory):
    directory = Path(directory).resolve()
    for name, expected in SOURCE_BLOBS.items():
        if source_blob(directory / name) != expected:
            raise ValueError("Frozen source mismatch: " + name)
    sys.path.insert(0, str(directory))
    import agent
    import finite_consequence
    import parameterized_actions
    import compositional_development
    import multi_level_development
    return agent, finite_consequence, parameterized_actions, compositional_development, multi_level_development

def lean_source(identity, outcomes, evidence_sha):
    """Use the real shared develop/promote implementation, not a Python copy."""
    if len(outcomes) != 2 or outcomes[0] == outcomes[1]:
        raise ValueError("No separating consequence")
    return '''import LemmaSynthesis.SynthesisCore
namespace ARC3SharedTransfer
open SynthesisCore
private def certificateId : String := ''' + json.dumps(identity) + '''
private def evidenceId : String := ''' + json.dumps(evidence_sha) + '''
private def univ : List Nat := [0, 1]
private def protectedObs : Nat → Nat := fun i => [0, 1][i]!
private def oldQ (_ : Nat) : Nat := 0
private def repairQ (tag : String) (i : Nat) : Nat :=
  if tag = certificateId then i else 0
private def candidates : List (Candidate Nat Nat String) :=
  [⟨"keepBaseline", 0, fun _ => 0⟩,
   ⟨certificateId, 1, fun i => i⟩]
private def development :=
  develop univ oldQ protectedObs candidates repairQ
private def selected? :=
  promoteIfReplayAdequate univ protectedObs repairQ development
private theorem selected_exactly : selected? = some certificateId := by native_decide
private theorem forged_empty_replay_refused :
  promoteIfReplayAdequate univ protectedObs repairQ
    (some { residual := (0, 1), selected := "keepBaseline", replayResiduals := [] }) = none := by
  native_decide
private theorem stale_replay_does_not_block :
  promoteIfReplayAdequate univ protectedObs repairQ
    (some { residual := (0, 1), selected := certificateId, replayResiduals := [(0, 1)] }) =
      some certificateId := by native_decide
#eval IO.println (if selected? = some certificateId then
  "ARC3_SHARED_PROMOTION=" ++ certificateId else "ARC3_SHARED_PROMOTION_REFUSED")
end ARC3SharedTransfer
'''

def run_lean_gate(identity, outcomes, evidence_sha, output, lean="lean"):
    """The only production promotion authority is successful external Lean."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    source = lean_source(identity, outcomes, evidence_sha)
    path = output / "ARC3SharedTransfer.lean"
    path.write_text(source)
    env = dict(os.environ, LEAN_PATH=str(ROOT / "lean"))
    core = ROOT / "lean/LemmaSynthesis/SynthesisCore.lean"
    subprocess.run([lean, "-o", str(output / "SynthesisCore.olean"), str(core)],
                   cwd=ROOT, env=env, check=True, capture_output=True, text=True)
    env["LEAN_PATH"] = str(output) + os.pathsep + str(ROOT / "lean")
    result = subprocess.run([lean, str(path)], cwd=ROOT, env=env,
                            check=True, capture_output=True, text=True)
    marker = "ARC3_SHARED_PROMOTION=" + identity
    if marker not in result.stdout.splitlines():
        raise ValueError("Lean did not return the exact selected identity")
    return {"identity": identity, "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
            "marker": marker, "lean_output": result.stdout}

def better(a, b):
    return (a["state"] == "WIN", a["levels_completed"], -a["actions"]) > (b["state"] == "WIN", b["levels_completed"], -b["actions"])

def promote(factory, prefix, source, cold, initial_sha, archive, output, gate=run_lean_gate):
    """Reject before installation on every mismatch or failed verifier."""
    prefix = tuple(prefix)
    if not prefix:
        return {"status": "NO_WITNESSED_OPTION"}
    first = F.replay(factory, prefix, None, 120)
    proof = F.replay(factory, prefix, first["final_sha256"], 120)
    valid = (first["status"] == proof["status"] == "OBSERVED"
             and first["executed"] == proof["executed"] == prefix
             and first["observations"] == proof["observations"]
             and first["initial_sha256"] == proof["initial_sha256"] == initial_sha
             and proof["levels_completed"] > 0)
    if not valid:
        return {"status": "INCONCLUSIVE_REPLAY", "replay": first, "proof": proof}
    candidate = {"actions": len(prefix), "levels_completed": proof["levels_completed"], "state": proof["state"]}
    if not better(candidate, cold):
        return {"status": "NO_MEASURED_IMPROVEMENT", "replay": first, "proof": proof}
    evidence = {"initial_sha256": initial_sha, "program": prefix, "cold": cold,
                "replay": first, "proof": proof, "source_commit": FROZEN}
    evidence_sha = digest(evidence)
    identity = digest({"kind": "arc3_witnessed_policy", "evidence_sha256": evidence_sha,
                       "program": prefix, "source_commit": FROZEN})
    # A failed, absent, or forged gate result cannot reach archive.install.
    approval = gate(identity, [cold, candidate], evidence_sha, output)
    if approval.get("identity") != identity:
        raise ValueError("Promotion identity mismatch")
    entry = first["initial_sha256"]
    archive.install(entry, prefix, first["final_sha256"], proof,
                    source=("policy", identity))
    return {"status": "REPLAY_GATED_PROMOTION_PASS", "identity": identity,
            "evidence_sha256": evidence_sha, "evidence": evidence, "approval": approval,
            "replay_actions": first["actions"] + proof["actions"]}

def run(factory, actions, discover, execute_stage, output, max_training_actions=3000,
        max_episodes=512, max_depth=32, gate=run_lean_gate):
    """A single bounded development cycle, followed by genuine fresh deployment."""
    actions = tuple(actions)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    archive = F.FeedbackArchive()
    first = factory()
    initial_sha = digest(F.observe(first.observation_space))
    first.close()
    # Reserve two maximum-depth replays inside the declared training budget.
    reserve = min(2 * max_depth, max_training_actions)
    discovery_budget = max_training_actions - reserve
    if discovery_budget < 1:
        raise ValueError("Training budget must leave room for replay")
    d = discover(factory, actions, budget=120, max_episodes=max_episodes,
                 max_depth=max_depth, max_training_actions=discovery_budget, max_levels=1)
    cold = execute_stage(factory(), (), actions * ((120 + len(actions)-1)//len(actions)),
                         0, 120, stop_at_progress=False)
    result = {"status": "NO_PROMOTION_WITHIN_BOUND", "source_commit": FROZEN,
              "source_development": d.snapshot(), "cold": cold, "initial_sha256": initial_sha,
              "grounded_actions": len(actions), "model_calls": 0, "competition_submission": False}
    if d.initial_sha256 != initial_sha or cold["initial_sha256"] != initial_sha:
        result["status"] = "INCONCLUSIVE_UNMATCHED_START"
        return result
    if not d.stages:
        return result
    candidate = promote(factory, d.prefix, d.stages[-1], cold, initial_sha, archive, output, gate)
    result["promotion"] = candidate
    result["training_actions"] = d.training_actions + candidate.get("replay_actions", 0)
    if candidate["status"] != "REPLAY_GATED_PROMOTION_PASS":
        return result
    if result["training_actions"] > max_training_actions:
        raise ValueError("Training budget exceeded before installation")
    # The actual installed operation must change the next search proposal.
    next_candidate = next(F.candidates(actions, archive, (), 120, max_depth, feedback=True))
    if next_candidate["source"] != ("option", 0):
        raise ValueError("Retained operation did not enter future search")
    warm = F.replay(factory, next_candidate["program"], None, 120)
    if warm["initial_sha256"] != initial_sha or warm["executed"] != tuple(d.prefix):
        result["status"] = "INCONCLUSIVE_DEPLOYMENT"
        return result
    result.update(status="COMPARABLE", warm={k:v for k,v in warm.items() if k != "observations"},
                  installed_options=archive.snapshot()["options"],
                  next_candidate_source=next_candidate["source"],
                  improved=better(warm, cold))
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--frozen-dir", required=True)
    p.add_argument("--environments-dir", required=True)
    p.add_argument("--game", default="bt33-a7c3f9d18b4e")
    p.add_argument("--output", default="arc3-shared-transfer.json")
    a = p.parse_args()
    agent, finite, grounding, compositional, multilevel = load_frozen(a.frozen_dir)
    from arc_agi import Arcade, OperationMode
    logger = logging.getLogger("arc3-shared-transfer")
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.WARNING)
    def factory():
        arcade = Arcade(operation_mode=OperationMode.OFFLINE, environments_dir=a.environments_dir, logger=logger)
        env = arcade.make(a.game)
        if env is None:
            raise RuntimeError("Environment unavailable")
        class Adapter:
            @property
            def observation_space(self): return env.observation_space
            @property
            def action_space(self): return env.action_space
            def reset(self): return env.reset()
            def step(self, action):
                kind, data = grounding.decode(action)
                return env.step(kind, data=data)
            def close(self): return arcade.close_scorecard()
        return Adapter()
    first = factory()
    actions, unsupported = grounding.action_catalog(first.action_space, first.observation_space, 8, 256)
    first.close()
    result = run(factory, actions, compositional.discover_levels, multilevel.execute_stage,
                 Path(a.output).parent / "shared-gate")
    result.update(game=a.game, mode="offline", unsupported_action_ids=unsupported,
                  upstream_commit=UPSTREAM, source_blobs=SOURCE_BLOBS)
    Path(a.output).write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n")
    print("ARC3_SHARED_TRANSFER=" + json.dumps({k:result.get(k) for k in
          ("status", "training_actions", "grounded_actions", "improved", "installed_options")}, sort_keys=True))

if __name__ == "__main__":
    main()

"""Replay-gated ARC3 continuation from an immutable checkpoint.

The frozen constructor grammar is unchanged. Shortest-first scheduling repairs
the observed starvation of affordable candidates. Every training action,
including rejected and failed replay, is charged at the environment boundary.
"""
import argparse
import json
import logging
from collections import deque
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import arc3_shared_transfer as T
import closed_feedback_v2 as F

SOURCE_RUN = 34240189934
SOURCE_IDENTITY = "cc9b95c1a7237465e8a8075e7277de07c0602c583d77d5e2aec1802ac2e83709"


def compact(result):
    return {k: result[k] for k in ("status", "initial_sha256", "final_sha256",
            "actions", "levels_completed", "state", "executed") if k in result}


class TrainingLimit(Exception):
    """No unfunded environment interaction is permitted."""


class ActionMeter:
    def __init__(self, factory, actions, episodes, max_actions, max_episodes):
        self._factory = factory
        self.actions = actions
        self.episodes = episodes
        self.max_actions = max_actions
        self.max_episodes = max_episodes

    def reserve(self, actions, episodes=0):
        if self.actions + actions > self.max_actions or self.episodes + episodes > self.max_episodes:
            raise TrainingLimit("Insufficient budget for the complete experiment")

    def factory(self):
        self.reserve(0, 1)
        env = self._factory()
        self.episodes += 1
        meter = self

        class MeasuredEnvironment:
            def __getattr__(self, name):
                return getattr(env, name)

            def step(self, action):
                meter.reserve(1)
                # Charge attempted interactions even if the external call raises.
                meter.actions += 1
                return env.step(action)

        return MeasuredEnvironment()


def order_frontier(search):
    """Change scheduling, not the frozen grammar or its retained evidence."""
    search.frontier = deque(sorted(search.frontier, key=len))


def continue_verified(factory, actions, source, search_type, execute_stage, output,
                      max_training_actions=3000, max_episodes=512, max_depth=32,
                      budget=120, max_levels=5, gate=T.run_lean_gate):
    actions = tuple(actions)
    if not actions or min(max_training_actions, max_episodes, max_depth, budget) < 1:
        raise ValueError("Positive bounds and nonempty actions required")
    if source.get("status") != "COMPARABLE" or source.get("source_commit") != T.FROZEN:
        raise ValueError("Unqualified source checkpoint")
    if source.get("promotion", {}).get("identity") != SOURCE_IDENTITY:
        raise ValueError("Unexpected source promotion identity")
    if source.get("promotion", {}).get("status") != "REPLAY_GATED_PROMOTION_PASS":
        raise ValueError("Source promotion was not accepted")
    stages = source["source_development"]["stages"]
    if len(stages) != 1 or source["source_development"]["prefix"] != stages[0]["prefix"]:
        raise ValueError("Unexpected source checkpoint structure")
    if source.get("training_actions", 0) > max_training_actions:
        raise ValueError("Source exceeds cumulative training bound")
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    meter = ActionMeter(factory, source["training_actions"],
                        source["source_development"]["training_episodes"],
                        max_training_actions, max_episodes)
    archive = F.FeedbackArchive()
    initial = source["initial_sha256"]
    prefix = ()
    checkpoint = initial
    level = 0
    options = []
    accepted = []
    evidence = []
    cold = execute_stage(factory(), (), actions * ((budget + len(actions)-1)//len(actions)),
                         0, budget, stop_at_progress=False)
    result = {"status": "NO_PROGRESS_WITHIN_BOUND", "source_run": SOURCE_RUN,
              "source_commit": T.FROZEN, "initial_sha256": initial,
              "cold": compact(cold), "grounded_actions": len(actions),
              "model_calls": 0, "competition_submission": False,
              "source_training_actions": source["training_actions"]}

    def finish(status):
        result.update(status=status, training_actions=meter.actions,
                      training_episodes=meter.episodes, accepted=accepted,
                      evidence=evidence, installed_options=archive.snapshot()["options"],
                      prefix=prefix, checkpoint_sha256=checkpoint, levels_witnessed=level)
        warm = F.replay(factory, prefix, None, budget)
        result["warm"] = compact(warm)
        result["improved"] = bool(warm["initial_sha256"] == initial
                                  and T.quality(warm) > T.quality(cold))
        result["terminal_win"] = bool(warm["initial_sha256"] == initial
                                      and warm["state"] == "WIN")
        if warm["initial_sha256"] != initial or warm["final_sha256"] != checkpoint:
            result["status"] = "INCONCLUSIVE_DEPLOYMENT"
            result["terminal_win"] = False
        return result

    if cold["initial_sha256"] != initial:
        return finish("INCONCLUSIVE_UNMATCHED_START")

    def promote(full, stage, entry):
        # Reserve both full-prefix replays before the first interaction.
        meter.reserve(2 * len(full), 2)
        staged = F.FeedbackArchive()
        approval = T.promote(meter.factory, full, stage, cold, initial, staged,
                             output / ("stage-" + str(stage["level"])), gate=gate)
        if approval["status"] != "REPLAY_GATED_PROMOTION_PASS":
            return approval
        proof = approval["evidence"]["proof"]
        suffix = tuple(full[len(entry):])
        staged.install(F.digest(proof["observations"][len(entry)]), suffix,
                       proof["final_sha256"], proof, entry_path=entry,
                       source=("policy", approval["identity"]))
        # Commit both capabilities only after the entire promotion succeeds.
        for item in staged.options:
            if item not in archive.options:
                archive.options.append(item)
        return approval

    def accept(approval, full, suffix, stage):
        nonlocal prefix, checkpoint, level
        prefix = full
        checkpoint = stage["checkpoint_sha256"]
        level = stage["level"]
        if suffix not in options:
            options.append(suffix)
        accepted.append({"level": level, "prefix": prefix, "suffix": suffix,
                         "checkpoint_sha256": checkpoint, "promotion": approval["identity"],
                         "gate_source_sha256": approval["approval"]["source_sha256"]})

    stage = stages[0]
    full = tuple(map(F.atom, stage["prefix"]))
    stage = dict(stage, prefix=full, suffix=full)
    if len(full) > budget:
        raise ValueError("Source prefix exceeds deployment bound")
    try:
        approval = promote(full, stage, ())
    except TrainingLimit:
        return finish("TRAINING_BOUND_EXHAUSTED")
    except (ValueError, subprocess.CalledProcessError, FileNotFoundError) as exc:
        result["verifier_error"] = str(exc)
        return finish("INCONCLUSIVE_VERIFIER")
    if approval["status"] != "REPLAY_GATED_PROMOTION_PASS":
        return finish(approval["status"])
    accept(approval, full, full, stage)

    while level < max_levels and meter.actions < max_training_actions and meter.episodes < max_episodes:
        search = search_type(actions, options, max_depth=max_depth)
        advanced = False
        while meter.actions < max_training_actions and meter.episodes < max_episodes:
            order_frontier(search)
            suffix = search.propose()
            if suffix is None:
                break
            full_length = len(prefix) + len(suffix)
            # Preserve the two-replay reserve. An unaffordable candidate is
            # not evidence of impossibility; try another affordable candidate.
            if full_length > budget or meter.actions + 3 * full_length > max_training_actions:
                evidence.append({"target": level, "suffix": suffix,
                                 "status": "NOT_ATTEMPTED_WITHIN_BOUND", "actions": 0})
                continue
            if meter.episodes + 3 > max_episodes:
                return finish("TRAINING_BOUND_EXHAUSTED")
            try:
                trial = execute_stage(meter.factory(), prefix, suffix, level, budget, checkpoint)
            except TrainingLimit:
                return finish("TRAINING_BOUND_EXHAUSTED")
            if trial["initial_sha256"] != initial or trial["status"].startswith("INCONCLUSIVE"):
                return finish("INCONCLUSIVE_PREFIX_MISMATCH")
            if trial["status"] in ("PREFIX_TERMINATED", "BUDGET_EXHAUSTED"):
                return finish(trial["status"])
            actual = tuple(trial["executed"][len(prefix):])
            local = dict(trial, actions=len(actual), executed=actual)
            evidence.append({"target": level, "suffix": suffix, "executed": actual,
                             "status": trial["status"], "progress": trial["progress"],
                             "trace_sha256": trial["trace_sha256"]})
            if trial["progress"] <= 0:
                search.retain(suffix, local)
                continue
            next_prefix = prefix + actual
            next_level = trial["levels_completed"]
            next_stage = {"level": next_level, "prefix": next_prefix, "suffix": actual,
                          "checkpoint_sha256": trial["final_sha256"]}
            try:
                approval = promote(next_prefix, next_stage, prefix)
            except TrainingLimit:
                return finish("TRAINING_BOUND_EXHAUSTED")
            except (ValueError, subprocess.CalledProcessError, FileNotFoundError) as exc:
                result["verifier_error"] = str(exc)
                return finish("INCONCLUSIVE_VERIFIER")
            if approval["status"] != "REPLAY_GATED_PROMOTION_PASS":
                return finish(approval["status"])
            accept(approval, next_prefix, actual, next_stage)
            advanced = True
            if approval["evidence"]["proof"]["state"] == "WIN":
                return finish("VERIFIED_WIN")
            break
        if not advanced:
            return finish("TRAINING_BOUND_EXHAUSTED" if meter.actions >= max_training_actions
                          or meter.episodes >= max_episodes else "NO_PROGRESS_WITHIN_BOUND")
    return finish("ALL_LEVELS_WITNESSED" if level >= max_levels else "TRAINING_BOUND_EXHAUSTED")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source-evidence", required=True)
    p.add_argument("--frozen-dir", required=True)
    p.add_argument("--environments-dir", required=True)
    p.add_argument("--game", default="bt33-a7c3f9d18b4e")
    p.add_argument("--output", default="arc3-multilevel-transfer.json")
    a = p.parse_args()
    agent, finite, grounding, compositional, multilevel = T.load_frozen(a.frozen_dir)
    from arc_agi import Arcade, OperationMode
    logger = logging.getLogger("arc3-multilevel-transfer")
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
    source = json.loads(Path(a.source_evidence).read_text())
    result = continue_verified(factory, actions, source, compositional.OptionSearch,
                               multilevel.execute_stage, Path(a.output).parent / "shared-gate")
    result.update(game=a.game, mode="offline", unsupported_action_ids=unsupported,
                  upstream_commit=T.UPSTREAM, source_blobs=T.SOURCE_BLOBS)
    Path(a.output).write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n")
    print("ARC3_MULTILEVEL_TRANSFER=" + json.dumps({k: result.get(k) for k in
          ("status", "training_actions", "levels_witnessed", "installed_options", "terminal_win")}, sort_keys=True))

if __name__ == "__main__":
    main()

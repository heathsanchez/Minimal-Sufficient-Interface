"""Bounded public-interface diagnostic from a replay-gated ARC3 checkpoint.

Reuse the archived capability and the existing Lean promotion gate. The only
new search rule chooses small experiments from public pixels and the existing
action grammar. A changed image is evidence, not a certified world rule.
"""
import argparse
from collections import Counter, deque
import json
import logging
from pathlib import Path
import subprocess

import arc3_multilevel_transfer as M
import arc3_shared_transfer as T
import closed_feedback_v2 as F

ARCHIVE_RUN = 34272649151
ARCHIVE_COMMIT = "716076371cfa187da3b0fe2f1150de03ec051f4c"
ARCHIVE_EVIDENCE_SHA256 = "0eba01df78865553b1be566d1544e77ef2d6a5006cb1b312d7c04e8c6c0eff51"
PRIOR_DISCOVERY_RUN = 34192005884


def validate_source(source):
    if source.get("status") != "ALL_LEVELS_WITNESSED":
        raise ValueError("Source is not an accepted archived checkpoint")
    if source.get("source_commit") != T.FROZEN or source.get("archive_run") != PRIOR_DISCOVERY_RUN:
        raise ValueError("Source provenance mismatch")
    if source.get("archive_commit") != "c65201683d0eccd8a03e07abb9ba35409419cf14":
        raise ValueError("Archived discovery commit mismatch")
    if source.get("new_discoveries") != 0 or source.get("terminal_win"):
        raise ValueError("Unexpected source result")
    accepted = source.get("accepted", [])
    prefix = tuple(map(F.atom, source.get("prefix", ())))
    if not accepted or not prefix or len(accepted) != source.get("levels_witnessed"):
        raise ValueError("Incomplete accepted history")
    previous = ()
    for i, stage in enumerate(accepted, 1):
        full = tuple(map(F.atom, stage["prefix"]))
        suffix = tuple(map(F.atom, stage["suffix"]))
        if (stage["level"] != i or not suffix or full != previous + suffix
                or not stage.get("promotion") or not stage.get("gate_source_sha256")):
            raise ValueError("Malformed accepted history")
        previous = full
    if previous != prefix or accepted[-1]["checkpoint_sha256"] != source.get("checkpoint_sha256"):
        raise ValueError("Source checkpoint mismatch")
    warm = source["warm"]
    if (tuple(map(F.atom, warm["executed"])) != prefix or
            warm["final_sha256"] != source["checkpoint_sha256"] or
            warm["initial_sha256"] != source["initial_sha256"] or
            warm["levels_completed"] != len(accepted) or warm["state"] != "NOT_FINISHED"):
        raise ValueError("Source deployment mismatch")
    if source.get("installed_options", 0) < len(accepted):
        raise ValueError("Missing retained capabilities")
    return prefix, source["checkpoint_sha256"], len(accepted)


def frame_delta(before, after):
    result = []
    for a, b in zip(before.get("frame", []), after.get("frame", [])):
        if len(a) != len(b) or any(len(x) != len(y) for x, y in zip(a, b)):
            result.append({"shape_changed": True})
            continue
        changed = [(y, x) for y, (row_a, row_b) in enumerate(zip(a, b))
                   for x, (u, v) in enumerate(zip(row_a, row_b)) if u != v]
        result.append({"shape_changed": False, "changed_elements": len(changed),
                       "bounds": [[min(p[i] for p in changed), max(p[i] for p in changed)]
                                  for i in range(2)] if changed else []})
    return result


def image_representatives(observation, actions):
    """Choose component representatives without assigning game semantics to colors."""
    allowed = {a for a in actions if isinstance(a, tuple) and len(a) == 3 and a[0] == 6}
    if not allowed:
        return ()
    out = []
    for image in observation.get("frame", []):
        if not image or not image[0]:
            continue
        height, width = len(image), len(image[0])
        if any(len(row) != width for row in image):
            continue
        background = Counter(v for row in image for v in row).most_common(1)[0][0]
        seen = set()
        components = []
        for y in range(height):
            for x in range(width):
                if (y, x) in seen or image[y][x] == background:
                    continue
                value = image[y][x]
                queue = deque([(y, x)])
                seen.add((y, x))
                cells = []
                while queue:
                    cy, cx = queue.popleft()
                    cells.append((cy, cx))
                    for ny, nx in ((cy-1,cx),(cy+1,cx),(cy,cx-1),(cy,cx+1)):
                        if (0 <= ny < height and 0 <= nx < width and
                                (ny,nx) not in seen and image[ny][nx] == value):
                            seen.add((ny,nx))
                            queue.append((ny,nx))
                components.append(cells)
        components.sort(key=lambda c: (-len(c), c[0]))
        for cells in components:
            cy = sum(y for y, x in cells) / len(cells)
            cx = sum(x for y, x in cells) / len(cells)
            ordered = sorted(cells, key=lambda p: ((p[0]-cy)**2+(p[1]-cx)**2, p))
            for y, x in (ordered[0], min(cells), max(cells)):
                action = (6, x, y)
                if action in allowed and action not in out:
                    out.append(action)
    return tuple(out)


def probes(actions, observation, options, max_probes=12, max_suffix=16):
    """Existing primitives, observation-derived parameters, and certified options."""
    if max_probes < 1 or max_suffix < 1:
        raise ValueError("Positive probe bounds required")
    actions = tuple(dict.fromkeys(map(F.atom, actions)))
    proposed = []
    def add(program, source):
        program = tuple(program)
        if program and len(program) <= max_suffix and program not in [p for p, _ in proposed]:
            proposed.append((program, source))
    for a in actions:
        if isinstance(a, int):
            add((a,), "primitive")
    for a in image_representatives(observation, actions):
        add((a,), "observed_component")
    for option in reversed(tuple(options)):
        add(tuple(map(F.atom, option)), "verified_option")
    for a in actions:
        if len(proposed) >= max_probes:
            break
        add((a,), "catalog")
    return tuple(proposed[:max_probes])


def run(factory, actions, source, output, max_training_actions=900,
        max_episodes=32, max_probes=12, max_suffix=16, budget=120,
        gate=T.run_lean_gate):
    prefix, checkpoint, level = validate_source(source)
    actions = tuple(dict.fromkeys(map(F.atom, actions)))
    if not actions or len(prefix) >= budget:
        raise ValueError("Invalid action or deployment bound")
    if max_training_actions < source["training_actions"] or max_episodes < source["training_episodes"]:
        raise ValueError("Source exceeds cumulative bound")
    if any(a not in set(actions) for a in prefix):
        raise ValueError("Source actions absent from public grammar")
    meter = M.ActionMeter(factory, source["training_actions"],
                          source["training_episodes"], max_training_actions, max_episodes)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    result = {"status": "NO_PROGRESS_WITHIN_BOUND", "source_run": ARCHIVE_RUN,
              "source_commit": T.FROZEN, "initial_sha256": source["initial_sha256"],
              "checkpoint_sha256": checkpoint, "grounded_actions": len(actions),
              "source_training_actions": source["training_actions"],
              "model_calls": 0, "competition_submission": False,
              "accepted": list(source["accepted"]), "new_discoveries": 0,
              "new_installed_options": 0, "traces": [], "terminal_win": False}
    warm = None
    best = None

    def finish(status):
        result.update(status=status, training_actions=meter.actions,
                      training_episodes=meter.episodes,
                      levels_witnessed=max(a["level"] for a in result["accepted"]),
                      installed_options=source["installed_options"] + result["new_installed_options"])
        if warm is not None:
            result["warm"] = M.compact(warm)
            result["terminal_win"] = warm["state"] == "WIN"
        return result

    def replay(path, expected=None):
        meter.reserve(len(path), 1)
        return F.replay(meter.factory, path, expected, budget)

    # Recheck the exact prior policy through the actual shared gate.
    source_stage = {"level": level, "prefix": prefix, "checkpoint_sha256": checkpoint}
    try:
        meter.reserve(2 * len(prefix), 2)
        approval = T.promote(meter.factory, prefix, source_stage, source["cold"],
                             source["initial_sha256"], F.FeedbackArchive(),
                             output / "source-gate", gate=gate)
    except M.TrainingLimit:
        return finish("TRAINING_BOUND_EXHAUSTED")
    except (ValueError, subprocess.CalledProcessError, FileNotFoundError) as exc:
        result["verifier_error"] = str(exc)
        return finish("INCONCLUSIVE_VERIFIER")
    if approval["status"] != "REPLAY_GATED_PROMOTION_PASS":
        return finish(approval["status"])
    if approval["identity"] != source["accepted"][-1]["promotion"]:
        return finish("INCONCLUSIVE_SOURCE_IDENTITY")
    result["source_approval"] = approval["status"]
    result["source_gate_source_sha256"] = approval["approval"]["source_sha256"]
    result["source_gate_identity"] = approval["identity"]
    warm = approval["evidence"]["proof"]
    entry = warm["observations"][-1]
    if F.digest(entry) != checkpoint or warm["levels_completed"] != level:
        return finish("INCONCLUSIVE_PREFIX_MISMATCH")

    options = [tuple(map(F.atom, a["suffix"])) for a in source["accepted"]]
    plan = probes(actions, entry, options, max_probes, max_suffix)
    result["probe_plan"] = [{"program": p, "source": s} for p, s in plan]
    for suffix, constructor in plan:
        requested = prefix + suffix
        if len(requested) > budget:
            continue
        try:
            # A possible promotion must fit before the experiment begins.
            meter.reserve(3 * len(requested), 3)
            trial = replay(requested)
        except M.TrainingLimit:
            result["pending_probe"] = suffix
            break
        if (trial["initial_sha256"] != source["initial_sha256"] or
                trial["status"] not in ("OBSERVED", "OBSERVED_TERMINAL_PREFIX") or
                tuple(trial["executed"][:len(prefix)]) != prefix or
                F.digest(trial["observations"][len(prefix)]) != checkpoint):
            return finish("INCONCLUSIVE_REPLAY")
        actual = tuple(trial["executed"][len(prefix):])
        observed = trial["observations"][len(prefix):]
        hashes = [F.digest(o) for o in observed]
        novelty = len(set(hashes[1:]) - {hashes[0]})
        record = {"source": constructor, "requested": suffix, "executed": actual,
                  "status": trial["status"], "initial_sha256": trial["initial_sha256"],
                  "final_sha256": trial["final_sha256"], "levels_completed": trial["levels_completed"],
                  "state": trial["state"], "novel_observations": novelty,
                  "trace_sha256": F.digest(observed), "delta": frame_delta(entry, observed[-1]),
                  "observations": observed}
        result["traces"].append(record)
        score = (trial["state"] == "WIN", trial["levels_completed"], novelty, -len(actual))
        if best is None or score > best[0]:
            best = (score, record, trial)
        if trial["levels_completed"] <= level and trial["state"] != "WIN":
            continue

        # A new capability is never installed from a stored score or unexecuted tail.
        full = prefix + actual
        stage = {"level": trial["levels_completed"], "prefix": full,
                 "checkpoint_sha256": trial["final_sha256"]}
        archive = F.FeedbackArchive()
        try:
            promotion = T.promote(meter.factory, full, stage, source["cold"],
                                  source["initial_sha256"], archive,
                                  output / "new-gate", gate=gate)
        except M.TrainingLimit:
            result["pending_promotion"] = full
            return finish("TRAINING_BOUND_EXHAUSTED")
        except (ValueError, subprocess.CalledProcessError, FileNotFoundError) as exc:
            result["verifier_error"] = str(exc)
            return finish("INCONCLUSIVE_VERIFIER")
        if promotion["status"] != "REPLAY_GATED_PROMOTION_PASS":
            return finish(promotion["status"])
        proof = promotion["evidence"]["proof"]
        archive.install(F.digest(proof["observations"][len(prefix)]), actual,
                        proof["final_sha256"], proof, entry_path=prefix,
                        source=("policy", promotion["identity"]))
        result["new_installed_options"] = archive.snapshot()["options"]
        result["new_discoveries"] = 1
        result["accepted"].append({"level": stage["level"], "prefix": full, "suffix": actual,
                                   "checkpoint_sha256": stage["checkpoint_sha256"],
                                   "promotion": promotion["identity"],
                                   "gate_source_sha256": promotion["approval"]["source_sha256"]})
        result["checkpoint_sha256"] = stage["checkpoint_sha256"]
        warm = proof
        return finish("VERIFIED_WIN" if proof["state"] == "WIN" else "PROGRESS_WITNESSED")

    if best is None:
        return finish("TRAINING_BOUND_EXHAUSTED" if result.get("pending_probe") else "NO_PROGRESS_WITHIN_BOUND")
    _, record, trial = best
    result["selected_probe"] = {k: v for k, v in record.items() if k != "observations"}
    try:
        proof = replay(prefix + tuple(record["executed"]), trial["final_sha256"])
    except M.TrainingLimit:
        result["pending_proof"] = prefix + tuple(record["executed"])
        return finish("TRAINING_BOUND_EXHAUSTED")
    if (proof["status"] != trial["status"] or proof["executed"] != trial["executed"]
            or proof["observations"] != trial["observations"]
            or proof["initial_sha256"] != source["initial_sha256"]):
        return finish("INCONCLUSIVE_REPLAY")
    result["selected_probe"]["replay_confirmed"] = True
    return finish("OBSERVED_RESIDUAL" if record["novel_observations"] else "NO_OBSERVATION_CHANGE_WITHIN_BOUND")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source-evidence", required=True)
    p.add_argument("--frozen-dir", required=True)
    p.add_argument("--environments-dir", required=True)
    p.add_argument("--game", default="bt33-a7c3f9d18b4e")
    p.add_argument("--output", default="arc3-level4-probe.json")
    args = p.parse_args()
    _, _, grounding, _, _ = T.load_frozen(args.frozen_dir)
    from arc_agi import Arcade, OperationMode
    logger = logging.getLogger("arc3-level4-probe")
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.WARNING)
    def factory():
        arcade = Arcade(operation_mode=OperationMode.OFFLINE,
                        environments_dir=args.environments_dir, logger=logger)
        env = arcade.make(args.game)
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
    actions, unsupported = grounding.action_catalog(first.action_space, first.observation_space, 1, 4096)
    first.close()
    source = json.loads(Path(args.source_evidence).read_text())
    result = run(factory, actions, source, Path(args.output).parent / "level4-gate")
    result.update(game=args.game, mode="offline", unsupported_action_ids=unsupported,
                  upstream_commit=T.UPSTREAM, source_blobs=T.SOURCE_BLOBS)
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True, default=str) + "\n")
    print("ARC3_LEVEL4_PROBE=" + json.dumps({k: result.get(k) for k in
          ("status","training_actions","training_episodes","levels_witnessed",
           "installed_options","new_discoveries","terminal_win")}, sort_keys=True))


if __name__ == "__main__":
    main()

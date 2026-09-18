"""Operationally consume the exact ls20 replay-bisimulation certificates.

This does NOT promote the failed global visual normalization.  It first
reproduces the active separator + recursive closure evidence, verifies the
certificate classes against the resulting quotient, then canonicalizes only
those exact certified public-state digests in developmental memory/exploration
keys.

Raw observation hashes, effect authority, protected outcomes and environment
replay remain unchanged.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys
from types import MethodType

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "ls20-certified-state-compile-results"
AGENT = OUT / "agent.py"
sys.path.insert(0, str(ROOT / "kaggle" / "scripts"))

import interventional_separator_probe as sep
import equivalence_factor_diagnostic as factors

sep.OUT = OUT
sep.AGENT = AGENT
factors.OUT = OUT
factors.AGENT = AGENT


def certified_mapping(module, game_id, envdir, max_actions):
    q_module, q, prefixes, source_meta = sep.build_frozen_trace(
        game_id, envdir, max_actions
    )
    if q_module is not module:
        # load_agent returns a module object; identity is not semantically
        # important, but the frozen hashes are pinned by workflow.
        pass
    source_nodes = set(q.nodes)
    classes0 = q.partitions(max_depth=max(8, len(q.nodes)))[-1]
    candidates = sep.merged_pairs(classes0, source_nodes)
    if len(candidates) != 15:
        raise AssertionError("ls20 observer residual changed")

    results = factors.reproduce_certificate_context(
        module, q, prefixes, game_id, envdir, candidates
    )
    if not all(
        row["status"] == "CLOSED_BOUNDED_REPLAY_BISIMULATION"
        for row in results
    ):
        raise AssertionError("ls20 closure certificate failed to reproduce")

    final_classes = q.partitions(max_depth=max(8, len(q.nodes)))[-1]
    mapping = {}
    class_rows = []
    for class_id, group in enumerate(factors.CLASSES):
        present = [node for node in group if node in q.nodes]
        if len(present) != len(group):
            raise AssertionError("certificate class member missing after replay")
        quotient_ids = {final_classes[node] for node in present}
        if len(quotient_ids) != 1:
            raise AssertionError("hard-coded certificate class no longer closes")
        representative = min(present)
        for node in present:
            mapping[node] = representative
        class_rows.append({
            "class_id": class_id,
            "size": len(present),
            "representative": representative,
            "members": list(present),
            "source_members": sum(node in source_nodes for node in present),
        })
    return mapping, class_rows, source_meta


def install_memory_overlay(controller, mapping, counters):
    def token(obs):
        rep = mapping.get(obs.evidence_sha256)
        if rep is None:
            return obs.frame_digest
        counters["certified_state_key_uses"] += 1
        counters[f"class:{rep[:12]}"] += 1
        return ("QCK", rep)

    def memory_context(self, obs):
        return (
            obs.levels_completed,
            obs.state,
            obs.available_actions,
            obs.height,
            obs.width,
            token(obs),
        )

    def retention_guard(self, obs):
        return (
            obs.levels_completed,
            obs.state,
            obs.available_actions,
            token(obs),
        )

    def exploration_guard(self, obs):
        base = (
            obs.levels_completed,
            obs.state,
            obs.available_actions,
            obs.height,
            obs.width,
        )
        if self._archive_completed:
            return base + (token(obs),)
        return base

    controller._memory_context = MethodType(memory_context, controller)
    controller._retention_guard = MethodType(retention_guard, controller)
    controller._exploration_guard = MethodType(exploration_guard, controller)


def run_arm(module, game_id, envdir, max_actions, mapping=None):
    from arc_agi import Arcade, OperationMode

    arc = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=envdir,
        logger=audit.quiet_logger(),
    )
    env = arc.make(game_id, seed=0)
    if env is None:
        raise RuntimeError("offline ls20 unavailable")

    policy = module.MyAgent(
        card_id="ls20-certified-state-compile",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    policy.controller.archived_capabilities = ()

    counters = Counter()
    if mapping:
        install_memory_overlay(policy.controller, mapping, counters)

    latest = policy._convert_raw_frame_data(env.observation_space)
    frames = [latest]
    actions = []
    sources = Counter()
    zero_change = 0
    max_level = int(latest.levels_completed)
    milestones = []
    mapped_state_visits = 0

    while len(actions) + 1 < max_actions and audit.state_name(latest) != "WIN":
        if policy.is_done(frames, latest):
            break

        before = latest
        before_digest = module.normalize_frame(before).evidence_sha256
        if mapping and before_digest in mapping:
            mapped_state_visits += 1
        before_level = int(before.levels_completed)

        chosen = policy.choose_action(frames, before)
        data = audit.validate_action(chosen, before)
        key = (
            int(chosen.value),
            None if data.get("x") is None else int(data.get("x")),
            None if data.get("y") is None else int(data.get("y")),
        )
        reasoning = getattr(chosen, "reasoning", {})
        source = (
            str(reasoning.get("source", "unknown"))
            if isinstance(reasoning, dict)
            else "unknown"
        )

        raw = env.step(chosen, data=data, reasoning={"source": source})
        latest = policy._convert_raw_frame_data(raw)
        after_digest = module.normalize_frame(latest).evidence_sha256
        zero_change += int(before_digest == after_digest)
        actions.append(key)
        sources[source] += 1

        if int(latest.levels_completed) > max_level:
            max_level = int(latest.levels_completed)
            milestones.append({"level": max_level, "actions": len(actions) + 1})
        frames.append(latest)

    arc.close_scorecard()
    memory = policy.controller.memory
    return {
        "actions": len(actions) + 1,
        "action_sequence": [list(a) for a in actions],
        "distinct_actions": len(set(actions)),
        "zero_observation_change": zero_change,
        "max_levels": max_level,
        "milestones": milestones,
        "final_state": audit.state_name(latest),
        "source_counts": dict(sources),
        "mapped_state_visits": mapped_state_visits,
        "certified_state_key_uses": counters["certified_state_key_uses"],
        "memory": {
            "attempt_facts": int(memory.attempt_fact_count),
            "branching_facts": int(memory.branching_fact_count),
            "refuted_programs": int(memory.refuted_count),
            "capabilities": int(memory.capability_count),
            "digest": memory.digest(),
        },
        "effect_authority": {
            "total_observations": int(policy.controller.effects.total_observations),
            "raw_context_catalogs": len(policy.controller.effects.catalogs),
        },
    }


def compact(row):
    return {k: v for k, v in row.items() if k != "action_sequence"}


def first_divergence(left, right):
    for i, (a, b) in enumerate(zip(left, right), start=1):
        if a != b:
            return {"action_index": i, "baseline": a, "compiled": b}
    if len(left) != len(right):
        return {
            "action_index": min(len(left), len(right)) + 1,
            "baseline_length": len(left),
            "compiled_length": len(right),
        }
    return None


def main():
    public = json.loads((OUT / "public.json").read_text())
    game = next(
        row for row in public["games"]
        if row["game_id"].startswith("ls20-")
    )
    game_id = game["game_id"]

    audit.AGENT = AGENT
    module = audit.load_agent()
    audit.block_network()

    mapping, class_rows, source_meta = certified_mapping(
        module,
        game_id,
        public["environments_dir"],
        public["max_actions"],
    )

    baseline = run_arm(
        module, game_id, public["environments_dir"], public["max_actions"]
    )
    compiled = run_arm(
        module,
        game_id,
        public["environments_dir"],
        public["max_actions"],
        mapping=mapping,
    )

    if baseline["max_levels"] != 0:
        raise AssertionError("frozen ls20 baseline changed")
    if compiled["max_levels"] < baseline["max_levels"]:
        raise AssertionError("certified state quotient regressed protected progress")

    activated = compiled["mapped_state_visits"] > 0
    result = {
        "status": (
            "CERTIFIED_STATE_QUOTIENT_ACTIVE"
            if activated
            else "CERTIFIED_STATE_QUOTIENT_NOT_REACHED_ON_SOURCE_TRACE"
        ),
        "interpretation": (
            "exact replay-bisimulation classes compiled only into developmental "
            "memory/exploration keys; failed global visual normalization is not used"
        ),
        "authority_separation": (
            "raw evidence_sha256, effects, protected outcomes and environment "
            "transitions remain unquotiented"
        ),
        "game_id": game_id,
        "source_trace": source_meta,
        "class_count": len(class_rows),
        "mapped_state_count": len(mapping),
        "classes": class_rows,
        "baseline": compact(baseline),
        "compiled": compact(compiled),
        "memory_delta": {
            key: int(compiled["memory"][key]) - int(baseline["memory"][key])
            for key in (
                "attempt_facts", "branching_facts",
                "refuted_programs", "capabilities",
            )
        },
        "first_action_divergence": first_divergence(
            baseline["action_sequence"], compiled["action_sequence"]
        ),
    }
    audit.write_json(OUT / "ls20-certified-state-compile.json", result)
    print(
        "LS20_CERTIFIED_STATE_COMPILE_RESULT="
        + json.dumps(result, sort_keys=True),
        flush=True,
    )
    print("ARC3_LS20_CERTIFIED_STATE_COMPILE=PASS", flush=True)


if __name__ == "__main__":
    main()

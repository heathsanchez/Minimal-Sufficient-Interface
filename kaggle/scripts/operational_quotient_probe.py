"""Compile grounded QCK certificates into developmental memory keys.

Authority stays raw: public observations, protected outcomes, effect evidence and
replay checks are unchanged.  Only the controller's retention / .mg context keys
are canonicalized for state pairs that the preceding grounded continuation
probe actually closed.

If no grounded certificates exist, this gate records that fact and exits green;
it never promotes UNKNOWN or separated pairs.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "grounded-interventional-v2-results"
AGENT = OUT / "agent.py"
REPORT = OUT / "grounded-interventional-v2.json"


class UnionFind:
    def __init__(self):
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        lo, hi = sorted((ra, rb))
        self.parent[hi] = lo

    def mapping(self) -> dict[str, str]:
        groups: dict[str, list[str]] = {}
        for node in list(self.parent):
            groups.setdefault(self.find(node), []).append(node)
        out = {}
        for members in groups.values():
            rep = min(members)
            if len(members) < 2:
                continue
            for node in members:
                out[node] = rep
        return out


def certificate_mapping(report: dict) -> tuple[dict[str, str], dict]:
    uf = UnionFind()
    closed_roots = []
    closed_pair_count = 0

    for row in report["vc33"]["closure_results"]:
        if row["status"] != "CLOSED_BOUNDED_GROUNDED_BISIMULATION":
            continue
        closed_roots.append(tuple(row["root"]))
        for item in row.get("closed_pairs", []):
            left, right = item["pair"]
            uf.union(str(left), str(right))
            closed_pair_count += 1

    mapping = uf.mapping()
    return mapping, {
        "closed_roots": len(closed_roots),
        "closed_pair_obligations": closed_pair_count,
        "mapped_raw_states": len(mapping),
        "quotient_classes": len(set(mapping.values())),
    }


def install_memory_overlay(controller: Any, mapping: dict[str, str], hits: Counter) -> None:
    def canonical_token(obs):
        rep = mapping.get(obs.evidence_sha256)
        if rep is None:
            return obs.frame_digest
        hits["certified_state_visits"] += 1
        return ("QCK", rep)

    def memory_context(obs):
        return (
            obs.levels_completed,
            obs.state,
            obs.available_actions,
            obs.height,
            obs.width,
            canonical_token(obs),
        )

    def retention_guard(obs):
        return (
            obs.levels_completed,
            obs.state,
            obs.available_actions,
            canonical_token(obs),
        )

    def exploration_guard(obs):
        base = (
            obs.levels_completed,
            obs.state,
            obs.available_actions,
            obs.height,
            obs.width,
        )
        if controller._archive_completed:
            return base + (canonical_token(obs),)
        return base

    # Instance-level functions deliberately override the static/class methods
    # used by the controller.  Raw evidence_sha256 remains untouched everywhere
    # else, especially consequence/effect authority.
    controller._memory_context = memory_context
    controller._retention_guard = retention_guard
    controller._exploration_guard = exploration_guard


def run_arm(module, game_id: str, envdir: str, max_actions: int, mapping: dict[str, str] | None):
    from arc_agi import Arcade, OperationMode

    arc = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=envdir,
        logger=audit.quiet_logger(),
    )
    env = arc.make(game_id, seed=0)
    if env is None:
        raise RuntimeError("offline vc33 unavailable")

    policy = module.MyAgent(
        card_id="qck-operational-compile",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    policy.controller.archived_capabilities = ()

    hits: Counter[str] = Counter()
    if mapping:
        install_memory_overlay(policy.controller, mapping, hits)

    latest = policy._convert_raw_frame_data(env.observation_space)
    frames = [latest]
    actions = []
    milestones = []
    max_level = int(latest.levels_completed)
    source_counts: Counter[str] = Counter()
    state_visits = Counter()

    while len(actions) + 1 < max_actions and audit.state_name(latest) != "WIN":
        if policy.is_done(frames, latest):
            break

        normalized = module.normalize_frame(latest)
        state_visits[normalized.evidence_sha256] += 1

        before_level = int(latest.levels_completed)
        chosen = policy.choose_action(frames, latest)
        data = audit.validate_action(chosen, latest)
        reasoning = getattr(chosen, "reasoning", {})
        source = (
            str(reasoning.get("source", "unknown"))
            if isinstance(reasoning, dict)
            else "unknown"
        )
        key = (
            int(chosen.value),
            None if data.get("x") is None else int(data.get("x")),
            None if data.get("y") is None else int(data.get("y")),
        )

        raw = env.step(chosen, data=data, reasoning={"source": source})
        latest = policy._convert_raw_frame_data(raw)
        actions.append(key)
        source_counts[source] += 1

        if int(latest.levels_completed) > max_level:
            max_level = int(latest.levels_completed)
            milestones.append({"level": max_level, "actions": len(actions) + 1})
        frames.append(latest)

    arc.close_scorecard()
    memory = policy.controller.memory

    return {
        "actions": len(actions) + 1,
        "action_sequence": actions,
        "milestones": milestones,
        "max_levels": max_level,
        "final_state": audit.state_name(latest),
        "source_counts": dict(source_counts),
        "certified_state_visits": int(hits["certified_state_visits"]),
        "distinct_public_states": len(state_visits),
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


def first_divergence(left: list, right: list):
    for index, (a, b) in enumerate(zip(left, right), start=1):
        if tuple(a) != tuple(b):
            return {"action_index": index, "raw": a, "certified": b}
    if len(left) != len(right):
        return {
            "action_index": min(len(left), len(right)) + 1,
            "raw_length": len(left),
            "certified_length": len(right),
        }
    return None


def compact(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "action_sequence"}


def main() -> None:
    report = json.loads(REPORT.read_text())
    mapping, cert = certificate_mapping(report)

    public = json.loads((OUT / "public.json").read_text())
    game = next(row for row in public["games"] if row["game_id"].startswith("vc33-"))

    if not mapping:
        result = {
            "status": "NO_CERTIFIED_GROUNDED_CLASSES_TO_COMPILE",
            "certificate": cert,
            "claim_boundary": "UNKNOWN and separated pairs were not promoted",
        }
        audit.write_json(OUT / "operational-quotient.json", result)
        print("QCK_OPERATIONAL_COMPILE=" + json.dumps(result, sort_keys=True), flush=True)
        print("ARC3_QCK_OPERATIONAL_COMPILE=PASS", flush=True)
        return

    audit.AGENT = AGENT
    module = audit.load_agent()
    audit.block_network()

    raw = run_arm(
        module,
        game["game_id"],
        public["environments_dir"],
        public["max_actions"],
        None,
    )
    certified = run_arm(
        module,
        game["game_id"],
        public["environments_dir"],
        public["max_actions"],
        mapping,
    )

    # The protected source milestone is an authority gate, not an optimization
    # target.  A compiled quotient may change internal memory, but not this.
    expected = [
        {"level": 1, "actions": 64},
        {"level": 2, "actions": 93},
    ]
    if raw["milestones"][:2] != expected:
        raise AssertionError("raw source milestone drifted from frozen vc33 evidence")
    if certified["milestones"][:2] != expected:
        raise AssertionError("certified quotient changed protected vc33 milestones")
    if certified["max_levels"] != raw["max_levels"]:
        raise AssertionError("certified quotient changed protected achieved level count")
    activated = certified["certified_state_visits"] > 0
    terminal_only = bool(
        report["vc33"].get("residual_root_contracts")
        and all(
            bool(row.get("terminal"))
            for row in report["vc33"]["residual_root_contracts"]
        )
    )

    result = {
        "status": (
            "CERTIFIED_MEMORY_QUOTIENT_ACTIVE"
            if activated
            else (
                "CERTIFIED_TERMINAL_EQUIVALENCE_NO_DECISION_EFFECT"
                if terminal_only
                else "CERTIFIED_QUOTIENT_NOT_REACHED_AS_DECISION_CONTEXT"
            )
        ),
        "certificate": cert,
        "mapping": mapping,
        "authority_separation": (
            "only retention/.mg context keys canonicalized; raw public evidence, "
            "effect authority, protected outcomes and replay checks remain exact"
        ),
        "activated_on_decision_context": activated,
        "terminal_only_certificate": terminal_only,
        "raw": compact(raw),
        "certified": compact(certified),
        "first_action_divergence": first_divergence(
            raw["action_sequence"], certified["action_sequence"]
        ),
        "memory_delta": {
            key: int(certified["memory"][key]) - int(raw["memory"][key])
            for key in ("attempt_facts", "branching_facts", "refuted_programs", "capabilities")
        },
    }
    audit.write_json(OUT / "operational-quotient.json", result)
    print("QCK_OPERATIONAL_COMPILE=" + json.dumps(result, sort_keys=True), flush=True)
    print("ARC3_QCK_OPERATIONAL_COMPILE=PASS", flush=True)


if __name__ == "__main__":
    main()

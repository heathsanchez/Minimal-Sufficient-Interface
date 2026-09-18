"""Performance V2: productive-frontier planning for ft09.

V1 showed that "try any unobserved exact action" is a bad performance objective:
it produced 392 no-op actions out of 399 planner choices. V2 keeps the exact
portfolio bank and certified G1 action quotient, but adds a conservative
productivity prior derived only from exact observations at the same context.

At a context:
  1. identify exact known actions that changed the public state;
  2. permit at most two untried Action-6 neighbors near those productive anchors;
  3. otherwise prefer a verified state-changing edge to the least visited target;
  4. otherwise route through deterministic known edges to the nearest context
     that has productive anchors plus an unresolved nearby action;
  5. otherwise fall back to the frozen controller.

Qualification is score-facing: compared with the same banked parent, V2 must
either increase protected level progress or reduce zero-observation-change
actions. No pure evidence-frontier gain is sufficient.
"""
from __future__ import annotations

from collections import Counter, deque
import json
from pathlib import Path
import sys
from types import MethodType

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "productive-frontier-performance-v2-results"
AGENT = OUT / "agent.py"
sys.path.insert(0, str(ROOT / "kaggle" / "scripts"))

import exact_evidence_portfolio as portfolio
import action_quotient_reinvest as gen1

portfolio.OUT = OUT
portfolio.AGENT = AGENT
portfolio.gen1.OUT = OUT
portfolio.gen1.AGENT = AGENT
portfolio.gen1.stable.OUT = OUT
portfolio.gen1.stable.AGENT = AGENT
portfolio.gen1.stable.aq.OUT = OUT
portfolio.gen1.stable.aq.AGENT = AGENT
portfolio.gen1.stable.transfer.OUT = OUT
portfolio.gen1.stable.transfer.AGENT = AGENT

gen1.OUT = OUT
gen1.AGENT = AGENT
gen1.stable.OUT = OUT
gen1.stable.AGENT = AGENT
gen1.stable.aq.OUT = OUT
gen1.stable.aq.AGENT = AGENT
gen1.stable.transfer.OUT = OUT
gen1.stable.transfer.AGENT = AGENT

aq = gen1.stable.aq

MAX_GRAPH_STATES = 2048
LOCAL_NEIGHBOR_TRIALS = 2
MAX_NEIGHBOR_DISTANCE = 8


def deterministic_target(effects, context, action):
    row = effects.edges.get((str(context), tuple(action)))
    if not row or row.get("terminal") or row.get("ambiguous"):
        return None
    outcomes = row.get("outcomes", {})
    if len(outcomes) != 1:
        return None
    return str(next(iter(outcomes)))


def productive_known_actions(effects, context):
    rows = []
    for (source, action), row in effects.edges.items():
        if source != str(context):
            continue
        if int(row.get("changed", 0)) <= 0:
            continue
        target = deterministic_target(effects, context, action)
        if target is None or target == str(context):
            continue
        rows.append((tuple(action), target, row))
    return rows


def neighbor_distance(action, anchor):
    if action[0] != 6 or anchor[0] != 6:
        return 10**9
    if action[1] is None or action[2] is None or anchor[1] is None or anchor[2] is None:
        return 10**9
    return abs(int(action[1]) - int(anchor[1])) + abs(int(action[2]) - int(anchor[2]))


def context_has_productive_frontier(effects, context):
    anchors = productive_known_actions(effects, context)
    if not anchors:
        return False
    catalog = tuple(effects.catalogs.get(str(context), ()))
    for action in catalog:
        action = tuple(action)
        if (str(context), action) in effects.edges:
            continue
        if min(neighbor_distance(action, anchor) for anchor, _target, _row in anchors) <= MAX_NEIGHBOR_DISTANCE:
            return True
    return False


def install_productive_planner(controller, counters):
    original = controller._select_probe
    controller._perf_context_visits = Counter()
    controller._perf_neighbor_trials = Counter()

    def select(self, obs, catalog):
        current = str(obs.evidence_sha256)
        self._perf_context_visits[current] += 1
        allowed = {
            self._action_key(token): token
            for token in catalog
        }
        anchors = productive_known_actions(self.effects, current)

        # Small, bounded local interpolation around exact productive actions.
        if anchors and self._perf_neighbor_trials[current] < LOCAL_NEIGHBOR_TRIALS:
            candidates = []
            for key, token in allowed.items():
                if (current, key) in self.effects.edges:
                    continue
                distance = min(
                    neighbor_distance(key, anchor)
                    for anchor, _target, _row in anchors
                )
                if distance <= MAX_NEIGHBOR_DISTANCE:
                    candidates.append((
                        distance,
                        self._candidate_key(token),
                        token,
                    ))
            if candidates:
                candidates.sort(key=lambda row: (row[0], row[1]))
                token = candidates[0][2]
                self._perf_neighbor_trials[current] += 1
                counters["productive_neighbor"] += 1
                counters["productive_neighbor_distance_sum"] += candidates[0][0]
                return self._token(
                    self._action_key(token),
                    "productive_neighbor",
                )

        # Reuse a verified state-changing edge, preferring targets not yet
        # revisited by this performance arm.
        moving = []
        for key, token in allowed.items():
            row = self.effects.edges.get((current, key))
            if not row or int(row.get("changed", 0)) <= 0:
                continue
            target = deterministic_target(self.effects, current, key)
            if target is None or target == current:
                continue
            moving.append((
                int(self._perf_context_visits.get(target, 0)),
                -int(row.get("changed", 0)),
                self._candidate_key(token),
                token,
                target,
            ))
        if moving:
            moving.sort(key=lambda row: (row[0], row[1], row[2]))
            token = moving[0][3]
            counters["known_productive"] += 1
            return self._token(
                self._action_key(token),
                "known_productive",
            )

        # Route only toward contexts that already have evidence of productive
        # interventions and still have a nearby untried action.
        queue = deque([(current, None, 0)])
        seen = {current}
        while queue and len(seen) <= MAX_GRAPH_STATES:
            context, first, depth = queue.popleft()
            if first is not None and context_has_productive_frontier(self.effects, context):
                counters["productive_route"] += 1
                counters["productive_route_depth_sum"] += depth
                return self._token(first, "productive_route")

            for action, target in self.effects.successors(context):
                action = tuple(action)
                if context == current and action not in allowed:
                    continue
                target = str(target)
                if target in seen:
                    continue
                seen.add(target)
                queue.append((
                    target,
                    action if first is None else first,
                    depth + 1,
                ))

        counters["fallback"] += 1
        return original(obs, catalog)

    controller._select_probe = MethodType(select, controller)


def run_policy(
    module,
    game_id,
    envdir,
    max_actions,
    *,
    certified_states,
    classes,
    preload_bank,
    planner,
):
    from arc_agi import Arcade, OperationMode

    arc = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=envdir,
        logger=audit.quiet_logger(),
    )
    env = arc.make(game_id, seed=0)
    if env is None:
        raise RuntimeError("offline ft09 unavailable")

    policy = module.MyAgent(
        card_id="productive-frontier-performance-v2",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    policy.controller.archived_capabilities = ()

    counters = Counter()
    gen1.install_overlay(
        policy.controller,
        set(certified_states),
        classes,
        counters,
        refill=True,
    )
    portfolio.install_exact_bank(
        policy.controller.effects,
        preload_bank,
        counters,
    )
    if planner:
        install_productive_planner(policy.controller, counters)

    latest = policy._convert_raw_frame_data(env.observation_space)
    frames = [latest]
    actions = []
    states = set()
    sources = Counter()
    zero_change = 0
    max_level = int(latest.levels_completed)
    milestones = []

    while len(actions) + 1 < max_actions and audit.state_name(latest) != "WIN":
        if policy.is_done(frames, latest):
            break

        before = latest
        before_digest = module.normalize_frame(before).evidence_sha256
        states.add(before_digest)

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
        states.add(after_digest)
        zero_change += int(before_digest == after_digest)
        actions.append(key)
        sources[source] += 1

        if int(latest.levels_completed) > max_level:
            max_level = int(latest.levels_completed)
            milestones.append({
                "level": max_level,
                "actions": len(actions) + 1,
            })

        frames.append(latest)

    bank = portfolio.export_exact_bank(policy.controller.effects)
    arc.close_scorecard()

    planner_stats = {
        key: int(value)
        for key, value in counters.items()
        if key in (
            "productive_neighbor",
            "productive_neighbor_distance_sum",
            "known_productive",
            "productive_route",
            "productive_route_depth_sum",
            "fallback",
        )
    }
    return {
        "actions_raw": actions,
        "states": states,
        "bank": bank,
        "stats": {
            "actions": len(actions) + 1,
            "unique_state_count": len(states),
            "distinct_actions": len(set(actions)),
            "distinct_action6": len({
                action for action in actions if action[0] == 6
            }),
            "zero_observation_change": zero_change,
            "max_levels": max_level,
            "milestones": milestones,
            "final_state": audit.state_name(latest),
            "source_counts": dict(sources),
            "planner": planner_stats,
            "bank_edge_keys": len(bank["edges"]),
            "bank_catalog_contexts": len(bank["catalogs"]),
        },
    }


def main():
    manifest = json.loads((OUT / "public.json").read_text())
    game = next(
        row for row in manifest["games"]
        if row["game_id"].startswith("ft09-")
    )
    game_id = game["game_id"]

    module, prefixes, visits, protected, trace = aq.collect_trace(
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
    )
    selected, _rows, common, classes, _class_rows = (
        gen1.stable.derive_stable_classes(
            module,
            game_id,
            manifest["environments_dir"],
            prefixes,
            visits,
            protected,
        )
    )
    certified_states = {digest for _count, digest in selected}

    compressed = portfolio.run_arm(
        module,
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
        certified_states=certified_states,
        classes=classes,
        refill=False,
    )
    reinvested = portfolio.run_arm(
        module,
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
        certified_states=certified_states,
        classes=classes,
        refill=True,
    )
    merged_bank = portfolio.merge_banks(
        compressed["bank"],
        reinvested["bank"],
    )

    parent = run_policy(
        module,
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
        certified_states=certified_states,
        classes=classes,
        preload_bank=merged_bank,
        planner=False,
    )
    planned = run_policy(
        module,
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
        certified_states=certified_states,
        classes=classes,
        preload_bank=merged_bank,
        planner=True,
    )

    levels_delta = (
        planned["stats"]["max_levels"] - parent["stats"]["max_levels"]
    )
    zero_delta = (
        planned["stats"]["zero_observation_change"]
        - parent["stats"]["zero_observation_change"]
    )
    if levels_delta < 0:
        raise AssertionError("productive planner regressed protected level progress")
    if levels_delta == 0 and zero_delta >= 0:
        raise AssertionError(
            "productive planner produced no score-facing performance gain"
        )
    if sum(planned["stats"]["planner"].values()) < 1:
        raise AssertionError("productive planner never activated")

    report = {
        "interpretation": (
            "performance V2 converts the exact portfolio bank into a productive "
            "transition prior rather than an unrestricted novelty prior"
        ),
        "claim_boundary": (
            "the only heuristic extrapolation is bounded same-context coordinate "
            "neighborhood search around exact actions with observed public-state "
            "change; all routing edges remain exact and deterministic"
        ),
        "prior_commit": "0a46a6c7132360f1cc10bb29504e7e74917b8b40",
        "game_id": game_id,
        "trace": trace,
        "g1_common_action_count": len(common),
        "g1_class_sizes": [len(group) for group in classes],
        "portfolio_bank": {
            "edge_keys": len(merged_bank["edges"]),
            "catalog_contexts": len(merged_bank["catalogs"]),
            "ambiguous_edges": sum(
                bool(row.get("ambiguous"))
                for row in merged_bank["edges"].values()
            ),
        },
        "parent": parent["stats"],
        "planned": planned["stats"],
        "performance_delta": {
            "levels": levels_delta,
            "zero_change_actions": zero_delta,
            "unique_states": (
                planned["stats"]["unique_state_count"]
                - parent["stats"]["unique_state_count"]
            ),
            "distinct_actions": (
                planned["stats"]["distinct_actions"]
                - parent["stats"]["distinct_actions"]
            ),
        },
        "novel_states_vs_parent": len(
            planned["states"] - parent["states"]
        ),
        "novel_actions_vs_parent": [
            list(action)
            for action in sorted(
                set(planned["actions_raw"]) - set(parent["actions_raw"])
            )
        ],
    }

    audit.write_json(
        OUT / "productive-frontier-performance-v2.json",
        report,
    )
    print(
        "PRODUCTIVE_FRONTIER_PERFORMANCE_V2_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_PRODUCTIVE_FRONTIER_PERFORMANCE_V2=PASS", flush=True)


if __name__ == "__main__":
    main()

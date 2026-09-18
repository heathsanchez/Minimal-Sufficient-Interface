"""Score-facing ft09 performance compounding from the exact evidence portfolio.

The evidence portfolio has already produced a conflict-free exact bank over
hundreds of public contexts. This experiment finally spends that retained
knowledge on action selection rather than only on diagnostics.

At a known context the planner:

1. tries an exact action that is still absent from the retained bank;
2. otherwise follows verified deterministic bank edges along the shortest path
   to a context that still has an untried exact action;
3. if no such frontier is reachable, prefers a verified non-self transition
   into the least revisited known context;
4. otherwise falls back to the unchanged frozen controller.

The Generation-1 certified action quotient remains active at its exact twelve
contexts, so known redundant interventions are not reintroduced.

No descriptor, visual, or cross-context inference is added. Planning is over
exact raw public digests and exact actions only.
"""
from __future__ import annotations

from collections import Counter, deque
import json
from pathlib import Path
import sys
from types import MethodType

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "exact-frontier-performance-results"
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


def _deterministic_target(effects, context, action):
    row = effects.edges.get((str(context), tuple(action)))
    if not row or row.get("terminal") or row.get("ambiguous"):
        return None
    outcomes = row.get("outcomes", {})
    if len(outcomes) != 1:
        return None
    return next(iter(outcomes))


def install_exact_frontier_planner(controller, counters):
    original = controller._select_probe
    controller._planner_context_visits = Counter()

    def select(self, obs, catalog):
        current = str(obs.evidence_sha256)
        self._planner_context_visits[current] += 1
        allowed = {
            self._action_key(token): token
            for token in catalog
        }

        # Cheapest genuinely new evidence: an exact action at the current
        # context with no retained consequence yet.
        local_untried = [
            token
            for key, token in allowed.items()
            if (current, key) not in self.effects.edges
        ]
        if local_untried:
            token = min(local_untried, key=self._candidate_key)
            counters["frontier_local"] += 1
            return self._token(
                self._action_key(token),
                "exact_frontier_local",
            )

        # Otherwise navigate the known deterministic graph to the nearest
        # context that still has an untried catalog action.
        queue = deque([(current, None, 0)])
        seen = {current}
        while queue and len(seen) <= MAX_GRAPH_STATES:
            context, first, depth = queue.popleft()
            known_catalog = (
                tuple(allowed)
                if context == current
                else tuple(self.effects.catalogs.get(context, ()))
            )
            if first is not None and any(
                (context, tuple(action)) not in self.effects.edges
                for action in known_catalog
            ):
                counters["frontier_route"] += 1
                counters["frontier_route_depth_sum"] += depth
                return self._token(first, "exact_frontier_route")

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

        # If the retained graph has no unresolved action frontier, prefer a
        # known state-changing edge that leads to the least revisited context.
        moving = []
        for key, token in allowed.items():
            target = _deterministic_target(self.effects, current, key)
            if target is None or target == current:
                continue
            moving.append((
                int(self._planner_context_visits.get(str(target), 0)),
                self._candidate_key(token),
                token,
                str(target),
            ))
        if moving:
            moving.sort(key=lambda row: (row[0], row[1]))
            _visits, _candidate, token, _target = moving[0]
            counters["known_novel_route"] += 1
            return self._token(
                self._action_key(token),
                "exact_known_route",
            )

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
        card_id="exact-frontier-performance",
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
        install_exact_frontier_planner(policy.controller, counters)

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
            "planner": {
                key: int(value)
                for key, value in counters.items()
                if key.startswith("frontier")
                or key in ("known_novel_route", "fallback")
            },
            "overlay": {
                key: int(value)
                for key, value in counters.items()
                if key not in (
                    "frontier_local",
                    "frontier_route",
                    "frontier_route_depth_sum",
                    "known_novel_route",
                    "fallback",
                )
            },
            "bank_edge_keys": len(bank["edges"]),
            "bank_catalog_contexts": len(bank["catalogs"]),
        },
    }


def compact(row):
    return row["stats"]


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

    banked_parent = run_policy(
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

    if banked_parent["stats"]["max_levels"] < 0:
        raise AssertionError("banked parent invalid")
    if planned["stats"]["max_levels"] < banked_parent["stats"]["max_levels"]:
        raise AssertionError("exact frontier planner regressed protected progress")
    if (
        sum(planned["stats"]["planner"].values()) < 1
    ):
        raise AssertionError("exact frontier planner never activated")

    parent_states = (
        compressed["states"]
        | reinvested["states"]
        | banked_parent["states"]
    )
    report = {
        "interpretation": (
            "score-facing exact-evidence planning: the conflict-free portfolio "
            "bank is used as a deterministic navigation graph toward unresolved "
            "exact action frontiers while certified redundant actions stay pruned"
        ),
        "claim_boundary": (
            "planning uses exact raw context digests, exact actions, exact "
            "deterministic retained successors and exact catalogs only"
        ),
        "prior_commit": "62bec7279a9bfb7d1f1dcdda878d01156d501118",
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
        "banked_parent": compact(banked_parent),
        "planned": compact(planned),
        "performance_delta": {
            "levels": (
                planned["stats"]["max_levels"]
                - banked_parent["stats"]["max_levels"]
            ),
            "zero_change_actions": (
                planned["stats"]["zero_observation_change"]
                - banked_parent["stats"]["zero_observation_change"]
            ),
            "unique_states": (
                planned["stats"]["unique_state_count"]
                - banked_parent["stats"]["unique_state_count"]
            ),
            "distinct_actions": (
                planned["stats"]["distinct_actions"]
                - banked_parent["stats"]["distinct_actions"]
            ),
        },
        "novel_states_vs_parent_portfolio": len(
            planned["states"] - parent_states
        ),
        "novel_actions_vs_banked_parent": [
            list(action)
            for action in sorted(
                set(planned["actions_raw"])
                - set(banked_parent["actions_raw"])
            )
        ],
    }

    audit.write_json(
        OUT / "exact-frontier-performance.json",
        report,
    )
    print(
        "EXACT_FRONTIER_PERFORMANCE_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_EXACT_FRONTIER_PERFORMANCE=PASS", flush=True)


if __name__ == "__main__":
    main()

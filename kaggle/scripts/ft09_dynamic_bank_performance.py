"""Dynamic exact-bank performance compounding for ft09.

A single exact-frontier episode is not enough: every newly learned exact
state/action consequence should be retained across RESET and remove that
acquisition cost from later episodes.

This experiment:
1. derives the already-certified Generation-1 action quotient;
2. builds the conflict-free compression/reinvestment parent bank;
3. runs four 400-action generations against the same mutable exact effect bank;
4. at every context, records the controller's quotient-aware PRIMARY catalog;
5. spends actions only on untried primary interventions or exact routes toward
   contexts with untried primary interventions;
6. exports the enlarged exact bank for future generations.

No descriptor or visual generalization is inherited. Only exact context/action
outcomes and exact primary catalogs persist.
"""
from __future__ import annotations

from collections import Counter, deque
import json
from pathlib import Path
import sys
from types import MethodType

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "ft09-survival-adjusted-performance-results"
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

STRATEGIES = (
    "prior_local_a",
    "route_prior_a",
    "known_first",
    "route_prior_b",
)
MAX_GRAPH_STATES = 4096
FATAL_ACTION = (6, 54, 54)
FATAL_CERTIFICATE = OUT / "ft09-fatal-basin-certificate.json"


def deterministic_target(effects, context, action):
    row = effects.edges.get((str(context), tuple(action)))
    if not row or row.get("terminal") or row.get("ambiguous"):
        return None
    outcomes = row.get("outcomes", {})
    if len(outcomes) != 1:
        return None
    return next(iter(outcomes))


def action_change_prior(effects, action):
    """Proposal score: controllability discounted by exact terminal evidence."""
    action = tuple(action)
    observed = 0
    changed = 0
    contexts = 0
    terminal_contexts = 0
    for (_context, candidate), row in effects.edges.items():
        if tuple(candidate) != action or row.get("ambiguous"):
            continue
        contexts += 1
        terminal_contexts += int(bool(row.get("terminal")))
        observed += int(row.get("n", 0))
        changed += int(row.get("changed", 0))

    change_rate = (changed + 1.0) / (observed + 2.0)
    # One exact terminal context is enough to discount a coordinate strongly.
    survival_discount = 1.0 / (1.0 + terminal_contexts)
    return (
        change_rate * survival_discount,
        contexts,
        observed,
        changed,
        terminal_contexts,
    )

def choose_token(tokens, effects, key_fn):
    return max(
        tokens,
        key=lambda token: (
            action_change_prior(effects, key_fn(token))[0],
            action_change_prior(effects, key_fn(token))[1],
            action_change_prior(effects, key_fn(token))[2],
            tuple(-1 if value is None else value for value in key_fn(token)),
        ),
    )


def install_dynamic_planner(controller, counters, strategy, fatal_contexts):
    original = controller._select_probe
    controller._dynamic_context_visits = Counter()

    def select(self, obs, catalog):
        current = str(obs.evidence_sha256)
        self._dynamic_context_visits[current] += 1

        allowed = {
            self._action_key(token): token
            for token in catalog
        }

        # Capture the quotient-aware PRIMARY catalog immediately, even on a
        # first visit. This makes a newly seen exact context usable by the next
        # generation without waiting for fallback selection to record it.
        primary_keys = tuple(
            self._action_key(token)
            for token in self._primary
            if self._action_key(token) in allowed
        )
        if primary_keys:
            self.effects.note_catalog(current, primary_keys)

        def local_untried_tokens():
            return [
                allowed[key]
                for key in self.effects.catalogs.get(current, ())
                if key in allowed
                and not (current in fatal_contexts and tuple(key) == FATAL_ACTION)
                and (current, tuple(key)) not in self.effects.edges
            ]

        def route_to_frontier():
            queue = deque([(current, None, 0)])
            seen = {current}
            candidates = []
            while queue and len(seen) <= MAX_GRAPH_STATES:
                context, first, depth = queue.popleft()
                known_catalog = tuple(self.effects.catalogs.get(context, ()))
                unknown = [
                    tuple(action)
                    for action in known_catalog
                    if (context, tuple(action)) not in self.effects.edges
                ]
                if first is not None and unknown and first in allowed:
                    best_prior = max(
                        action_change_prior(self.effects, action)
                        for action in unknown
                    )
                    candidates.append((
                        best_prior[0],
                        best_prior[1],
                        best_prior[2],
                        -depth,
                        first,
                        depth,
                    ))

                for action, target in self.effects.successors(context):
                    action = tuple(action)
                    if context in fatal_contexts and action == FATAL_ACTION:
                        continue
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
            if not candidates:
                return None
            candidates.sort(reverse=True)
            _score, _contexts, _obs, _neg_depth, first, depth = candidates[0]
            return first, depth

        moving = []
        for key, token in allowed.items():
            if current in fatal_contexts and tuple(key) == FATAL_ACTION:
                continue
            target = deterministic_target(self.effects, current, key)
            if target is None or target == current:
                continue
            moving.append((
                int(self._dynamic_context_visits.get(str(target), 0)),
                self._candidate_key(token),
                token,
            ))

        if strategy == "known_first" and moving:
            moving.sort(key=lambda row: (row[0], row[1]))
            _visits, _key, token = moving[0]
            counters["known_route"] += 1
            return self._token(
                self._action_key(token),
                "dynamic_known_route",
            )

        if strategy.startswith("route_prior"):
            routed = route_to_frontier()
            if routed is not None:
                first, depth = routed
                counters["frontier_route"] += 1
                counters["frontier_route_depth_sum"] += depth
                return self._token(first, "dynamic_frontier_route")

        local = local_untried_tokens()
        if local:
            token = choose_token(local, self.effects, self._action_key)
            prior = action_change_prior(self.effects, self._action_key(token))
            counters["frontier_local"] += 1
            counters["frontier_local_prior_milli_sum"] += int(prior[0] * 1000)
            counters["frontier_local_support_sum"] += int(prior[2])
            return self._token(
                self._action_key(token),
                "dynamic_frontier_local",
            )

        routed = route_to_frontier()
        if routed is not None:
            first, depth = routed
            counters["frontier_route"] += 1
            counters["frontier_route_depth_sum"] += depth
            return self._token(first, "dynamic_frontier_route")

        for key, token in allowed.items():
            target = deterministic_target(self.effects, current, key)
            if target is None or target == current:
                continue
            moving.append((
                int(self._dynamic_context_visits.get(str(target), 0)),
                self._candidate_key(token),
                token,
            ))
        if moving:
            moving.sort(key=lambda row: (row[0], row[1]))
            _visits, _key, token = moving[0]
            counters["known_route"] += 1
            return self._token(
                self._action_key(token),
                "dynamic_known_route",
            )

        counters["fallback"] += 1
        return original(obs, catalog)

    controller._select_probe = MethodType(select, controller)


def run_generation(
    module,
    game_id,
    envdir,
    max_actions,
    *,
    certified_states,
    classes,
    bank,
    strategy,
    generation,
    fatal_contexts,
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
        card_id=f"ft09-dynamic-bank-g{generation}",
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
        bank,
        counters,
    )
    install_dynamic_planner(
        policy.controller,
        counters,
        strategy,
        fatal_contexts,
    )

    start_edges = len(policy.controller.effects.edges)
    start_catalogs = len(policy.controller.effects.catalogs)

    latest = policy._convert_raw_frame_data(env.observation_space)
    frames = [latest]
    states = set()
    actions = []
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

    next_bank = portfolio.export_exact_bank(policy.controller.effects)
    arc.close_scorecard()

    return next_bank, {
        "generation": generation,
        "strategy": strategy,
        "actions": len(actions) + 1,
        "max_levels": max_level,
        "milestones": milestones,
        "final_state": audit.state_name(latest),
        "unique_state_count": len(states),
        "distinct_actions": len(set(actions)),
        "distinct_action6": len({
            action for action in actions if action[0] == 6
        }),
        "zero_observation_change": zero_change,
        "source_counts": dict(sources),
        "planner": {
            key: int(value)
            for key, value in counters.items()
            if key.startswith("frontier")
            or key in ("known_route", "fallback")
        },
        "bank_edge_keys_before": start_edges,
        "bank_edge_keys_after": len(next_bank["edges"]),
        "bank_edge_growth": len(next_bank["edges"]) - start_edges,
        "bank_catalog_contexts_before": start_catalogs,
        "bank_catalog_contexts_after": len(next_bank["catalogs"]),
        "bank_catalog_growth": len(next_bank["catalogs"]) - start_catalogs,
    }


def serializable_bank(bank):
    return {
        "schema": "arc3-exact-effect-bank-v1",
        "game_id": "ft09-0d8bbf25",
        "agent_sha256": "d9f0b95dfee14613425e8f557808e129b25e8a055ad481800b1024ce45281ead",
        "edges": [
            {
                "context": context,
                "action": list(action),
                "row": row,
            }
            for (context, action), row in sorted(
                bank["edges"].items(),
                key=lambda item: repr(item[0]),
            )
        ],
        "catalogs": {
            context: [list(action) for action in actions]
            for context, actions in sorted(bank["catalogs"].items())
        },
    }


def main():
    certificate = json.loads(FATAL_CERTIFICATE.read_text())
    if certificate.get("status") != "CLOSED_BOUNDED_FATAL_BASIN_CERTIFICATE":
        raise AssertionError("fatal-basin certificate status changed")
    fatal_contexts = set(certificate.get("fatal_source_digests", ()))
    if len(fatal_contexts) != int(certificate.get("fatal_source_states", -1)):
        raise AssertionError("fatal-basin digest set/count mismatch")

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
    bank = portfolio.merge_banks(
        compressed["bank"],
        reinvested["bank"],
    )

    initial_edges = len(bank["edges"])
    initial_catalogs = len(bank["catalogs"])
    generations = []

    for generation, strategy in enumerate(STRATEGIES, start=1):
        bank, row = run_generation(
            module,
            game_id,
            manifest["environments_dir"],
            manifest["max_actions"],
            certified_states=certified_states,
            classes=classes,
            bank=bank,
            strategy=strategy,
            generation=generation,
            fatal_contexts=fatal_contexts,
        )
        if row["max_levels"] < 0:
            raise AssertionError("dynamic ft09 generation invalid")
        generations.append(row)
        print(
            "FT09_DYNAMIC_BANK_GENERATION="
            + json.dumps(row, sort_keys=True),
            flush=True,
        )

    audit.write_json(
        OUT / "dynamic-exact-effect-bank.json",
        serializable_bank(bank),
    )

    report = {
        "interpretation": (
            "performance compounding by retaining exact ft09 effect evidence "
            "while ranking new primary coordinates by survival-adjusted "
            "controllability and excluding the bounded certified (54,54) hazard family"
        ),
        "claim_boundary": (
            "only exact context/action outcomes and exact primary catalogs persist; "
            "survival-adjusted controllability is proposal-only; the (54,54) "
            "exclusion is bounded to the retained fatal-basin evidence"
        ),
        "trace": trace,
        "g1_common_action_count": len(common),
        "g1_class_sizes": [len(group) for group in classes],
        "fatal_basin": {
            "certified_contexts": len(fatal_contexts),
            "suppressed_action": list(FATAL_ACTION),
        },
        "initial_bank": {
            "edge_keys": initial_edges,
            "catalog_contexts": initial_catalogs,
        },
        "generations": generations,
        "final_bank": {
            "edge_keys": len(bank["edges"]),
            "catalog_contexts": len(bank["catalogs"]),
            "edge_growth": len(bank["edges"]) - initial_edges,
            "catalog_growth": len(bank["catalogs"]) - initial_catalogs,
            "ambiguous_edges": sum(
                bool(row.get("ambiguous"))
                for row in bank["edges"].values()
            ),
        },
        "max_level_reached": max(row["max_levels"] for row in generations),
        "min_zero_change_actions": min(
            row["zero_observation_change"] for row in generations
        ),
        "max_unique_states": max(
            row["unique_state_count"] for row in generations
        ),
    }

    audit.write_json(
        OUT / "ft09-dynamic-bank-performance.json",
        report,
    )
    print(
        "FT09_DYNAMIC_BANK_PERFORMANCE_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_FT09_DYNAMIC_BANK_PERFORMANCE=PASS", flush=True)


if __name__ == "__main__":
    main()

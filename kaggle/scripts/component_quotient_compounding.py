"""Compound QCK/QCKN inside the ls20 primitive-action successor cone.

The earlier dead-component run spent 991 exact replay probes and stopped at a
raw-state bound of 256.  This experiment turns that residual into a developmental
loop:

  raw cone
    -> partial consequential quotient
    -> attack the largest surviving merged class
    -> separator or replay-bisimulation certificate
    -> count certified duplicate states as recovered state budget
    -> spend that budget on deeper frontier states
    -> recompute and repeat.

No visual factor, guessed ontology, or hidden environment state is used.  Every
new edge still comes from exact RESET replay and a legal primitive intervention.
UNKNOWN never becomes equivalence merely because a per-root probe budget ends.
"""
from __future__ import annotations

from collections import defaultdict, deque
from itertools import combinations
import json
from pathlib import Path
import sys

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "component-quotient-compounding-results"
AGENT = OUT / "agent.py"
sys.path.insert(0, str(ROOT / "kaggle" / "src"))
sys.path.insert(0, str(ROOT / "kaggle" / "scripts"))

import interventional_dead_component as dead
import interventional_separator_probe as sep
import interventional_closure_probe as closure

dead.OUT = OUT
dead.AGENT = AGENT
dead.sep.OUT = OUT
dead.sep.AGENT = AGENT
dead.closure.OUT = OUT
dead.closure.AGENT = AGENT
sep.OUT = OUT
sep.AGENT = AGENT
closure.OUT = OUT
closure.AGENT = AGENT

BASE_RAW_STATE_BOUND = 256
BASE_PROBE_BOUND = 1024
TOTAL_EXTRA_PROBES = 4096
PER_ROOT_PROBE_CAP = 512
ROUNDS = 4
ROOTS_PER_ROUND = 4


class UnionFind:
    def __init__(self):
        self.parent = {}

    def find(self, x):
        self.parent.setdefault(x, x)
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        lo, hi = sorted((ra, rb))
        self.parent[hi] = lo

    def components(self):
        groups = defaultdict(list)
        for node in list(self.parent):
            groups[self.find(node)].append(node)
        return [sorted(group) for group in groups.values() if len(group) > 1]

    def same(self, a, b):
        return self.find(a) == self.find(b)


def fully_observed(q, node):
    record = q.nodes[node]
    legal = set(record.legal_actions)
    observed = q._observed_actions(node)
    return bool(legal) and legal <= observed


def primitive_contract(q, node):
    record = q.nodes[node]
    legal = tuple(record.legal_actions)
    return (
        bool(legal)
        and not any(action in (0, 6) for action in legal)
        and str(record.protected[0]) not in ("WIN", "GAME_OVER")
    )


def reachable(q):
    seen = {dead.TARGET}
    queue = deque([dead.TARGET])
    while queue:
        source = queue.popleft()
        for rows in q.edges.get(source, {}).values():
            for _outcome, target in rows:
                if target not in seen:
                    seen.add(target)
                    queue.append(target)
    return seen


def quotient_groups(q, nodes):
    parts = q.partitions(max_depth=max(8, len(q.nodes)))
    classes = parts[-1]
    groups = defaultdict(list)
    for node in nodes:
        if node in classes:
            groups[int(classes[node])].append(node)
    merged = [
        sorted(group)
        for group in groups.values()
        if len(group) > 1
    ]
    merged.sort(key=lambda group: (-len(group), group))
    return parts, classes, merged


def group_stats(groups):
    sizes = sorted((len(group) for group in groups), reverse=True)
    return {
        "merged_group_count": len(groups),
        "merged_state_count": sum(sizes),
        "largest_groups": sizes[:12],
        "pair_count": sum(size * (size - 1) // 2 for size in sizes),
    }


def certified_stats(uf):
    groups = uf.components()
    sizes = sorted((len(group) for group in groups), reverse=True)
    return {
        "class_count": len(groups),
        "mapped_states": sum(sizes),
        "saved_raw_states": sum(size - 1 for size in sizes),
        "class_sizes": sizes,
        "classes": groups,
    }


def choose_pair(q, prefix_by_digest, uf, blocked):
    candidates = {
        node
        for node in reachable(q)
        if fully_observed(q, node)
        and primitive_contract(q, node)
    }
    _parts, _classes, groups = quotient_groups(q, candidates)

    for group in groups:
        ordered = sorted(
            group,
            key=lambda node: (len(prefix_by_digest.get(node, (10**9,))), node),
        )
        for left, right in combinations(ordered, 2):
            pair = tuple(sorted((left, right)))
            if pair in blocked or uf.same(left, right):
                continue
            return pair, len(group), group
    return None, 0, []


def expand_reinvestment_frontier(
    q,
    prefix_by_digest,
    explorer,
    allowed_extra_states,
    probe_ceiling,
):
    if allowed_extra_states <= 0:
        return {
            "allowed_extra_states": int(allowed_extra_states),
            "expanded_states": 0,
            "new_probes": 0,
        }

    before_probes = explorer.new_probes
    expanded = 0

    while expanded < allowed_extra_states and explorer.new_probes < probe_ceiling:
        frontier = [
            node
            for node in reachable(q)
            if node in q.nodes
            and not fully_observed(q, node)
            and primitive_contract(q, node)
            and node in prefix_by_digest
        ]
        if not frontier:
            break
        frontier.sort(key=lambda node: (len(prefix_by_digest[node]), node))
        node = frontier[0]

        for action in q.nodes[node].legal_actions:
            if explorer.new_probes >= probe_ceiling:
                break
            explorer.ensure_action(node, int(action))

        if fully_observed(q, node):
            expanded += 1
        else:
            break

    return {
        "allowed_extra_states": int(allowed_extra_states),
        "expanded_states": expanded,
        "new_probes": explorer.new_probes - before_probes,
    }


def main():
    manifest = json.loads((OUT / "public.json").read_text())
    game = next(
        row for row in manifest["games"]
        if row["game_id"].startswith("ls20-")
    )
    game_id = game["game_id"]

    dead.MAX_STATES = BASE_RAW_STATE_BOUND
    dead.MAX_NEW_PROBES = BASE_PROBE_BOUND
    closure.MAX_NEW_PROBES = BASE_PROBE_BOUND

    module, q, prefix_by_digest, source_meta = sep.build_frozen_trace(
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
    )
    original_nodes = set(q.nodes)
    classes = q.partitions(max_depth=max(8, len(q.nodes)))[-1]
    candidates = sep.merged_pairs(classes, original_nodes)
    if len(original_nodes) != 355 or len(candidates) != 15:
        raise AssertionError("frozen ls20 precondition changed")

    survivors, certificate_probes = dead.prepare_certificate_context(
        module,
        q,
        prefix_by_digest,
        game_id,
        manifest["environments_dir"],
        candidates,
    )
    baseline = dead.explore_component(
        module,
        q,
        prefix_by_digest,
        game_id,
        manifest["environments_dir"],
    )
    if baseline["status"] != "UNKNOWN_STATE_BOUND":
        raise AssertionError("dead-component baseline no longer hits state bound")
    if baseline["states"] != BASE_RAW_STATE_BOUND:
        raise AssertionError("dead-component baseline state count changed")

    baseline_sources = {row["source"] for row in baseline["edges"]}
    initial_reachable = reachable(q)
    initial_full = {
        node for node in initial_reachable
        if node in q.nodes and fully_observed(q, node)
    }
    _parts, _classes, initial_groups = quotient_groups(q, initial_full)

    uf = UnionFind()
    blocked = set()
    closer = closure.ClosureProbe(
        module,
        q,
        prefix_by_digest,
        game_id,
        manifest["environments_dir"],
    )
    closer.new_probes = 0
    closure.MAX_PAIR_OBLIGATIONS = 4096

    rounds = []
    total_reinvested_expansions = 0

    for round_index in range(1, ROUNDS + 1):
        round_start_probes = closer.new_probes
        attacks = []

        for _ in range(ROOTS_PER_ROUND):
            if closer.new_probes >= TOTAL_EXTRA_PROBES:
                break
            pair, partial_group_size, partial_group = choose_pair(
                q, prefix_by_digest, uf, blocked
            )
            if pair is None:
                break

            before = closer.new_probes
            closure.MAX_NEW_PROBES = min(
                TOTAL_EXTRA_PROBES,
                closer.new_probes + PER_ROOT_PROBE_CAP,
            )
            try:
                result = closer.close_root(pair)
            except RuntimeError as exc:
                result = {
                    "root": pair,
                    "status": "UNKNOWN_ROOT_PROBE_CAP",
                    "error": str(exc),
                    "pair_obligations": None,
                    "edges": [],
                }

            spent = closer.new_probes - before
            status = result["status"]
            if status == "CLOSED_BOUNDED_REPLAY_BISIMULATION":
                uf.union(*pair)
            else:
                blocked.add(pair)

            attacks.append({
                "root": list(pair),
                "partial_group_size": partial_group_size,
                "partial_group_head": partial_group[:12],
                "status": status,
                "new_probes": spent,
                "pair_obligations": result.get("pair_obligations"),
                "separator_word": result.get("separator_word"),
                "reason": result.get("reason"),
            })

            if closer.new_probes >= TOTAL_EXTRA_PROBES:
                break

        cert = certified_stats(uf)
        allowed_total_reinvest = cert["saved_raw_states"]
        remaining_reinvest = max(
            0, allowed_total_reinvest - total_reinvested_expansions
        )

        closure.MAX_NEW_PROBES = TOTAL_EXTRA_PROBES
        reinvest = expand_reinvestment_frontier(
            q,
            prefix_by_digest,
            closer,
            remaining_reinvest,
            TOTAL_EXTRA_PROBES,
        )
        total_reinvested_expansions += reinvest["expanded_states"]

        now_reachable = reachable(q)
        now_full = {
            node for node in now_reachable
            if node in q.nodes and fully_observed(q, node)
        }
        _p, _c, groups = quotient_groups(q, now_full)

        rounds.append({
            "round": round_index,
            "attacks": attacks,
            "certified": cert,
            "reinvestment": reinvest,
            "reachable_states": len(now_reachable),
            "fully_observed_reachable_states": len(now_full),
            "partial_quotient": group_stats(groups),
            "round_new_probes": closer.new_probes - round_start_probes,
            "total_extra_probes": closer.new_probes,
        })

        if closer.new_probes >= TOTAL_EXTRA_PROBES:
            break
        if not attacks and reinvest["expanded_states"] == 0:
            break

    final_reachable = reachable(q)
    final_full = {
        node for node in final_reachable
        if node in q.nodes and fully_observed(q, node)
    }
    _parts, _classes, final_groups = quotient_groups(q, final_full)
    cert = certified_stats(uf)

    report = {
        "interpretation": (
            "QCK/QCKN compounding inside the exact ls20 primitive-action cone: "
            "partial quotient candidates are actively attacked; only recursively "
            "closed pairs earn reusable state-budget savings, which are immediately "
            "spent on deeper exact frontier expansion"
        ),
        "claim_boundary": (
            "partial quotient groups are hypotheses only; certified savings count "
            "only CLOSED_BOUNDED_REPLAY_BISIMULATION results; capped/unknown roots "
            "remain unmerged"
        ),
        "prior_commit": "51ebf9e532ad6c9d8bae47d57d4b5d88757ec564",
        "game_id": game_id,
        "source_trace": source_meta,
        "initial_candidate_pairs": len(candidates),
        "one_step_survivors": len(survivors),
        "certificate_new_probes": certificate_probes,
        "baseline": {
            "status": baseline["status"],
            "raw_states": baseline["states"],
            "new_probes": baseline["new_probes"],
            "edge_count": len(baseline["edges"]),
            "terminal_states": len(baseline["terminal_states"]),
            "fully_observed_reachable_states": len(initial_full),
            "reachable_states": len(initial_reachable),
            "partial_quotient": group_stats(initial_groups),
        },
        "rounds": rounds,
        "final": {
            "extra_probes": closer.new_probes,
            "reachable_states": len(final_reachable),
            "fully_observed_reachable_states": len(final_full),
            "certified": cert,
            "reinvested_frontier_states": total_reinvested_expansions,
            "partial_quotient": group_stats(final_groups),
        },
    }

    audit.write_json(OUT / "component-quotient-compounding.json", report)
    print(
        "COMPONENT_QUOTIENT_COMPOUNDING_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_COMPONENT_QUOTIENT_COMPOUNDING=PASS", flush=True)


if __name__ == "__main__":
    main()

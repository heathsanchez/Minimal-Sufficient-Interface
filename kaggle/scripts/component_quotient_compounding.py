"""QCK/QCKN cone compounding V2: certify cheap merges, spend immediately.

V1 attacks the largest partial quotient classes. V2 uses a stronger economic
policy: harvest the cheapest high-confidence certificates first. In particular,
a pair of fully observed states whose four primitive actions have identical
outcomes and identical raw successors is a zero-frontier replay-bisimulation
obligation and should be banked before spending hundreds of probes on a deep
uncertain pair.

Each successful certificate immediately earns one raw-state budget credit.
Those credits are spent in the same generation on previously unexpanded
reachable frontier states. The quotient is then recomputed and the process
repeats.

Only CLOSED_BOUNDED_REPLAY_BISIMULATION earns credit. UNKNOWN and separators
never do.
"""
from __future__ import annotations

from collections import defaultdict, deque
from itertools import combinations
import json
from pathlib import Path
import sys

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "component-quotient-compounding-v2-results"
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
PER_ROOT_PROBE_CAP = 384
GENERATIONS = 20


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

    def same(self, a, b):
        return self.find(a) == self.find(b)

    def components(self):
        groups = defaultdict(list)
        for node in list(self.parent):
            groups[self.find(node)].append(node)
        return [
            sorted(group)
            for group in groups.values()
            if len(group) > 1
        ]


def fully_observed(q, node):
    if node not in q.nodes:
        return False
    legal = set(q.nodes[node].legal_actions)
    return bool(legal) and legal <= q._observed_actions(node)


def primitive_contract(q, node):
    if node not in q.nodes:
        return False
    row = q.nodes[node]
    legal = tuple(row.legal_actions)
    return (
        bool(legal)
        and not any(action in (0, 6) for action in legal)
        and str(row.protected[0]) not in ("WIN", "GAME_OVER")
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
    grouped = defaultdict(list)
    for node in nodes:
        if node in classes:
            grouped[int(classes[node])].append(node)
    groups = [
        sorted(group)
        for group in grouped.values()
        if len(group) > 1
    ]
    groups.sort(key=lambda group: (-len(group), group))
    return parts, classes, groups


def group_stats(groups):
    sizes = sorted((len(group) for group in groups), reverse=True)
    return {
        "merged_group_count": len(groups),
        "merged_state_count": sum(sizes),
        "largest_groups": sizes[:16],
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


def prefix_length(prefix_by_digest, node):
    prefix = prefix_by_digest.get(node)
    return len(prefix) if prefix is not None else 10**9


def one_step_pair_cost(q, left, right, uf):
    """Estimate unresolved closure work from already observed one-step edges."""
    frontier = 0
    unresolved = 0
    identical_successors = 0
    outcome_mismatch = 0

    legal = tuple(q.nodes[left].legal_actions)
    if legal != tuple(q.nodes[right].legal_actions):
        return (10**6, 10**6, 0, 1)

    for action in legal:
        lrows = q.edges.get(left, {}).get(int(action), set())
        rrows = q.edges.get(right, {}).get(int(action), set())
        if len(lrows) != 1 or len(rrows) != 1:
            frontier += 10
            unresolved += 10
            continue

        lout, ltarget = next(iter(lrows))
        rout, rtarget = next(iter(rrows))
        if lout != rout:
            outcome_mismatch += 1
            continue
        if ltarget == rtarget:
            identical_successors += 1
            continue
        if uf.same(ltarget, rtarget):
            continue

        unresolved += 1
        if not fully_observed(q, ltarget) or not fully_observed(q, rtarget):
            frontier += 1

    return frontier, unresolved, identical_successors, outcome_mismatch


def choose_pair(q, prefix_by_digest, uf, blocked):
    candidate_nodes = {
        node
        for node in reachable(q)
        if fully_observed(q, node) and primitive_contract(q, node)
    }
    _parts, _classes, groups = quotient_groups(q, candidate_nodes)

    ranked = []
    for group in groups:
        for left, right in combinations(group, 2):
            pair = tuple(sorted((left, right)))
            if pair in blocked or uf.same(left, right):
                continue
            cost = one_step_pair_cost(q, left, right, uf)
            ranked.append((
                cost[0],                        # unexpanded successor obligations
                cost[1],                        # distinct unresolved target pairs
                -cost[2],                       # prefer identical raw successors
                -len(group),                    # then larger potential class
                prefix_length(prefix_by_digest, left)
                + prefix_length(prefix_by_digest, right),
                pair,
                len(group),
                group,
                cost,
            ))

    if not ranked:
        return None
    ranked.sort(key=lambda row: row[:6])
    row = ranked[0]
    return {
        "pair": row[5],
        "partial_group_size": row[6],
        "partial_group": row[7],
        "cost": {
            "frontier_obligations": row[8][0],
            "unresolved_target_pairs": row[8][1],
            "identical_raw_successors": row[8][2],
            "outcome_mismatch": row[8][3],
        },
    }


def expand_one_frontier_state(q, prefix_by_digest, explorer, probe_ceiling):
    frontier = [
        node
        for node in reachable(q)
        if node in prefix_by_digest
        and primitive_contract(q, node)
        and not fully_observed(q, node)
    ]
    if not frontier:
        return None
    frontier.sort(key=lambda node: (prefix_length(prefix_by_digest, node), node))
    node = frontier[0]
    before = explorer.new_probes

    for action in q.nodes[node].legal_actions:
        if explorer.new_probes >= probe_ceiling:
            break
        explorer.ensure_action(node, int(action))

    if not fully_observed(q, node):
        return {
            "state": node,
            "status": "PARTIAL_PROBE_BOUND",
            "new_probes": explorer.new_probes - before,
        }
    return {
        "state": node,
        "status": "EXPANDED",
        "new_probes": explorer.new_probes - before,
        "prefix_length": prefix_length(prefix_by_digest, node),
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
        raise AssertionError("dead-component baseline no longer hits raw-state bound")
    if baseline["states"] != BASE_RAW_STATE_BOUND:
        raise AssertionError("dead-component baseline state count changed")

    initial_reachable = reachable(q)
    initial_full = {
        node
        for node in initial_reachable
        if fully_observed(q, node)
    }
    _p, _c, initial_groups = quotient_groups(q, initial_full)

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

    generations = []
    reinvested_states = 0

    for generation in range(1, GENERATIONS + 1):
        if closer.new_probes >= TOTAL_EXTRA_PROBES:
            break

        before_cert = certified_stats(uf)
        choice = choose_pair(q, prefix_by_digest, uf, blocked)
        attack = None

        if choice is not None:
            pair = choice["pair"]
            before_probes = closer.new_probes
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
                    "separator_word": None,
                    "reason": None,
                }

            status = result["status"]
            if status == "CLOSED_BOUNDED_REPLAY_BISIMULATION":
                uf.union(*pair)
            else:
                blocked.add(pair)

            attack = {
                "root": list(pair),
                "partial_group_size": choice["partial_group_size"],
                "cost": choice["cost"],
                "status": status,
                "new_probes": closer.new_probes - before_probes,
                "pair_obligations": result.get("pair_obligations"),
                "separator_word": result.get("separator_word"),
                "reason": result.get("reason"),
            }

        after_cert = certified_stats(uf)
        newly_earned = max(
            0,
            after_cert["saved_raw_states"] - before_cert["saved_raw_states"],
        )

        # Credits are cumulative. Spend every unspent credit immediately.
        unspent = max(
            0,
            after_cert["saved_raw_states"] - reinvested_states,
        )
        expansion_rows = []
        closure.MAX_NEW_PROBES = TOTAL_EXTRA_PROBES
        while unspent > 0 and closer.new_probes < TOTAL_EXTRA_PROBES:
            row = expand_one_frontier_state(
                q, prefix_by_digest, closer, TOTAL_EXTRA_PROBES
            )
            if row is None:
                break
            expansion_rows.append(row)
            if row["status"] != "EXPANDED":
                break
            reinvested_states += 1
            unspent -= 1

        now_reachable = reachable(q)
        now_full = {
            node
            for node in now_reachable
            if fully_observed(q, node)
        }
        _parts, _classes, groups = quotient_groups(q, now_full)

        generations.append({
            "generation": generation,
            "attack": attack,
            "newly_earned_state_credits": newly_earned,
            "certified": after_cert,
            "reinvestment": {
                "expanded_states": len([
                    row for row in expansion_rows
                    if row["status"] == "EXPANDED"
                ]),
                "rows": expansion_rows,
                "total_reinvested_states": reinvested_states,
                "unspent_credits": max(
                    0,
                    after_cert["saved_raw_states"] - reinvested_states,
                ),
            },
            "reachable_states": len(now_reachable),
            "fully_observed_reachable_states": len(now_full),
            "partial_quotient": group_stats(groups),
            "total_extra_probes": closer.new_probes,
        })

        if choice is None and not expansion_rows:
            break

    final_reachable = reachable(q)
    final_full = {
        node for node in final_reachable
        if fully_observed(q, node)
    }
    _p, _c, final_groups = quotient_groups(q, final_full)
    final_cert = certified_stats(uf)

    report = {
        "interpretation": (
            "low-cost-first QCK/QCKN compounding in the exact ls20 primitive "
            "successor cone: every closed bisimulation pair earns a raw-state "
            "credit that is spent immediately on deeper exact frontier coverage"
        ),
        "claim_boundary": (
            "partial quotient classes only rank attacks; only recursive replay "
            "closure earns credits; separator and capped roots remain distinct"
        ),
        "prior_commit": "2420ed6096dac9538518e4c3bc3e8b625260c014",
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
            "reachable_states": len(initial_reachable),
            "fully_observed_reachable_states": len(initial_full),
            "partial_quotient": group_stats(initial_groups),
        },
        "generations": generations,
        "final": {
            "extra_probes": closer.new_probes,
            "reachable_states": len(final_reachable),
            "fully_observed_reachable_states": len(final_full),
            "certified": final_cert,
            "reinvested_frontier_states": reinvested_states,
            "partial_quotient": group_stats(final_groups),
        },
    }

    audit.write_json(
        OUT / "component-quotient-compounding-v2.json",
        report,
    )
    print(
        "COMPONENT_QUOTIENT_COMPOUNDING_V2_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_COMPONENT_QUOTIENT_COMPOUNDING_V2=PASS", flush=True)


if __name__ == "__main__":
    main()

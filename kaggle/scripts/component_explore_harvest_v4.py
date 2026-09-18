"""ARC3 ls20 V4: explore first, harvest free certificates, persist the ledger.

V1 proved that aggressive partial-quotient attacks can expand the exact primitive
successor cone dramatically (678 -> 1917 reachable states, 284 -> 1310 fully
observed) but earned no reusable equivalence certificates while spending its
4096-probe exploration budget.

V2 proved the complementary fact: cheap fully-observed bisimulation pairs can be
certified at zero additional probe cost and each certificate can immediately buy
deeper frontier coverage.

V4 composes those two lessons in one stateful run:

  baseline exact cone
    -> exploration burst (rich evidence graph)
    -> zero-new-probe certificate harvest over that enriched graph
    -> convert certified duplicate states into raw-state credits
    -> spend credits on deeper exact frontier states
    -> re-harvest newly exposed zero-cost certificates
    -> persist the full exact graph + replay-prefix ledger.

Only CLOSED_BOUNDED_REPLAY_BISIMULATION earns a credit.  UNKNOWN and separated
pairs stay distinct.  The evidence ledger is intended to prevent later
generations from repaying for exact probes already performed.
"""
from __future__ import annotations

from collections import defaultdict, deque
from itertools import combinations
import json
from pathlib import Path
import sys

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "component-explore-harvest-v4-results"
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
EXPLORATION_PROBES = 4096
EXPLORATION_ROOT_CAP = 512
HARVEST_PAIR_ATTEMPTS = 1500
HARVEST_CYCLES = 6
MAX_REINVEST_PROBES = 2048


class UnionFind:
    def __init__(self):
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, a: str, b: str) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        lo, hi = sorted((ra, rb))
        self.parent[hi] = lo
        return True

    def same(self, a: str, b: str) -> bool:
        return self.find(a) == self.find(b)

    def components(self) -> list[list[str]]:
        groups: dict[str, list[str]] = defaultdict(list)
        for node in list(self.parent):
            groups[self.find(node)].append(node)
        return [
            sorted(group)
            for group in groups.values()
            if len(group) > 1
        ]


def fully_observed(q, node: str) -> bool:
    if node not in q.nodes:
        return False
    legal = set(q.nodes[node].legal_actions)
    return bool(legal) and legal <= q._observed_actions(node)


def primitive_contract(q, node: str) -> bool:
    if node not in q.nodes:
        return False
    row = q.nodes[node]
    legal = tuple(row.legal_actions)
    return (
        bool(legal)
        and not any(action in (0, 6) for action in legal)
        and str(row.protected[0]) not in ("WIN", "GAME_OVER")
    )


def reachable(q) -> set[str]:
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


def quotient_groups(q, nodes: set[str]):
    parts = q.partitions(max_depth=max(8, len(q.nodes)))
    classes = parts[-1]
    grouped: dict[int, list[str]] = defaultdict(list)
    for node in nodes:
        if node in classes:
            grouped[int(classes[node])].append(node)
    groups = [
        sorted(group)
        for group in grouped.values()
        if len(group) > 1
    ]
    groups.sort(key=lambda group: (-len(group), group))
    return classes, groups


def group_stats(groups: list[list[str]]) -> dict:
    sizes = sorted((len(group) for group in groups), reverse=True)
    return {
        "merged_group_count": len(groups),
        "merged_state_count": sum(sizes),
        "largest_groups": sizes[:20],
        "pair_count": sum(size * (size - 1) // 2 for size in sizes),
    }


def certified_stats(uf: UnionFind) -> dict:
    groups = uf.components()
    sizes = sorted((len(group) for group in groups), reverse=True)
    return {
        "class_count": len(groups),
        "mapped_states": sum(sizes),
        "saved_raw_states": sum(size - 1 for size in sizes),
        "class_sizes": sizes,
        "classes": groups,
    }


def prefix_length(prefixes, node):
    value = prefixes.get(node)
    return len(value) if value is not None else 10**9


def choose_exploration_pair(q, prefixes, blocked, uf):
    nodes = {
        node
        for node in reachable(q)
        if fully_observed(q, node) and primitive_contract(q, node)
    }
    _classes, groups = quotient_groups(q, nodes)
    for group in groups:
        ordered = sorted(
            group,
            key=lambda node: (prefix_length(prefixes, node), node),
        )
        for left, right in combinations(ordered, 2):
            pair = tuple(sorted((left, right)))
            if pair in blocked or uf.same(*pair):
                continue
            return pair, len(group)
    return None, 0


def one_step_cost(q, left, right, uf):
    if tuple(q.nodes[left].legal_actions) != tuple(q.nodes[right].legal_actions):
        return (10**9, 10**9, 0)
    missing = 0
    unresolved = 0
    identical = 0
    for action in q.nodes[left].legal_actions:
        lrows = q.edges.get(left, {}).get(int(action), set())
        rrows = q.edges.get(right, {}).get(int(action), set())
        if len(lrows) != 1 or len(rrows) != 1:
            missing += 1
            continue
        lout, lt = next(iter(lrows))
        rout, rt = next(iter(rrows))
        if lout != rout:
            return (10**8, 10**8, identical)
        if lt == rt:
            identical += 1
        elif not uf.same(lt, rt):
            unresolved += 1
    return (missing, unresolved, identical)


def ranked_harvest_pairs(q, prefixes, uf, blocked):
    nodes = {
        node
        for node in reachable(q)
        if fully_observed(q, node) and primitive_contract(q, node)
    }
    _classes, groups = quotient_groups(q, nodes)
    rows = []
    for group in groups:
        for left, right in combinations(group, 2):
            pair = tuple(sorted((left, right)))
            if pair in blocked or uf.same(*pair):
                continue
            cost = one_step_cost(q, left, right, uf)
            rows.append((
                cost[0],
                cost[1],
                -cost[2],
                -len(group),
                prefix_length(prefixes, left) + prefix_length(prefixes, right),
                pair,
                len(group),
            ))
    rows.sort()
    return rows


def expand_frontier_credits(
    q,
    prefixes,
    explorer,
    credits: int,
    probe_ceiling: int,
):
    rows = []
    spent_credits = 0
    while spent_credits < credits and explorer.new_probes < probe_ceiling:
        frontier = [
            node
            for node in reachable(q)
            if node in prefixes
            and primitive_contract(q, node)
            and not fully_observed(q, node)
        ]
        if not frontier:
            break
        frontier.sort(key=lambda node: (prefix_length(prefixes, node), node))
        node = frontier[0]
        before = explorer.new_probes
        for action in q.nodes[node].legal_actions:
            if explorer.new_probes >= probe_ceiling:
                break
            explorer.ensure_action(node, int(action))
        status = "EXPANDED" if fully_observed(q, node) else "PROBE_BOUND"
        rows.append({
            "state": node,
            "prefix_length": prefix_length(prefixes, node),
            "status": status,
            "new_probes": explorer.new_probes - before,
        })
        if status != "EXPANDED":
            break
        spent_credits += 1
    return rows


def serialize_ledger(q, prefixes, metadata):
    nodes = {
        str(node): {
            "protected": list(record.protected),
            "legal_actions": [int(action) for action in record.legal_actions],
        }
        for node, record in sorted(q.nodes.items(), key=lambda item: str(item[0]))
    }
    edges = []
    for source in sorted(q.edges, key=str):
        for action in sorted(q.edges[source]):
            for outcome, target in sorted(q.edges[source][action], key=repr):
                edges.append({
                    "source": str(source),
                    "action": int(action),
                    "outcome": list(outcome) if isinstance(outcome, tuple) else outcome,
                    "target": str(target),
                })
    replay_prefixes = {
        str(node): [
            [
                int(action_id),
                None if x is None else int(x),
                None if y is None else int(y),
            ]
            for action_id, x, y in prefix
        ]
        for node, prefix in sorted(prefixes.items())
        if node in q.nodes
    }
    return {
        "schema": "arc3-exact-replay-ledger-v1",
        "metadata": metadata,
        "nodes": nodes,
        "edges": edges,
        "prefixes": replay_prefixes,
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

    module, q, prefixes, source_meta = sep.build_frozen_trace(
        game_id,
        manifest["environments_dir"],
        manifest["max_actions"],
    )
    original_nodes = set(q.nodes)
    initial_classes = q.partitions(max_depth=max(8, len(q.nodes)))[-1]
    candidates = sep.merged_pairs(initial_classes, original_nodes)
    if len(original_nodes) != 355 or len(candidates) != 15:
        raise AssertionError("frozen ls20 precondition changed")

    survivors, certificate_probes = dead.prepare_certificate_context(
        module,
        q,
        prefixes,
        game_id,
        manifest["environments_dir"],
        candidates,
    )
    baseline = dead.explore_component(
        module,
        q,
        prefixes,
        game_id,
        manifest["environments_dir"],
    )
    if baseline["status"] != "UNKNOWN_STATE_BOUND":
        raise AssertionError("baseline no longer hits the 256-state bound")

    baseline_reachable = reachable(q)
    baseline_full = {
        node for node in baseline_reachable if fully_observed(q, node)
    }
    _c, baseline_groups = quotient_groups(q, baseline_full)

    explorer = closure.ClosureProbe(
        module, q, prefixes, game_id, manifest["environments_dir"]
    )
    explorer.new_probes = 0
    closure.MAX_PAIR_OBLIGATIONS = 4096
    blocked = set()
    uf = UnionFind()
    exploration_attacks = []

    # Phase 1: deliberately maximize evidence, reproducing the productive V1
    # behavior. Certificates are accepted if they happen, but are not required.
    while explorer.new_probes < EXPLORATION_PROBES:
        pair, group_size = choose_exploration_pair(q, prefixes, blocked, uf)
        if pair is None:
            break
        before = explorer.new_probes
        closure.MAX_NEW_PROBES = min(
            EXPLORATION_PROBES,
            explorer.new_probes + EXPLORATION_ROOT_CAP,
        )
        try:
            result = explorer.close_root(pair)
        except RuntimeError as exc:
            result = {
                "status": "UNKNOWN_ROOT_PROBE_CAP",
                "root": pair,
                "error": str(exc),
            }
        status = result["status"]
        if status == "CLOSED_BOUNDED_REPLAY_BISIMULATION":
            uf.union(*pair)
        else:
            blocked.add(pair)
        exploration_attacks.append({
            "root": list(pair),
            "partial_group_size": group_size,
            "status": status,
            "new_probes": explorer.new_probes - before,
            "pair_obligations": result.get("pair_obligations"),
            "reason": result.get("reason"),
            "separator_word": result.get("separator_word"),
        })
        if explorer.new_probes >= EXPLORATION_PROBES:
            break

    enriched_reachable = reachable(q)
    enriched_full = {
        node for node in enriched_reachable if fully_observed(q, node)
    }
    _c, enriched_groups = quotient_groups(q, enriched_full)

    # Phase 2: freeze the exploration probe count. Try only closures that need
    # no new environment probe. Any attempted missing edge throws before probing.
    harvest_cycles = []
    reinvested = 0
    reinvest_probe_start = explorer.new_probes
    reinvest_probe_ceiling = EXPLORATION_PROBES + MAX_REINVEST_PROBES

    for cycle in range(1, HARVEST_CYCLES + 1):
        cert_before = certified_stats(uf)
        attempts = 0
        closed = 0
        separated = 0
        needs_more_evidence = 0

        while attempts < HARVEST_PAIR_ATTEMPTS:
            ranked = ranked_harvest_pairs(q, prefixes, uf, blocked)
            if not ranked:
                break
            # Always take the currently cheapest partial-equivalence candidate.
            _missing, _unresolved, _neg_identical, _neg_group, _plen, pair, group_size = ranked[0]
            attempts += 1
            before = explorer.new_probes
            closure.MAX_NEW_PROBES = explorer.new_probes
            try:
                result = explorer.close_root(pair)
            except RuntimeError:
                blocked.add(pair)
                needs_more_evidence += 1
                continue

            if explorer.new_probes != before:
                raise AssertionError("zero-probe harvest unexpectedly performed a probe")

            if result["status"] == "CLOSED_BOUNDED_REPLAY_BISIMULATION":
                if uf.union(*pair):
                    closed += 1
            elif result["status"] == "SEPARATED":
                blocked.add(pair)
                separated += 1
            else:
                blocked.add(pair)
                needs_more_evidence += 1

        cert_after = certified_stats(uf)
        available_credits = max(
            0, cert_after["saved_raw_states"] - reinvested
        )

        closure.MAX_NEW_PROBES = reinvest_probe_ceiling
        expansion_rows = expand_frontier_credits(
            q,
            prefixes,
            explorer,
            available_credits,
            reinvest_probe_ceiling,
        )
        newly_expanded = sum(row["status"] == "EXPANDED" for row in expansion_rows)
        reinvested += newly_expanded

        now_reachable = reachable(q)
        now_full = {
            node for node in now_reachable if fully_observed(q, node)
        }
        _c, groups = quotient_groups(q, now_full)
        harvest_cycles.append({
            "cycle": cycle,
            "attempts": attempts,
            "zero_probe_closed": closed,
            "zero_probe_separated": separated,
            "needs_more_evidence": needs_more_evidence,
            "certified_before": cert_before,
            "certified_after": cert_after,
            "available_credits": available_credits,
            "expansions": expansion_rows,
            "total_reinvested_states": reinvested,
            "reachable_states": len(now_reachable),
            "fully_observed_reachable_states": len(now_full),
            "partial_quotient": group_stats(groups),
            "reinvestment_probes": explorer.new_probes - reinvest_probe_start,
        })

        if closed == 0 and newly_expanded == 0:
            break

    final_reachable = reachable(q)
    final_full = {
        node for node in final_reachable if fully_observed(q, node)
    }
    _c, final_groups = quotient_groups(q, final_full)
    final_cert = certified_stats(uf)

    ledger = serialize_ledger(
        q,
        prefixes,
        {
            "game_id": game_id,
            "agent_sha256": audit.sha(AGENT.read_bytes()),
            "source_branch": "arc3-component-explore-harvest-v4",
            "source_trace": source_meta,
            "baseline_probe_count": baseline["new_probes"],
            "exploration_extra_probes": EXPLORATION_PROBES,
            "reinvestment_extra_probes": explorer.new_probes - reinvest_probe_start,
        },
    )
    audit.write_json(OUT / "exact-replay-ledger.json", ledger)

    report = {
        "interpretation": (
            "explore-first then zero-probe-certificate-harvest compounding over "
            "the exact ls20 primitive successor cone"
        ),
        "claim_boundary": (
            "harvest certificates require recursive closure with zero additional "
            "environment probes; UNKNOWN/needs-evidence pairs remain distinct"
        ),
        "prior_commit": "2420ed6096dac9538518e4c3bc3e8b625260c014",
        "game_id": game_id,
        "source_trace": source_meta,
        "initial_candidate_pairs": len(candidates),
        "one_step_survivors": len(survivors),
        "certificate_new_probes": certificate_probes,
        "baseline": {
            "raw_bound_states": baseline["states"],
            "new_probes": baseline["new_probes"],
            "reachable_states": len(baseline_reachable),
            "fully_observed_reachable_states": len(baseline_full),
            "partial_quotient": group_stats(baseline_groups),
        },
        "exploration": {
            "extra_probes": explorer.new_probes - (explorer.new_probes - reinvest_probe_start),
            "attacks": exploration_attacks,
            "reachable_states": len(enriched_reachable),
            "fully_observed_reachable_states": len(enriched_full),
            "partial_quotient": group_stats(enriched_groups),
            "certified_after_exploration": certified_stats(uf),
        },
        "harvest_cycles": harvest_cycles,
        "final": {
            "exploration_extra_probes": reinvest_probe_start,
            "reinvestment_extra_probes": explorer.new_probes - reinvest_probe_start,
            "total_post_baseline_probes": explorer.new_probes,
            "reachable_states": len(final_reachable),
            "fully_observed_reachable_states": len(final_full),
            "certified": final_cert,
            "reinvested_frontier_states": reinvested,
            "partial_quotient": group_stats(final_groups),
            "ledger_nodes": len(ledger["nodes"]),
            "ledger_edges": len(ledger["edges"]),
            "ledger_prefixes": len(ledger["prefixes"]),
        },
    }
    audit.write_json(OUT / "component-explore-harvest-v4.json", report)
    print(
        "COMPONENT_EXPLORE_HARVEST_V4_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_COMPONENT_EXPLORE_HARVEST_V4=PASS", flush=True)


if __name__ == "__main__":
    main()

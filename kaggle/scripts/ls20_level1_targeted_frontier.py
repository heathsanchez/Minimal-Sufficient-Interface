"""Deep-frontier exact Level-1 search for ls20.

The retained Level-1 transition graph contains 811 nonterminal Level-1 states
and 2,468 known Level-1→Level-1 edges. It is a DAG: there are no nontrivial
strongly connected components. From the compiled L1 entry, the current known
DAG reaches depth 65.

This experiment therefore targets the deepest unresolved Level-1 boundary
first, rather than the cheapest replay prefix. If Level-1 dynamics are a
monotone progression, the deepest unresolved frontier is the most
performance-relevant place to look for L2.


The retained performance ledger already pays RESET->L1 in 56 primitive actions
and contains thousands of exact Level-1 transitions. Eight sequential
400-action generations expanded the ledger substantially but did not reach L2.

This experiment uses the ledger as an indexed counterfactual search structure
instead of forcing another wandering episode.

Loop:
  - choose the shortest-prefix Level-1 state with an unresolved legal primitive action;
  - replay its exact retained RESET prefix and verify every intermediate digest;
  - try one missing primitive action;
  - record the exact successor into the mutable ledger;
  - immediately add any newly discovered state/prefix back to the frontier;
  - stop on protected progress to Level 2.

Probe priority is:
  1. shortest exact replay prefix;
  2. more unresolved actions at the source;
  3. primitive action order 3,4,2,1, based only on the existing Level-1
     terminal-risk frequencies. This ordering is proposal-only.

UNKNOWN/ambiguous edges are never treated as deterministic evidence.
"""
from __future__ import annotations

from collections import Counter, deque
import json
from pathlib import Path
import sys
from typing import Any

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "ls20-level1-scc-frontier-v3-results"
AGENT = OUT / "agent.py"
LEDGER = OUT / "level-compounded-exact-replay-ledger.json"

sys.path.insert(0, str(ROOT / "kaggle" / "scripts"))
import ls20_dynamic_ledger_performance as dyn

EXPECTED_AGENT_SHA = dyn.EXPECTED_AGENT_SHA
EXPECTED_GAME = dyn.EXPECTED_GAME
EXPECTED_NODES = 4195
EXPECTED_EDGES = 11599

TARGET_LEVEL = 2
MAX_PROBES = 1500
MAX_REPLAY_ACTIONS = 120000
ACTION_PRIORITY = {3: 0, 4: 1, 2: 2, 1: 3}


def load_ledger():
    payload = json.loads(LEDGER.read_text())
    meta = payload.get("metadata", {})
    if payload.get("schema") != "arc3-exact-replay-ledger-v1":
        raise AssertionError("unexpected exact replay ledger schema")
    if meta.get("agent_sha256") != EXPECTED_AGENT_SHA:
        raise AssertionError("ledger agent mismatch")
    if meta.get("game_id") != EXPECTED_GAME:
        raise AssertionError("ledger game mismatch")
    if len(payload.get("nodes", {})) != EXPECTED_NODES:
        raise AssertionError("ledger node count changed")
    if len(payload.get("edges", [])) != EXPECTED_EDGES:
        raise AssertionError("ledger edge count changed")

    dyn.EXPECTED_NODES = EXPECTED_NODES
    dyn.EXPECTED_EDGES = EXPECTED_EDGES
    return payload, dyn.DynamicExactLedger(payload)


def make_action(action_id: int):
    from arcengine import GameAction

    action = GameAction.from_id(int(action_id))
    if action.is_complex():
        raise AssertionError("ls20 targeted frontier expected primitive actions")
    return action, action.action_data.model_dump()


def shortest_reset_prefixes(ledger):
    roots = [
        node
        for node, prefix in ledger.prefixes.items()
        if len(prefix) == 0
    ]
    if len(roots) != 1:
        raise AssertionError("expected one RESET ledger root")
    root = roots[0]

    routes = {root: ()}
    queue = deque([root])
    while queue:
        source = queue.popleft()
        prefix = routes[source]
        for action in ledger.legal(source):
            target = ledger.successor.get((source, int(action)))
            if target is None or target in routes:
                continue
            protected = ledger.protected(target)
            if protected and str(protected[0]) in ("GAME_OVER", "WIN"):
                continue
            routes[target] = prefix + ((int(action), None, None),)
            queue.append(target)
    return root, routes


_LAST_SCC_STATS = {}


def level1_depths(ledger):
    """Return node -> depth in the SCC condensation DAG.

    Raw Level-1 dynamics may become cyclic as the frontier expands. The
    consequential progress coordinate is therefore depth after quotienting
    exact strongly connected components, not raw-node DAG depth.
    """
    global _LAST_SCC_STATS

    level1 = {
        node
        for node, row in ledger.nodes.items()
        if str(row["protected"][0]) == "NOT_FINISHED"
        and int(row["protected"][1]) == TARGET_LEVEL - 1
    }

    _root, compiled_routes = shortest_reset_prefixes(ledger)
    reachable_level1 = {
        node for node in level1 if node in compiled_routes
    }
    if not reachable_level1:
        raise AssertionError("no reachable nonterminal Level-1 states")

    entry = min(
        reachable_level1,
        key=lambda node: (len(compiled_routes[node]), node),
    )

    adjacency = {node: [] for node in reachable_level1}
    for (source, _action), target in ledger.successor.items():
        if source in reachable_level1 and target in reachable_level1:
            adjacency[source].append(target)

    # Tarjan SCC decomposition over exact deterministic Level-1 edges.
    index = 0
    stack = []
    on_stack = set()
    indices = {}
    lowlink = {}
    components = []

    def strongconnect(node):
        nonlocal index
        indices[node] = index
        lowlink[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for target in adjacency.get(node, ()):
            if target not in indices:
                strongconnect(target)
                lowlink[node] = min(lowlink[node], lowlink[target])
            elif target in on_stack:
                lowlink[node] = min(lowlink[node], indices[target])

        if lowlink[node] == indices[node]:
            component = []
            while True:
                value = stack.pop()
                on_stack.remove(value)
                component.append(value)
                if value == node:
                    break
            components.append(tuple(sorted(component)))

    for node in sorted(reachable_level1):
        if node not in indices:
            strongconnect(node)

    component_of = {}
    for cid, component in enumerate(components):
        for node in component:
            component_of[node] = cid

    cadj = {cid: set() for cid in range(len(components))}
    indegree = Counter()
    for source, targets in adjacency.items():
        source_c = component_of[source]
        for target in targets:
            target_c = component_of[target]
            if source_c == target_c or target_c in cadj[source_c]:
                continue
            cadj[source_c].add(target_c)
            indegree[target_c] += 1

    queue = [
        cid for cid in range(len(components))
        if indegree[cid] == 0
    ]
    topo = []
    while queue:
        cid = queue.pop()
        topo.append(cid)
        for target_c in cadj[cid]:
            indegree[target_c] -= 1
            if indegree[target_c] == 0:
                queue.append(target_c)

    if len(topo) != len(components):
        raise AssertionError("SCC condensation graph must be acyclic")

    entry_c = component_of[entry]
    cdepth = {entry_c: 0}
    for cid in topo:
        if cid not in cdepth:
            continue
        for target_c in cadj[cid]:
            cdepth[target_c] = max(
                cdepth.get(target_c, -1),
                cdepth[cid] + 1,
            )

    depth = {
        node: int(cdepth.get(component_of[node], -1))
        for node in reachable_level1
    }
    nontrivial = [
        component for component in components if len(component) > 1
    ]
    _LAST_SCC_STATS = {
        "reachable_level1_states": len(reachable_level1),
        "scc_count": len(components),
        "nontrivial_scc_count": len(nontrivial),
        "largest_scc": max((len(component) for component in components), default=0),
        "nontrivial_scc_sizes": sorted(
            (len(component) for component in nontrivial),
            reverse=True,
        )[:20],
        "condensation_edges": sum(len(targets) for targets in cadj.values()),
        "max_quotient_depth": max(depth.values(), default=-1),
        "entry": entry,
        "entry_prefix_actions": len(compiled_routes[entry]),
    }
    return entry, depth

def candidate_rows(ledger):
    rows = []
    attempted = set()
    _entry, depth = level1_depths(ledger)
    _root, compiled_routes = shortest_reset_prefixes(ledger)

    for node, row in ledger.nodes.items():
        protected = tuple(row["protected"])
        if (
            len(protected) < 2
            or str(protected[0]) != "NOT_FINISHED"
            or int(protected[1]) != TARGET_LEVEL - 1
        ):
            continue

        prefix = compiled_routes.get(str(node))
        if prefix is None:
            continue

        legal = tuple(
            int(action)
            for action in row.get("legal_actions", ())
            if int(action) not in (0, 6)
        )
        missing = [
            action
            for action in legal
            if (node, action) not in ledger.successor
            and (node, action) not in ledger.ambiguous
            and (node, action) not in attempted
        ]
        if not missing:
            continue

        node_depth = int(depth.get(str(node), -1))
        for action in missing:
            rows.append((
                -node_depth,
                len(prefix),
                -len(missing),
                ACTION_PRIORITY.get(int(action), 99),
                str(node),
                int(action),
                prefix,
            ))

    rows.sort()
    return rows


def replay_probe(module, game_id, envdir, ledger, source, action_id, prefix):
    from arc_agi import Arcade, OperationMode

    arc = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=envdir,
        logger=audit.quiet_logger(),
    )
    env = arc.make(game_id, seed=0)
    if env is None:
        raise RuntimeError("offline ls20 unavailable")

    adapter = module.MyAgent(
        card_id="targeted-frontier-replay",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )

    latest = adapter._convert_raw_frame_data(env.observation_space)
    digest = str(module.normalize_frame(latest).evidence_sha256)

    for action_key in prefix:
        aid, x, y = action_key
        if x is not None or y is not None:
            arc.close_scorecard()
            raise AssertionError("retained ls20 prefix contains parameterized action")

        expected = ledger.successor.get((digest, int(aid)))
        if expected is None:
            arc.close_scorecard()
            raise AssertionError("replay prefix contains non-deterministic/missing retained edge")

        action, data = make_action(int(aid))
        raw = env.step(
            action,
            data=data,
            reasoning={"source": "targeted_frontier_prefix"},
        )
        latest = adapter._convert_raw_frame_data(raw)
        actual = str(module.normalize_frame(latest).evidence_sha256)
        if actual != expected:
            arc.close_scorecard()
            raise AssertionError("retained replay prefix diverged")
        digest = actual

    if digest != source:
        arc.close_scorecard()
        raise AssertionError("replay failed to recover targeted source")

    before = module.normalize_frame(latest)
    before_level = int(before.levels_completed)

    action, data = make_action(action_id)
    raw = env.step(
        action,
        data=data,
        reasoning={"source": "targeted_frontier_probe"},
    )
    latest = adapter._convert_raw_frame_data(raw)
    after = module.normalize_frame(latest)
    target = str(after.evidence_sha256)
    delta = int(after.levels_completed) - before_level
    outcome = (
        "LEVEL_INCREMENT" if delta > 0 else str(after.state),
        int(delta),
    )

    arc.close_scorecard()
    return {
        "source": source,
        "action": int(action_id),
        "target": target,
        "target_protected": dyn.protected(after),
        "target_legal": dyn.legal_actions(after),
        "outcome": outcome,
        "prefix": prefix,
    }


def main():
    payload, ledger = load_ledger()

    manifest = json.loads((OUT / "public.json").read_text())
    game = next(
        row for row in manifest["games"]
        if row["game_id"] == EXPECTED_GAME
    )

    audit.AGENT = AGENT
    module = audit.load_agent()
    audit.block_network()

    initial_level1_boundaries = len({
        row[4]
        for row in candidate_rows(ledger)
    })

    probes = []
    replay_actions = 0
    progress = None
    ambiguous_added = 0
    new_nodes = 0
    new_edges = 0

    while len(probes) < MAX_PROBES and replay_actions < MAX_REPLAY_ACTIONS:
        rows = candidate_rows(ledger)
        if not rows:
            break

        neg_depth, prefix_len, neg_missing, _action_rank, source, action_id, prefix = rows[0]
        cost = int(prefix_len) + 1
        if replay_actions + cost > MAX_REPLAY_ACTIONS:
            break

        row = replay_probe(
            module,
            game["game_id"],
            manifest["environments_dir"],
            ledger,
            source,
            action_id,
            prefix,
        )
        replay_actions += cost

        target = row["target"]
        target_prefix = tuple(prefix) + ((int(action_id), None, None),)
        if ledger.add_node(
            target,
            protected_value=row["target_protected"],
            legal=row["target_legal"],
            prefix=target_prefix,
        ):
            new_nodes += 1

        added, ambiguous = ledger.add_edge(
            source,
            action_id,
            target,
            row["outcome"],
        )
        new_edges += int(added)
        ambiguous_added += int(ambiguous)

        summary = {
            "probe": len(probes) + 1,
            "source": source,
            "source_prefix_actions": prefix_len,
            "source_missing_actions": -neg_missing,
            "source_quotient_depth": -neg_depth,
            "action": action_id,
            "target": target,
            "target_protected": list(row["target_protected"]),
            "outcome": list(row["outcome"]),
            "cumulative_replay_actions": replay_actions,
            "new_node": bool(target not in payload["nodes"]),
            "became_ambiguous": bool(ambiguous),
        }
        probes.append(summary)

        if int(row["target_protected"][1]) >= TARGET_LEVEL:
            progress_word = [
                int(aid)
                for aid, x, y in target_prefix
                if x is None and y is None
            ]
            progress = {
                "target_level": int(row["target_protected"][1]),
                "target": target,
                "target_protected": list(row["target_protected"]),
                "executed_actions": len(progress_word),
                "reported_milestone_action": len(progress_word) + 1,
                "action_word": progress_word,
                "probe_index": len(probes),
                "cumulative_replay_actions": replay_actions,
            }
            break

        if len(probes) % 50 == 0:
            print(
                "TARGETED_FRONTIER_CHECKPOINT="
                + json.dumps(
                    {
                        "probes": len(probes),
                        "replay_actions": replay_actions,
                        "ledger_nodes": len(ledger.nodes),
                        "ledger_edges": len(ledger.edge_records),
                        "remaining_level1_boundaries": len({
                            item[4] for item in candidate_rows(ledger)
                        }),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )

    final_boundaries = len({
        row[4]
        for row in candidate_rows(ledger)
    })

    augmented = ledger.export(generation_rows=[])
    audit.write_json(
        OUT / "scc-frontier-v3-exact-replay-ledger.json",
        augmented,
    )

    report = {
        "interpretation": (
            "deepest-SCC-condensation-frontier exact counterfactual search using "
            "shortest composed RESET prefixes from the retained ls20 replay ledger"
        ),
        "claim_boundary": (
            "each probe begins with the shortest currently known deterministic RESET "
            "route and every intermediate digest must match the retained ledger; "
            "SCC-condensation depth and action ordering are proposal-only"
        ),
        "initial": {
            "ledger_nodes": len(payload["nodes"]),
            "ledger_edges": len(payload["edges"]),
            "level1_boundary_states": initial_level1_boundaries,
        },
        "budget": {
            "max_probes": MAX_PROBES,
            "max_replay_actions": MAX_REPLAY_ACTIONS,
        },
        "scc_quotient": dict(_LAST_SCC_STATS),
        "result": {
            "status": (
                "PROGRESS_FOUND"
                if progress is not None
                else (
                    "FRONTIER_CLOSED"
                    if final_boundaries == 0
                    else "BUDGET_EXHAUSTED"
                )
            ),
            "probes": len(probes),
            "replay_actions": replay_actions,
            "progress": progress,
            "new_nodes": new_nodes,
            "new_edges": new_edges,
            "new_ambiguous_edges": ambiguous_added,
            "final_ledger_nodes": len(ledger.nodes),
            "final_ledger_edges": len(ledger.edge_records),
            "remaining_level1_boundary_states": final_boundaries,
        },
        "probe_rows": probes,
    }

    audit.write_json(
        OUT / "ls20-level1-scc-frontier-v3.json",
        report,
    )
    print(
        "LS20_LEVEL1_SCC_FRONTIER_V3_RESULT="
        + json.dumps(report, sort_keys=True),
        flush=True,
    )
    print("ARC3_LS20_LEVEL1_SCC_FRONTIER_V3=PASS", flush=True)


if __name__ == "__main__":
    main()

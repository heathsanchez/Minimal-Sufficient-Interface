"""Exact-parameter intervention audit and recursive closure for ARC3.

This V2 probe fixes the action-family alias exposed by ft09/vc33.  Complex
interventions are keyed by (action_id, x, y), never by action_id alone.

The finite closure contract is deliberately explicit:
  * every primitive legal action;
  * every exact parameterized action-6 coordinate used anywhere by the frozen
    source trajectory in that world; and
  * a small deterministic dimensions-only coordinate basis (first 16 points
    from the generic runtime's 8 -> 4 -> 1 enumeration).

This is bounded public development evidence.  Coordinates outside this declared
finite vocabulary remain UNKNOWN; no universal hidden-state equivalence is
claimed.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
from itertools import combinations
import json
from pathlib import Path
import sys

import benchmark_audit as audit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "grounded-interventional-v2-results"
AGENT = OUT / "agent.py"
sys.path.insert(0, str(ROOT / "kaggle" / "src"))
sys.path.insert(0, str(ROOT / "kaggle" / "scripts"))

from metalogic_arc3.interventional_quotient import PartialInterventionalQuotient
from metalogic_arc3.grounded_interventional_quotient import (
    GroundedInterventionalQuotient,
    action_sort_key,
)
from interventional_quotient_diagnostic import legal_ids, protected, raw_digest

ActionKey = tuple[int, int | None, int | None]

BASIS_COMPLEX_POINTS = 16
MAX_NEW_PROBES = 768
MAX_PAIR_OBLIGATIONS = 4096


class ProbeBudgetExhausted(RuntimeError):
    pass


def canonical_pair(left: str, right: str) -> tuple[str, str]:
    return (left, right) if left <= right else (right, left)


def terminal_protected(value: tuple) -> bool:
    return bool(value) and str(value[0]) in ("WIN", "GAME_OVER")


def make_action(key: ActionKey):
    from arcengine import GameAction

    aid, x, y = key
    action = GameAction.from_id(int(aid))
    if action.is_complex():
        if x is None or y is None:
            raise ValueError("complex exact intervention requires coordinates")
        action.set_data({"x": int(x), "y": int(y)})
    return action, action.action_data.model_dump()


def coordinate_basis(height: int, width: int, limit: int = BASIS_COMPLEX_POINTS):
    seen: set[tuple[int, int]] = set()
    out: list[tuple[int, int]] = []
    if height < 1 or width < 1 or limit < 1:
        return tuple()
    for step in (8, 4, 1):
        for y in range(step // 2, height, step):
            for x in range(step // 2, width, step):
                point = (int(x), int(y))
                if point in seen:
                    continue
                seen.add(point)
                out.append(point)
                if len(out) >= limit:
                    return tuple(out)
    return tuple(out)


def node_meta(module, frame) -> dict:
    obs = module.normalize_frame(frame)
    return {
        "protected": tuple(protected(frame)),
        "legal_families": tuple(legal_ids(frame)),
        "height": int(obs.height),
        "width": int(obs.width),
    }


def declared_grounded_contract(meta: dict, vocabulary: tuple[ActionKey, ...]) -> tuple[ActionKey, ...]:
    legal = set(int(value) for value in meta["legal_families"])
    actions: set[ActionKey] = set()

    for aid in sorted(legal):
        if aid == 6:
            for key in vocabulary:
                if int(key[0]) == 6:
                    actions.add((6, int(key[1]), int(key[2])))
            for x, y in coordinate_basis(meta["height"], meta["width"]):
                actions.add((6, x, y))
        else:
            actions.add((int(aid), None, None))

    return tuple(sorted(actions, key=action_sort_key))


def build_source_trace(module, game_id: str, envdir: str, max_actions: int) -> dict:
    from arc_agi import Arcade, OperationMode

    audit.block_network()
    arc = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=envdir,
        logger=audit.quiet_logger(),
    )
    env = arc.make(game_id, seed=0)
    if env is None:
        raise RuntimeError("offline public world unavailable")

    policy = module.MyAgent(
        card_id="grounded-v2-source",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )
    policy.controller.archived_capabilities = ()

    latest = policy._convert_raw_frame_data(env.observation_space)
    digest = raw_digest(module, latest)

    nodes: dict[str, dict] = {digest: node_meta(module, latest)}
    prefixes: dict[str, tuple[ActionKey, ...]] = {digest: ()}
    prefix: tuple[ActionKey, ...] = ()
    transitions: list[dict] = []
    exact_vocabulary: set[ActionKey] = set()
    frames = [latest]
    source_counts: Counter[str] = Counter()
    milestones: list[dict] = []
    max_level = int(latest.levels_completed)
    actions = 0

    while actions + 1 < max_actions and audit.state_name(latest) != "WIN":
        if policy.is_done(frames, latest):
            break

        before = latest
        source = digest
        before_level = int(before.levels_completed)

        chosen = policy.choose_action(frames, before)
        data = audit.validate_action(chosen, before)
        key: ActionKey = (
            int(chosen.value),
            None if data.get("x") is None else int(data.get("x")),
            None if data.get("y") is None else int(data.get("y")),
        )
        reasoning = getattr(chosen, "reasoning", {})
        source_name = (
            str(reasoning.get("source", "unknown"))
            if isinstance(reasoning, dict)
            else "unknown"
        )

        raw = env.step(chosen, data=data, reasoning={"source": source_name})
        latest = policy._convert_raw_frame_data(raw)
        digest = raw_digest(module, latest)
        meta = node_meta(module, latest)
        old = nodes.get(digest)
        if old is not None and old != meta:
            raise AssertionError("same public digest has conflicting visible contract")
        nodes[digest] = meta

        delta = int(latest.levels_completed) - before_level
        outcome = (
            "LEVEL_INCREMENT" if delta > 0 else audit.state_name(latest),
            int(delta),
        )
        transitions.append({
            "source": source,
            "action": key,
            "target": digest,
            "outcome": outcome,
        })
        exact_vocabulary.add(key)
        actions += 1
        source_counts[source_name] += 1
        prefix = prefix + (key,)
        old_prefix = prefixes.get(digest)
        if old_prefix is None or len(prefix) < len(old_prefix):
            prefixes[digest] = prefix
        frames.append(latest)

        if int(latest.levels_completed) > max_level:
            max_level = int(latest.levels_completed)
            milestones.append({"level": max_level, "actions": actions + 1})

    arc.close_scorecard()

    vocabulary = tuple(sorted(exact_vocabulary, key=action_sort_key))

    family = PartialInterventionalQuotient()
    grounded = GroundedInterventionalQuotient()
    for node, meta in nodes.items():
        family.observe_node(
            node,
            protected=tuple(meta["protected"]),
            legal_actions=tuple(meta["legal_families"]),
        )
        grounded.observe_node(
            node,
            protected=tuple(meta["protected"]),
            legal_actions=declared_grounded_contract(meta, vocabulary),
        )

    for row in transitions:
        family.observe_transition(
            row["source"],
            int(row["action"][0]),
            row["target"],
            outcome=tuple(row["outcome"]),
        )
        grounded.observe_transition(
            row["source"],
            tuple(row["action"]),
            row["target"],
            outcome=tuple(row["outcome"]),
        )

    return {
        "nodes": nodes,
        "prefixes": prefixes,
        "transitions": transitions,
        "vocabulary": vocabulary,
        "family": family,
        "grounded": grounded,
        "meta": {
            "actions": actions + 1,
            "raw_states": len(nodes),
            "source_counts": dict(source_counts),
            "milestones": milestones,
            "max_levels": max_level,
            "final_state": audit.state_name(latest),
            "exact_action_variants": len(vocabulary),
            "exact_action6_variants": sum(int(key[0]) == 6 for key in vocabulary),
        },
    }


def merged_pairs(classes: dict, nodes: set[str]) -> list[tuple[str, str]]:
    groups: dict[int, list[str]] = defaultdict(list)
    for node, class_id in classes.items():
        if node in nodes:
            groups[int(class_id)].append(node)
    return sorted(
        canonical_pair(left, right)
        for group in groups.values()
        for left, right in combinations(sorted(group), 2)
    )


def family_fully_observed(q: PartialInterventionalQuotient, left: str, right: str) -> bool:
    lrow, rrow = q.nodes[left], q.nodes[right]
    if lrow.legal_actions != rrow.legal_actions or not lrow.legal_actions:
        return False
    legal = set(lrow.legal_actions)
    return legal <= q._observed_actions(left) and legal <= q._observed_actions(right)


def replay_and_probe(
    module,
    game_id: str,
    envdir: str,
    prefix: tuple[ActionKey, ...],
    expected_source: str,
    action_key: ActionKey,
) -> dict:
    from arc_agi import Arcade, OperationMode

    arc = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=envdir,
        logger=audit.quiet_logger(),
    )
    env = arc.make(game_id, seed=0)
    if env is None:
        raise RuntimeError("offline public world unavailable during replay")
    adapter = module.MyAgent(
        card_id="grounded-v2-replay",
        game_id="source-blind",
        agent_name="frozen-mg-arc5",
        ROOT_URL="",
        record=False,
        arc_env=None,
    )

    latest = adapter._convert_raw_frame_data(env.observation_space)
    for key in prefix:
        action, data = make_action(key)
        raw = env.step(action, data=data, reasoning={"source": "exact_replay"})
        latest = adapter._convert_raw_frame_data(raw)

    source_digest = raw_digest(module, latest)
    if source_digest != expected_source:
        arc.close_scorecard()
        raise AssertionError(
            "exact replay failed to recover quotient obligation: "
            f"{expected_source[:12]} != {source_digest[:12]}"
        )

    before_level = int(latest.levels_completed)
    action, data = make_action(action_key)
    raw = env.step(action, data=data, reasoning={"source": "grounded_separator_probe"})
    after = adapter._convert_raw_frame_data(raw)
    target = raw_digest(module, after)
    delta = int(after.levels_completed) - before_level
    result = {
        "source": source_digest,
        "action": action_key,
        "target": target,
        "outcome": (
            "LEVEL_INCREMENT" if delta > 0 else audit.state_name(after),
            int(delta),
        ),
        "target_meta": node_meta(module, after),
    }
    arc.close_scorecard()
    return result


class ClosureProbe:
    def __init__(
        self,
        module,
        game_id: str,
        envdir: str,
        q: GroundedInterventionalQuotient,
        prefixes: dict[str, tuple[ActionKey, ...]],
        node_rows: dict[str, dict],
        vocabulary: tuple[ActionKey, ...],
    ):
        self.module = module
        self.game_id = game_id
        self.envdir = envdir
        self.q = q
        self.prefixes = prefixes
        self.node_rows = node_rows
        self.vocabulary = vocabulary
        self.new_probes = 0
        self.rows: list[dict] = []

    def ensure_action(self, node: str, action: ActionKey):
        existing = self.q.edges.get(node, {}).get(action, set())
        if existing:
            return set(existing)
        if self.new_probes >= MAX_NEW_PROBES:
            raise ProbeBudgetExhausted("global exact replay probe budget exhausted")
        prefix = self.prefixes.get(node)
        if prefix is None:
            raise RuntimeError("missing exact replay prefix for successor obligation")

        row = replay_and_probe(
            self.module,
            self.game_id,
            self.envdir,
            prefix,
            node,
            action,
        )
        self.new_probes += 1
        self.rows.append(row)

        target_meta = row["target_meta"]
        old = self.node_rows.get(row["target"])
        if old is not None and old != target_meta:
            raise AssertionError("replayed target has conflicting visible contract")
        self.node_rows[row["target"]] = target_meta

        self.q.observe_node(
            row["target"],
            protected=tuple(target_meta["protected"]),
            legal_actions=declared_grounded_contract(target_meta, self.vocabulary),
        )
        self.q.observe_transition(
            row["source"],
            tuple(row["action"]),
            row["target"],
            outcome=tuple(row["outcome"]),
        )

        candidate_prefix = tuple(prefix) + (tuple(action),)
        old_prefix = self.prefixes.get(row["target"])
        if old_prefix is None or len(candidate_prefix) < len(old_prefix):
            self.prefixes[row["target"]] = candidate_prefix

        print(
            "GROUNDED_PROBE="
            + json.dumps(
                {
                    "source": node[:16],
                    "action": list(action),
                    "target": row["target"][:16],
                    "outcome": row["outcome"],
                    "probe_index": self.new_probes,
                },
                sort_keys=True,
            ),
            flush=True,
        )
        return set(self.q.edges[node][action])

    def close_root(self, root: tuple[str, str]) -> dict:
        root = canonical_pair(*root)
        queue = deque([(root, ())])
        seen: dict[tuple[str, str], tuple[ActionKey, ...]] = {}
        edges: list[dict] = []

        try:
            while queue:
                if len(seen) > MAX_PAIR_OBLIGATIONS:
                    return {
                        "root": root,
                        "status": "UNKNOWN_PAIR_BOUND",
                        "separator_word": None,
                        "pair_obligations": len(seen),
                        "edges": edges,
                    }

                pair, word = queue.popleft()
                pair = canonical_pair(*pair)
                if pair[0] == pair[1] or pair in seen:
                    continue
                seen[pair] = tuple(word)
                left, right = pair
                lrow, rrow = self.q.nodes[left], self.q.nodes[right]

                if lrow.protected != rrow.protected:
                    return {
                        "root": root,
                        "status": "SEPARATED",
                        "reason": "protected_outcome",
                        "separator_word": [list(key) for key in word],
                        "witness_pair": pair,
                        "pair_obligations": len(seen),
                        "edges": edges,
                    }
                if lrow.legal_actions != rrow.legal_actions:
                    return {
                        "root": root,
                        "status": "SEPARATED",
                        "reason": "grounded_legal_contract",
                        "separator_word": [list(key) for key in word],
                        "witness_pair": pair,
                        "pair_obligations": len(seen),
                        "edges": edges,
                    }
                if terminal_protected(lrow.protected):
                    continue
                if not lrow.legal_actions:
                    return {
                        "root": root,
                        "status": "UNKNOWN_NO_DECLARED_ACTIONS",
                        "separator_word": None,
                        "witness_pair": pair,
                        "pair_obligations": len(seen),
                        "edges": edges,
                    }

                for action in lrow.legal_actions:
                    left_rows = self.ensure_action(left, action)
                    right_rows = self.ensure_action(right, action)
                    if len(left_rows) != 1 or len(right_rows) != 1:
                        return {
                            "root": root,
                            "status": "UNKNOWN_NONDETERMINISTIC_OBSERVATION",
                            "separator_word": None,
                            "witness_pair": pair,
                            "action": list(action),
                            "left_successors": len(left_rows),
                            "right_successors": len(right_rows),
                            "pair_obligations": len(seen),
                            "edges": edges,
                        }

                    left_outcome, left_target = next(iter(left_rows))
                    right_outcome, right_target = next(iter(right_rows))
                    next_word = tuple(word) + (action,)
                    edges.append({
                        "pair": pair,
                        "action": action,
                        "left_outcome": left_outcome,
                        "right_outcome": right_outcome,
                        "left_target": left_target,
                        "right_target": right_target,
                    })

                    if left_outcome != right_outcome:
                        return {
                            "root": root,
                            "status": "SEPARATED",
                            "reason": "transition_outcome",
                            "separator_word": [list(key) for key in next_word],
                            "witness_pair": pair,
                            "pair_obligations": len(seen),
                            "edges": edges,
                        }
                    if left_target != right_target:
                        queue.append((
                            canonical_pair(left_target, right_target),
                            next_word,
                        ))
        except ProbeBudgetExhausted:
            return {
                "root": root,
                "status": "UNKNOWN_PROBE_BUDGET",
                "separator_word": None,
                "pair_obligations": len(seen),
                "edges": edges,
            }

        return {
            "root": root,
            "status": "CLOSED_BOUNDED_GROUNDED_BISIMULATION",
            "separator_word": None,
            "pair_obligations": len(seen),
            "edges": edges,
            "closed_pairs": [
                {
                    "pair": pair,
                    "word": [list(key) for key in word],
                }
                for pair, word in sorted(seen.items())
            ],
        }


def summarize(q, bound: int) -> dict:
    result = q.summary(max_depth=max(8, bound))
    if result["depths"]:
        final = result["depths"][-1]
        if result["stabilized"]:
            assert final["contradictory_merged_pairs"] == 0
    return result


def main() -> None:
    manifest = json.loads((OUT / "public.json").read_text())

    audit.AGENT = AGENT
    module = audit.load_agent()
    worlds = {}
    for short in ("ft09", "vc33"):
        row = next(item for item in manifest["games"] if item["game_id"].startswith(short + "-"))
        trace = build_source_trace(
            module,
            row["game_id"],
            manifest["environments_dir"],
            manifest["max_actions"],
        )
        worlds[short] = (row["game_id"], trace)

    ft_game, ft = worlds["ft09"]
    vc_game, vc = worlds["vc33"]

    ft_family_summary = summarize(ft["family"], len(ft["family"].nodes))
    ft_grounded_summary = summarize(ft["grounded"], len(ft["grounded"].nodes))
    ft_family_final = ft_family_summary["depths"][-1]
    ft_grounded_final = ft_grounded_summary["depths"][-1]

    # Pin the known family-collapse residual, then ask what exact parameters do.
    assert ft["meta"]["raw_states"] == 87
    assert ft["meta"]["exact_action6_variants"] == 77
    assert ft_family_final["ambiguous_observed_edges"] == 43

    vc_family_parts = vc["family"].partitions(max_depth=max(8, len(vc["family"].nodes)))
    vc_family_classes = vc_family_parts[-1]
    vc_pairs = merged_pairs(vc_family_classes, set(vc["family"].nodes))
    vc_full_pairs = [
        pair for pair in vc_pairs
        if family_fully_observed(vc["family"], *pair)
    ]

    assert vc["meta"]["raw_states"] == 198
    assert vc["meta"]["milestones"][:2] == [
        {"level": 1, "actions": 64},
        {"level": 2, "actions": 93},
    ]
    assert len(vc_full_pairs) == 28

    before_grounded_parts = vc["grounded"].partitions(
        max_depth=max(8, len(vc["grounded"].nodes))
    )
    before_grounded_classes = before_grounded_parts[-1]

    parameter_split = [
        pair for pair in vc_full_pairs
        if before_grounded_classes[pair[0]] != before_grounded_classes[pair[1]]
    ]

    # Do not stop at the old family-level candidates. Exact parameterization can
    # reveal a different residual pair after refinement. Attack every remaining
    # merged source-state pair under the declared grounded intervention contract.
    residual_grounded_pairs = merged_pairs(
        before_grounded_classes,
        set(vc["grounded"].nodes),
    )
    roots = sorted(
        residual_grounded_pairs,
        key=lambda pair: (
            len(vc["prefixes"].get(pair[0], ())) + len(vc["prefixes"].get(pair[1], ())),
            pair,
        ),
    )

    closer = ClosureProbe(
        module,
        vc_game,
        manifest["environments_dir"],
        vc["grounded"],
        dict(vc["prefixes"]),
        dict(vc["nodes"]),
        tuple(vc["vocabulary"]),
    )
    closure_results = [closer.close_root(pair) for pair in roots]

    vc_after_summary = summarize(
        closer.q,
        len(closer.q.nodes) + MAX_PAIR_OBLIGATIONS,
    )
    vc_after_final = vc_after_summary["depths"][-1]

    report = {
        "interpretation": (
            "exact-parameter QCK/QCKN audit on frozen MG-ARC5; family-level "
            "action aliases are split into (action_id,x,y); recursive closure "
            "is only under the declared finite replay-grounded vocabulary plus "
            "a deterministic 16-point dimensions-only basis"
        ),
        "claim_boundary": (
            "bounded public development evidence only; unlisted coordinates, "
            "hidden state, and unseen continuations remain UNKNOWN"
        ),
        "prior_commit": "d24e3da4b1f27f759735f07c8822104d43607144",
        "ft09": {
            "game_id": ft_game,
            "source": ft["meta"],
            "family_final": ft_family_final,
            "grounded_final": ft_grounded_final,
            "family_ambiguous_edges": ft_family_final["ambiguous_observed_edges"],
            "grounded_ambiguous_edges": ft_grounded_final["ambiguous_observed_edges"],
            "family_summary": ft_family_summary,
            "grounded_summary": ft_grounded_summary,
        },
        "vc33": {
            "game_id": vc_game,
            "source": vc["meta"],
            "family_fully_observed_candidate_pairs": len(vc_full_pairs),
            "parameterization_split_before_new_probes": len(parameter_split),
            "parameterization_split_pairs": parameter_split,
            "residual_grounded_pairs_before_active_closure": len(residual_grounded_pairs),
            "residual_root_contracts": [
                {
                    "pair": list(pair),
                    "protected": list(vc["grounded"].nodes[pair[0]].protected),
                    "legal_action_count": len(vc["grounded"].nodes[pair[0]].legal_actions),
                    "terminal": terminal_protected(vc["grounded"].nodes[pair[0]].protected),
                }
                for pair in roots
            ],
            "closure_roots_attempted": len(roots),
            "closure_new_probes": closer.new_probes,
            "closure_results": closure_results,
            "family_candidates_split_by_parameterization": len(parameter_split),
            "residual_separated_roots": sum(
                row["status"] == "SEPARATED" for row in closure_results
            ),
            "closed_roots": sum(
                row["status"] == "CLOSED_BOUNDED_GROUNDED_BISIMULATION"
                for row in closure_results
            ),
            "unknown_roots": sum(
                row["status"].startswith("UNKNOWN")
                for row in closure_results
            ),
            "final_grounded_quotient": vc_after_final,
            "final_grounded_summary": vc_after_summary,
        },
    }

    audit.write_json(OUT / "grounded-interventional-v2.json", report)
    print("GROUNDED_INTERVENTIONAL_V2_RESULT=" + json.dumps(report, sort_keys=True), flush=True)
    print("ARC3_GROUNDED_INTERVENTIONAL_V2=PASS", flush=True)


if __name__ == "__main__":
    main()

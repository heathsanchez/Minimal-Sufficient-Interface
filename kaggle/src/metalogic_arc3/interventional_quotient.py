from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from typing import Any, Hashable


NodeKey = Hashable
Outcome = Hashable


@dataclass(frozen=True)
class NodeRecord:
    protected: tuple[Any, ...]
    legal_actions: tuple[int, ...]


class PartialInterventionalQuotient:
    """Finite evidence quotient over a partially observed transition system.

    Raw observations are opaque node keys. The quotient never inspects pixels.
    Nodes may be grouped only through protected consequences and observed
    action-labelled continuations. Untried actions stay explicitly UNKNOWN.

    This is a bounded empirical diagnostic, not a proof of equivalence under
    unobserved continuations.
    """

    UNKNOWN = ("UNKNOWN",)

    def __init__(self) -> None:
        self.nodes: dict[NodeKey, NodeRecord] = {}
        self.edges: dict[
            NodeKey, dict[int, set[tuple[Outcome, NodeKey]]]
        ] = defaultdict(lambda: defaultdict(set))

    def observe_node(
        self,
        node: NodeKey,
        *,
        protected: tuple[Any, ...],
        legal_actions: tuple[int, ...],
    ) -> None:
        row = NodeRecord(
            tuple(protected),
            tuple(sorted({int(action) for action in legal_actions})),
        )
        old = self.nodes.get(node)
        if old is not None and old != row:
            raise ValueError("same raw observation has conflicting protected contract")
        self.nodes[node] = row

    def observe_transition(
        self,
        source: NodeKey,
        action_family: int,
        target: NodeKey,
        *,
        outcome: Outcome,
    ) -> None:
        if source not in self.nodes or target not in self.nodes:
            raise ValueError("transition endpoints must be observed first")
        action = int(action_family)
        if action not in self.nodes[source].legal_actions and action != 0:
            raise ValueError("observed action absent from legal action contract")
        self.edges[source][action].add((outcome, target))

    @staticmethod
    def _class_ids(signatures: dict[NodeKey, Any]) -> dict[NodeKey, int]:
        unique = sorted({repr(value): value for value in signatures.values()})
        ids = {key: index for index, key in enumerate(unique)}
        return {node: ids[repr(value)] for node, value in signatures.items()}

    def _base_signatures(self) -> dict[NodeKey, Any]:
        return {
            node: (row.protected, row.legal_actions)
            for node, row in self.nodes.items()
        }

    def _step_signatures(
        self,
        classes: dict[NodeKey, int],
    ) -> dict[NodeKey, Any]:
        signatures: dict[NodeKey, Any] = {}
        for node, row in self.nodes.items():
            action_rows = []
            for action in row.legal_actions:
                observed = self.edges.get(node, {}).get(action, set())
                if not observed:
                    action_rows.append((action, self.UNKNOWN))
                    continue
                targets = tuple(
                    sorted(
                        (
                            repr(outcome),
                            int(classes[target]),
                        )
                        for outcome, target in observed
                    )
                )
                action_rows.append((action, targets))
            signatures[node] = (
                row.protected,
                row.legal_actions,
                tuple(action_rows),
            )
        return signatures

    def partitions(self, max_depth: int = 8) -> list[dict[NodeKey, int]]:
        if max_depth < 0:
            raise ValueError("nonnegative quotient depth required")
        if not self.nodes:
            return []
        classes = self._class_ids(self._base_signatures())
        out = [classes]
        for _depth in range(max_depth):
            nxt = self._class_ids(self._step_signatures(classes))
            out.append(nxt)
            if nxt == classes:
                break
            classes = nxt
        return out

    def _members(self, classes: dict[NodeKey, int]) -> dict[int, list[NodeKey]]:
        out: dict[int, list[NodeKey]] = defaultdict(list)
        for node, class_id in classes.items():
            out[int(class_id)].append(node)
        return out

    def _observed_actions(self, node: NodeKey) -> set[int]:
        return {
            int(action)
            for action, rows in self.edges.get(node, {}).items()
            if rows
        }

    def _action_relation(
        self,
        node: NodeKey,
        action: int,
        classes: dict[NodeKey, int],
    ) -> set[tuple[str, int]]:
        return {
            (repr(outcome), int(classes[target]))
            for outcome, target in self.edges.get(node, {}).get(int(action), set())
        }

    def evidence_stats(self, classes: dict[NodeKey, int]) -> dict[str, int | float]:
        members = self._members(classes)
        merged_pairs = 0
        supported_pairs = 0
        fully_observed_pairs = 0
        contradictory_pairs = 0

        for group in members.values():
            for left, right in combinations(group, 2):
                merged_pairs += 1
                left_actions = self._observed_actions(left)
                right_actions = self._observed_actions(right)
                common = left_actions & right_actions
                if common:
                    supported_pairs += 1
                contradiction = any(
                    self._action_relation(left, action, classes)
                    != self._action_relation(right, action, classes)
                    for action in common
                )
                contradictory_pairs += int(contradiction)

                legal = set(self.nodes[left].legal_actions)
                if legal == set(self.nodes[right].legal_actions):
                    if legal and legal <= left_actions and legal <= right_actions:
                        fully_observed_pairs += 1

        ambiguous_edges = 0
        for source, by_action in self.edges.items():
            for action, rows in by_action.items():
                relation = {
                    (repr(outcome), int(classes[target]))
                    for outcome, target in rows
                }
                ambiguous_edges += int(len(relation) > 1)

        n = len(self.nodes)
        class_count = len(set(classes.values()))
        return {
            "raw_states": n,
            "quotient_states": class_count,
            "compression": n / max(1, class_count),
            "merged_pairs": merged_pairs,
            "supported_merged_pairs": supported_pairs,
            "fully_observed_merged_pairs": fully_observed_pairs,
            "unsupported_or_partial_pairs": merged_pairs - fully_observed_pairs,
            "contradictory_merged_pairs": contradictory_pairs,
            "ambiguous_observed_edges": ambiguous_edges,
            "largest_class": max((len(group) for group in members.values()), default=0),
        }

    def summary(self, max_depth: int = 8) -> dict[str, Any]:
        partitions = self.partitions(max_depth=max_depth)
        rows = []
        for depth, classes in enumerate(partitions):
            rows.append({"depth": depth, **self.evidence_stats(classes)})
        return {
            "nodes": len(self.nodes),
            "observed_transitions": sum(
                len(rows)
                for by_action in self.edges.values()
                for rows in by_action.values()
            ),
            "depths": rows,
            "stabilized": len(partitions) < max_depth + 1,
        }

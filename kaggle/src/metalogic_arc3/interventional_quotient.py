from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from typing import Any, Hashable


NodeKey = Hashable
Outcome = Hashable
ActionLabel = Hashable


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
            NodeKey, dict[ActionLabel, set[tuple[Outcome, NodeKey]]]
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

    @staticmethod
    def _action_family(action: ActionLabel) -> int:
        if isinstance(action, tuple):
            if not action:
                raise ValueError("empty action label")
            return int(action[0])
        return int(action)

    def observe_transition(
        self,
        source: NodeKey,
        action_label: ActionLabel,
        target: NodeKey,
        *,
        outcome: Outcome,
    ) -> None:
        if source not in self.nodes or target not in self.nodes:
            raise ValueError("transition endpoints must be observed first")
        family = self._action_family(action_label)
        if family not in self.nodes[source].legal_actions and family != 0:
            raise ValueError("observed action absent from legal action contract")
        self.edges[source][action_label].add((outcome, target))

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
            admitted: set[ActionLabel] = set(self._observed_actions(node))
            for family in row.legal_actions:
                if int(family) == 6:
                    # Coordinate actions are an intervention family, not one
                    # operation. Keep an explicit UNKNOWN parameter-space
                    # obligation even after some coordinates are observed.
                    admitted.add(("UNOBSERVED_PARAMETER_SPACE", 6))
                else:
                    admitted.add(int(family))
            admitted_actions = tuple(sorted(admitted, key=repr))
            for action in admitted_actions:
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

    @staticmethod
    def _same_partition(
        left: dict[NodeKey, int],
        right: dict[NodeKey, int],
    ) -> bool:
        if set(left) != set(right):
            return False
        left_groups: dict[int, set[NodeKey]] = defaultdict(set)
        right_groups: dict[int, set[NodeKey]] = defaultdict(set)
        for node, class_id in left.items():
            left_groups[int(class_id)].add(node)
        for node, class_id in right.items():
            right_groups[int(class_id)].add(node)
        return {
            frozenset(group) for group in left_groups.values()
        } == {
            frozenset(group) for group in right_groups.values()
        }

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
            if self._same_partition(nxt, classes):
                break
            classes = nxt
        return out

    def _members(self, classes: dict[NodeKey, int]) -> dict[int, list[NodeKey]]:
        out: dict[int, list[NodeKey]] = defaultdict(list)
        for node, class_id in classes.items():
            out[int(class_id)].append(node)
        return out

    def _observed_actions(self, node: NodeKey) -> set[ActionLabel]:
        return {
            action
            for action, rows in self.edges.get(node, {}).items()
            if rows
        }

    def _observed_families(self, node: NodeKey) -> set[int]:
        return {
            self._action_family(action)
            for action in self._observed_actions(node)
        }

    def _action_relation(
        self,
        node: NodeKey,
        action: ActionLabel,
        classes: dict[NodeKey, int],
    ) -> set[tuple[str, int]]:
        return {
            (repr(outcome), int(classes[target]))
            for outcome, target in self.edges.get(node, {}).get(action, set())
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
                    # A parameterized family is never declared fully observed
                    # merely because a finite subset of coordinates was tried.
                    if 6 not in legal:
                        left_families = self._observed_families(left)
                        right_families = self._observed_families(right)
                        if legal and legal <= left_families and legal <= right_families:
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
        stabilized = bool(
            len(partitions) >= 2
            and self._same_partition(partitions[-1], partitions[-2])
        )
        final_depth = max(0, len(partitions) - 1)
        selected = {
            depth
            for depth in (0, 1, 2, 4, 8, 16, 32, 64, final_depth)
            if depth < len(partitions)
        }
        rows = [
            {"depth": depth, **self.evidence_stats(partitions[depth])}
            for depth in sorted(selected)
        ]
        return {
            "nodes": len(self.nodes),
            "observed_transitions": sum(
                len(rows)
                for by_action in self.edges.values()
                for rows in by_action.values()
            ),
            "depths": rows,
            "stabilized": stabilized,
            "stabilization_depth": final_depth if stabilized else None,
            "depth_bound": max_depth,
        }

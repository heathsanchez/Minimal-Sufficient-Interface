from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations
from typing import Any, Hashable


NodeKey = Hashable
ActionKey = tuple[int, int | None, int | None]
Outcome = Hashable


def action_sort_key(action: ActionKey) -> tuple[int, int, int]:
    aid, x, y = action
    return (int(aid), -1 if x is None else int(x), -1 if y is None else int(y))


@dataclass(frozen=True)
class NodeRecord:
    protected: tuple[Any, ...]
    legal_actions: tuple[ActionKey, ...]


class GroundedInterventionalQuotient:
    """Finite exact-action quotient with explicit UNKNOWN continuations.

    Action identity includes parameters, so e.g. action 6 at (x1,y1) and
    action 6 at (x2,y2) are distinct interventions.  A merge is evidence only
    relative to the declared finite legal-action contract carried by each node.
    Unobserved declared actions remain UNKNOWN and cannot certify equivalence.
    """

    UNKNOWN = ("UNKNOWN",)

    def __init__(self) -> None:
        self.nodes: dict[NodeKey, NodeRecord] = {}
        self.edges: dict[
            NodeKey, dict[ActionKey, set[tuple[Outcome, NodeKey]]]
        ] = defaultdict(lambda: defaultdict(set))

    @staticmethod
    def _normalize_action(action: ActionKey) -> ActionKey:
        aid, x, y = action
        return (
            int(aid),
            None if x is None else int(x),
            None if y is None else int(y),
        )

    def observe_node(
        self,
        node: NodeKey,
        *,
        protected: tuple[Any, ...],
        legal_actions: tuple[ActionKey, ...],
    ) -> None:
        legal = tuple(sorted(
            {self._normalize_action(action) for action in legal_actions},
            key=action_sort_key,
        ))
        row = NodeRecord(tuple(protected), legal)
        old = self.nodes.get(node)
        if old is not None and old != row:
            raise ValueError("same raw observation has conflicting grounded contract")
        self.nodes[node] = row

    def observe_transition(
        self,
        source: NodeKey,
        action: ActionKey,
        target: NodeKey,
        *,
        outcome: Outcome,
    ) -> None:
        if source not in self.nodes or target not in self.nodes:
            raise ValueError("transition endpoints must be observed first")
        key = self._normalize_action(action)
        self.edges[source][key].add((outcome, target))

    @staticmethod
    def _class_ids(signatures: dict[NodeKey, Any]) -> dict[NodeKey, int]:
        unique = sorted({repr(value): value for value in signatures.values()})
        ids = {key: index for index, key in enumerate(unique)}
        return {node: ids[repr(value)] for node, value in signatures.items()}

    @staticmethod
    def _same_partition(
        left: dict[NodeKey, int],
        right: dict[NodeKey, int],
    ) -> bool:
        if set(left) != set(right):
            return False
        def groups(rows):
            out: dict[int, set[NodeKey]] = defaultdict(set)
            for node, class_id in rows.items():
                out[int(class_id)].add(node)
            return {frozenset(group) for group in out.values()}
        return groups(left) == groups(right)

    def _base_signatures(self) -> dict[NodeKey, Any]:
        return {
            node: (row.protected, row.legal_actions)
            for node, row in self.nodes.items()
        }

    def _observed_actions(self, node: NodeKey) -> set[ActionKey]:
        return {
            action
            for action, rows in self.edges.get(node, {}).items()
            if rows
        }

    def _step_signatures(
        self,
        classes: dict[NodeKey, int],
    ) -> dict[NodeKey, Any]:
        out: dict[NodeKey, Any] = {}
        for node, row in self.nodes.items():
            admitted = sorted(
                set(row.legal_actions) | self._observed_actions(node),
                key=action_sort_key,
            )
            action_rows = []
            for action in admitted:
                observed = self.edges.get(node, {}).get(action, set())
                if not observed:
                    action_rows.append((action, self.UNKNOWN))
                    continue
                relation = tuple(sorted(
                    (repr(outcome), int(classes[target]))
                    for outcome, target in observed
                ))
                action_rows.append((action, relation))
            out[node] = (
                row.protected,
                row.legal_actions,
                tuple(action_rows),
            )
        return out

    def partitions(self, max_depth: int = 8) -> list[dict[NodeKey, int]]:
        if max_depth < 0:
            raise ValueError("nonnegative quotient depth required")
        if not self.nodes:
            return []
        classes = self._class_ids(self._base_signatures())
        result = [classes]
        for _ in range(max_depth):
            nxt = self._class_ids(self._step_signatures(classes))
            result.append(nxt)
            if self._same_partition(nxt, classes):
                break
            classes = nxt
        return result

    def _members(self, classes: dict[NodeKey, int]) -> dict[int, list[NodeKey]]:
        out: dict[int, list[NodeKey]] = defaultdict(list)
        for node, class_id in classes.items():
            out[int(class_id)].append(node)
        return out

    def _action_relation(
        self,
        node: NodeKey,
        action: ActionKey,
        classes: dict[NodeKey, int],
    ) -> set[tuple[str, int]]:
        return {
            (repr(outcome), int(classes[target]))
            for outcome, target in self.edges.get(node, {}).get(action, set())
        }

    def fully_observed_pair(self, left: NodeKey, right: NodeKey) -> bool:
        lrow, rrow = self.nodes[left], self.nodes[right]
        if lrow.legal_actions != rrow.legal_actions or not lrow.legal_actions:
            return False
        la = self._observed_actions(left)
        ra = self._observed_actions(right)
        return set(lrow.legal_actions) <= la and set(rrow.legal_actions) <= ra

    def evidence_stats(self, classes: dict[NodeKey, int]) -> dict[str, int | float]:
        members = self._members(classes)
        merged_pairs = supported = full = contradictory = 0
        for group in members.values():
            for left, right in combinations(group, 2):
                merged_pairs += 1
                la = self._observed_actions(left)
                ra = self._observed_actions(right)
                common = la & ra
                supported += int(bool(common))
                contradictory += int(any(
                    self._action_relation(left, action, classes)
                    != self._action_relation(right, action, classes)
                    for action in common
                ))
                full += int(self.fully_observed_pair(left, right))

        ambiguous = 0
        for node, by_action in self.edges.items():
            for action, rows in by_action.items():
                relation = {
                    (repr(outcome), int(classes[target]))
                    for outcome, target in rows
                }
                ambiguous += int(len(relation) > 1)

        n = len(self.nodes)
        count = len(set(classes.values()))
        return {
            "raw_states": n,
            "quotient_states": count,
            "compression": n / max(1, count),
            "merged_pairs": merged_pairs,
            "supported_merged_pairs": supported,
            "fully_observed_merged_pairs": full,
            "unsupported_or_partial_pairs": merged_pairs - full,
            "contradictory_merged_pairs": contradictory,
            "ambiguous_observed_edges": ambiguous,
            "largest_class": max((len(group) for group in members.values()), default=0),
        }

    def summary(self, max_depth: int = 8) -> dict[str, Any]:
        parts = self.partitions(max_depth=max_depth)
        stabilized = bool(
            len(parts) >= 2 and self._same_partition(parts[-1], parts[-2])
        )
        final_depth = max(0, len(parts) - 1)
        selected = {
            depth
            for depth in (0, 1, 2, 4, 8, 16, 32, 64, final_depth)
            if depth < len(parts)
        }
        return {
            "nodes": len(self.nodes),
            "observed_transitions": sum(
                len(rows)
                for by_action in self.edges.values()
                for rows in by_action.values()
            ),
            "depths": [
                {"depth": depth, **self.evidence_stats(parts[depth])}
                for depth in sorted(selected)
            ],
            "stabilized": stabilized,
            "stabilization_depth": final_depth if stabilized else None,
            "depth_bound": max_depth,
        }

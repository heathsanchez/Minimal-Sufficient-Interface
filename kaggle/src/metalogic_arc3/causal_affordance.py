from __future__ import annotations

from collections import Counter, OrderedDict
from dataclasses import dataclass
from typing import Any, Iterable

ActionKey = tuple[int, int | None, int | None]
Grid = tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class EffectSignature:
    changed: int
    bbox_w: int
    bbox_h: int
    dx_sign: int
    dy_sign: int
    components: int
    directness: float

    def structural(self) -> tuple[int, int, int, int, int, int]:
        return (
            self.changed,
            self.bbox_w,
            self.bbox_h,
            self.dx_sign,
            self.dy_sign,
            self.components,
        )


def _sign(value: float) -> int:
    return 1 if value > 0 else -1 if value < 0 else 0


def _changed_cells(before: Grid, after: Grid) -> list[tuple[int, int]]:
    if len(before) != len(after):
        return []
    if before and after and len(before[0]) != len(after[0]):
        return []
    return [
        (x, y)
        for y, (row_before, row_after) in enumerate(zip(before, after))
        for x, (a, b) in enumerate(zip(row_before, row_after))
        if a != b
    ]


def _component_count(cells: Iterable[tuple[int, int]]) -> int:
    remaining = set(cells)
    count = 0
    while remaining:
        count += 1
        stack = [remaining.pop()]
        while stack:
            x, y = stack.pop()
            for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
    return count


def effect_signature(before: Grid, after: Grid, action: ActionKey) -> EffectSignature:
    cells = _changed_cells(before, after)
    if not cells:
        return EffectSignature(0, 0, 0, 0, 0, 0, 0.0)

    xs = [x for x, _ in cells]
    ys = [y for _, y in cells]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)

    action_id, ax, ay = action
    if action_id == 6 and ax is not None and ay is not None:
        nearest = min(abs(ax - x) + abs(ay - y) for x, y in cells)
        directness = 1.0 / (1.0 + nearest)
        dx_sign = _sign(cx - ax)
        dy_sign = _sign(cy - ay)
    else:
        # Primitive actions have no spatial intervention coordinate. Their
        # controllability must therefore be established through consistency or
        # reversibility rather than a fabricated spatial penalty.
        directness = 1.0
        dx_sign = 0
        dy_sign = 0

    return EffectSignature(
        changed=len(cells),
        bbox_w=max_x - min_x + 1,
        bbox_h=max_y - min_y + 1,
        dx_sign=dx_sign,
        dy_sign=dy_sign,
        components=_component_count(cells),
        directness=directness,
    )


class AffordanceMemory:
    """Bounded evidence for action-conditioned controllable structure.

    This stores observations, not universal causal laws. A descriptor becomes
    more useful when its observed effects are spatially direct (where that is
    meaningful), structurally repeatable, or part of an observed reversible
    transition. Parameter equivalence is defeasible and only collapses actions
    after the same descriptor has produced a shared structural effect class.
    """

    def __init__(self, limit: int = 2048) -> None:
        if limit < 1:
            raise ValueError("positive affordance-memory bound required")
        self.limit = int(limit)
        self._rows: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._action_signatures: OrderedDict[
            tuple[str, ActionKey], Counter[tuple[Any, ...]]
        ] = OrderedDict()
        self._transitions: OrderedDict[tuple[str, ActionKey], str] = OrderedDict()

    @staticmethod
    def _action(value: ActionKey | Iterable[Any]) -> ActionKey:
        action_id, x, y = tuple(value)
        return (
            int(action_id),
            None if x is None else int(x),
            None if y is None else int(y),
        )

    @staticmethod
    def _signature(value: EffectSignature | Iterable[Any]) -> tuple[Any, ...]:
        if isinstance(value, EffectSignature):
            return value.structural()
        return tuple(value)

    def _trim(self) -> None:
        while len(self._rows) > self.limit:
            descriptor, _ = self._rows.popitem(last=False)
            for key in [key for key in self._action_signatures if key[0] == descriptor]:
                del self._action_signatures[key]
        while len(self._action_signatures) > self.limit * 4:
            self._action_signatures.popitem(last=False)
        while len(self._transitions) > self.limit * 4:
            self._transitions.popitem(last=False)

    def record(
        self,
        context: str,
        action: ActionKey,
        descriptor: str,
        signature: EffectSignature | Iterable[Any],
        *,
        directness: float | None = None,
        target: str | None = None,
    ) -> None:
        descriptor = str(descriptor)
        action = self._action(action)
        structural = self._signature(signature)
        if directness is None:
            directness = signature.directness if isinstance(signature, EffectSignature) else 0.0
        directness = max(0.0, min(1.0, float(directness)))

        row = self._rows.setdefault(
            descriptor,
            {"n": 0, "directness": 0.0, "signatures": Counter()},
        )
        row["n"] += 1
        row["directness"] += directness
        row["signatures"][structural] += 1
        self._rows.move_to_end(descriptor)

        key = (descriptor, action)
        counts = self._action_signatures.setdefault(key, Counter())
        counts[structural] += 1
        self._action_signatures.move_to_end(key)

        if target is not None:
            self._transitions[(str(context), action)] = str(target)
            self._transitions.move_to_end((str(context), action))
        self._trim()

    def affordance_score(self, descriptor: str) -> float:
        row = self._rows.get(str(descriptor))
        if not row:
            return 0.0
        n = int(row["n"])
        direct = float(row["directness"]) / n
        dominant = max(row["signatures"].values(), default=0) / n
        # Repeatability and intervention/effect alignment are independent
        # evidence. The small support term prevents a one-shot visual novelty
        # from outranking a repeatedly controlled variable.
        support = min(1.0, n / 3.0)
        return direct * dominant * (0.5 + 0.5 * support)

    def parameter_equivalent(
        self,
        descriptor: str,
        left: ActionKey,
        right: ActionKey,
    ) -> bool:
        left_counts = self._action_signatures.get((str(descriptor), self._action(left)))
        right_counts = self._action_signatures.get((str(descriptor), self._action(right)))
        if not left_counts or not right_counts:
            return False
        return bool(set(left_counts).intersection(right_counts))

    def has_reversible_pair(self, source: str, action: ActionKey, target: str) -> bool:
        source = str(source)
        target = str(target)
        if self._transitions.get((source, self._action(action))) != target:
            return False
        return any(
            candidate_source == target and candidate_target == source
            for (candidate_source, _candidate_action), candidate_target in self._transitions.items()
        )

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Hashable, Iterable

from .consequence_arc import (
    RelationalEffect,
    RelationalObservation,
    SemanticAction,
)
from .protected_future import (
    ExplorationBoundary,
    FiniteMachine,
    Transition,
    UnknownResidual,
    canonical_digest,
)
from .semantic_path import _matrix


Cell = tuple[int, int]


def project_route_after_waypoint(
    actions: Iterable[Hashable],
    positions: Iterable[Hashable],
    *,
    waypoints: Iterable[Hashable],
    target_arity: int,
) -> tuple[Hashable, ...] | UnknownResidual:
    """Project the route suffix selected by one visible interior waypoint."""
    actions = tuple(actions)
    positions = tuple(positions)
    if len(positions) != len(actions) + 1:
        return UnknownResidual(
            "target.projection@1",
            "route_position_arity",
        )
    waypoint_set = set(waypoints)
    on_route = tuple(
        (index, position)
        for index, position in enumerate(positions[1:-1], start=1)
        if position in waypoint_set
    )
    if len(on_route) != 1:
        return UnknownResidual(
            "target.projection@1",
            "on_route_waypoint_not_unique",
            (f"observed={len(on_route)}",),
        )
    program = actions[on_route[0][0]:]
    if len(program) != target_arity:
        return UnknownResidual(
            "target.projection@1",
            "waypoint_suffix_target_arity",
            (f"observed={len(program)}", f"required={target_arity}"),
        )
    return program


def observable_change_mask(
    before: Iterable[Hashable],
    after: Iterable[Hashable],
) -> tuple[int, ...] | UnknownResidual:
    """Encode coordinate-wise consequential change without naming values."""
    before = tuple(before)
    after = tuple(after)
    if len(before) != len(after):
        return UnknownResidual(
            "observer.correspondence@1",
            "observation_coordinate_arity",
        )
    return tuple(int(left != right) for left, right in zip(before, after))


def align_marker_events(
    events: Iterable[tuple[Cell, Hashable]],
    *,
    target_arity: int,
) -> tuple[Hashable, ...] | UnknownResidual:
    """Align event observations by the spatial order of unique marker cells."""
    events = tuple(events)
    positions = tuple(position for position, _ in events)
    if len(set(positions)) != len(positions):
        return UnknownResidual(
            "target.projection@1",
            "marker_position_not_unique",
        )
    if len(events) != target_arity:
        return UnknownResidual(
            "target.projection@1",
            "marker_event_target_arity",
            (f"observed={len(events)}", f"required={target_arity}"),
        )
    return tuple(observation for _, observation in sorted(events))


def compress_observable_trace(
    initial_observation: Hashable,
    successor_observations: Iterable[Hashable],
    *,
    target_arity: int,
) -> tuple[Hashable, ...] | UnknownResidual:
    """Return the stutter-invariant trace of protected observations."""
    trace = [initial_observation]
    for observation in successor_observations:
        if observation != trace[-1]:
            trace.append(observation)
    if len(trace) != target_arity:
        return UnknownResidual(
            "target.projection@1",
            "observable_trace_target_arity",
            (f"observed={len(trace)}", f"required={target_arity}"),
        )
    return tuple(trace)


def project_goal_phase_transitions(
    actions: Iterable[Hashable],
    cell_supports: Iterable[Iterable[Hashable]],
    *,
    target_arity: int,
) -> tuple[Hashable, ...] | UnknownResidual:
    """Project route transitions whose destination belongs to the goal phase.

    Phase membership is relational: a destination's visible token support must
    be a non-empty subset of the goal cell's support.  This admits marked goal
    phase cells without naming a color or pairing route indices.
    """
    actions = tuple(actions)
    supports = tuple(frozenset(support) for support in cell_supports)
    if len(supports) != len(actions) + 1:
        return UnknownResidual(
            "target.projection@1",
            "route_cell_support_arity",
        )
    goal_support = supports[-1]
    if not goal_support:
        return UnknownResidual(
            "target.projection@1",
            "empty_goal_support",
        )
    program = tuple(
        action
        for action, destination in zip(actions, supports[1:])
        if destination and destination <= goal_support
    )
    if len(program) != target_arity:
        return UnknownResidual(
            "target.projection@1",
            "goal_phase_target_arity",
            (f"observed={len(program)}", f"required={target_arity}"),
        )
    return program


def _components(cells: set[Cell]) -> tuple[frozenset[Cell], ...]:
    unseen = set(cells)
    result = []
    while unseen:
        seed = min(unseen)
        unseen.remove(seed)
        component = {seed}
        frontier = [seed]
        while frontier:
            row, col = frontier.pop()
            for neighbor in (
                (row - 1, col),
                (row + 1, col),
                (row, col - 1),
                (row, col + 1),
            ):
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    component.add(neighbor)
                    frontier.append(neighbor)
        result.append(frozenset(component))
    return tuple(result)


def _normalized_shape(cells: Iterable[Cell]) -> tuple[Cell, ...]:
    cells = tuple(cells)
    top = min(row for row, _ in cells)
    left = min(col for _, col in cells)
    return tuple(sorted((row - top, col - left) for row, col in cells))


def relational_signature(frame) -> tuple:
    """Color- and translation-invariant visible component relations."""
    grid = _matrix(frame)
    counts = Counter(value for row in grid for value in row)
    background = min(
        (value for value, count in counts.items() if count == max(counts.values())),
        key=repr,
    )
    colored_cells: dict[int, set[Cell]] = {}
    for row, line in enumerate(grid):
        for col, value in enumerate(line):
            if value != background:
                colored_cells.setdefault(value, set()).add((row, col))
    if not colored_cells:
        return ("relational-grid@1", (), ())

    all_cells = set().union(*colored_cells.values())
    origin_row = min(row for row, _ in all_cells)
    origin_col = min(col for _, col in all_cells)
    role_descriptors = {}
    for color, cells in colored_cells.items():
        shapes = tuple(sorted(_normalized_shape(component) for component in _components(cells)))
        placements = tuple(
            sorted(
                (
                    min(row for row, _ in component) - origin_row,
                    min(col for _, col in component) - origin_col,
                    _normalized_shape(component),
                )
                for component in _components(cells)
            )
        )
        role_descriptors[color] = (shapes, placements)
    ordered_colors = tuple(
        sorted(colored_cells, key=lambda color: repr(role_descriptors[color]))
    )
    role_index = {color: index for index, color in enumerate(ordered_colors)}
    cells = tuple(
        sorted(
            (
                row - origin_row,
                col - origin_col,
                role_index[value],
            )
            for row, line in enumerate(grid)
            for col, value in enumerate(line)
            if value != background
        )
    )
    roles = tuple(role_descriptors[color] for color in ordered_colors)
    return "relational-grid@1", cells, roles


def relational_observation(frame) -> RelationalObservation:
    _, cells, roles = relational_signature(frame)
    objects = tuple(
        ("role", index, role)
        for index, role in enumerate(roles)
    )
    relations = tuple(
        ("cell", row, col, role)
        for row, col, role in cells
    )
    return RelationalObservation.build(objects=objects, relations=relations)


@dataclass(frozen=True)
class MacroEffect:
    action: SemanticAction
    observations: tuple[RelationalObservation, ...]
    effect: RelationalEffect


def _without_stutter(values):
    result = []
    for value in values:
        if not result or value != result[-1]:
            result.append(value)
    return tuple(result)


def local_effect_features(frames) -> dict[str, Hashable]:
    grids = tuple(_matrix(frame) for frame in frames)
    dimensions = {(len(grid), len(grid[0])) for grid in grids if grid}
    if len(grids) < 2 or len(dimensions) != 1:
        raise ValueError("effect_frame_shape")

    backgrounds = tuple(
        min(
            Counter(cell for row in grid for cell in row).items(),
            key=lambda item: (-item[1], repr(item[0])),
        )[0]
        for grid in grids
    )
    foreground = tuple(
        {
            (row, col): cell
            for row, line in enumerate(grid)
            for col, cell in enumerate(line)
            if cell != background
        }
        for grid, background in zip(grids, backgrounds)
    )
    colors = set().union(*(set(snapshot.values()) for snapshot in foreground))
    if not colors:
        return {
            "action.arity@1": len(grids) - 1,
            "trace.empty@1": True,
        }

    all_cells = set().union(*(set(snapshot) for snapshot in foreground))
    origin = (
        min(row for row, _ in all_cells),
        min(col for _, col in all_cells),
    )
    descriptors = {
        color: tuple(
            tuple(
                sorted(
                    (row - origin[0], col - origin[1])
                    for (row, col), value in snapshot.items()
                    if value == color
                )
            )
            for snapshot in foreground
        )
        for color in colors
    }
    ordered_colors = tuple(
        sorted(colors, key=lambda color: canonical_digest(descriptors[color]))
    )
    role = {color: index for index, color in enumerate(ordered_colors)}
    role_snapshots = tuple(
        {
            cell: role[color]
            for cell, color in snapshot.items()
        }
        for snapshot in foreground
    )
    dynamic = {
        cell
        for cell in all_cells
        if len({snapshot.get(cell) for snapshot in role_snapshots}) > 1
    }
    if not dynamic:
        dynamic = all_cells
    context = dynamic | {
        neighbor
        for row, col in dynamic
        for neighbor in (
            (row - 1, col),
            (row + 1, col),
            (row, col - 1),
            (row, col + 1),
        )
        if neighbor in all_cells
    }
    local_origin = (
        min(row for row, _ in context),
        min(col for _, col in context),
    )
    roles = tuple(
        tuple(
            sorted(
                (
                    row - local_origin[0],
                    col - local_origin[1],
                    snapshot[(row, col)],
                )
                for row, col in context
                if (row, col) in snapshot
            )
        )
        for snapshot in role_snapshots
    )
    occupancy = tuple(
        tuple((row, col) for row, col, _ in snapshot)
        for snapshot in roles
    )
    return {
        "action.arity@1": len(grids) - 1,
        "support.context@1": tuple(
            sorted(
                (row - local_origin[0], col - local_origin[1])
                for row, col in context
            )
        ),
        "trace.occupancy@1": occupancy,
        "trace.roles@1": roles,
        "trace.stutter@1": _without_stutter(roles),
    }


def relational_effect(frames) -> RelationalEffect:
    return RelationalEffect.build(local_effect_features(frames))


def macro_effect(frames, controls) -> MacroEffect:
    frames = tuple(frames)
    observations = tuple(relational_observation(frame) for frame in frames)
    controls = tuple(controls)
    if len(observations) != len(controls) + 1:
        raise ValueError("macro_frame_control_arity")
    return MacroEffect(
        SemanticAction("macro", controls),
        observations,
        relational_effect(frames),
    )


@dataclass(frozen=True)
class ArcObservation:
    state_id: str
    signature: tuple
    level: int
    terminal: bool
    active_port: int | None
    history: tuple[Hashable, ...]

    @property
    def protected(self):
        return self.signature, self.level, self.terminal, self.active_port


class ArcTraceBuilder:
    def __init__(
        self,
        *,
        actions: Iterable[Hashable],
        max_depth: int,
        max_states: int,
    ):
        self.actions = tuple(actions)
        self.boundary = ExplorationBoundary(self.actions, max_depth, max_states)
        self._states: dict[str, ArcObservation] = {}
        self._transitions: dict[tuple[str, Hashable], Transition] = {}
        self._residual: UnknownResidual | None = None

    def observe(
        self,
        frame,
        *,
        level: int,
        terminal: bool,
        active_port: int | None = None,
        history: Iterable[Hashable] = (),
    ) -> ArcObservation:
        signature = relational_signature(frame)
        history_tuple = tuple(history)
        state_id = canonical_digest(
            {
                "signature": signature,
                "level": int(level),
                "terminal": bool(terminal),
                "active_port": active_port,
                "history": history_tuple,
            }
        )
        observation = ArcObservation(
            state_id,
            signature,
            int(level),
            bool(terminal),
            active_port,
            history_tuple,
        )
        self._states[state_id] = observation
        return observation

    def record(
        self,
        source: ArcObservation,
        action: Hashable,
        target: ArcObservation,
        *,
        effect: Hashable,
        required_control: Hashable | None = None,
    ) -> None:
        if action not in self.actions:
            raise ValueError("unknown_arc_action")
        if source.state_id not in self._states or target.state_id not in self._states:
            raise ValueError("unobserved_arc_state")
        transition = Transition(
            source.state_id,
            action,
            target.state_id,
            target.protected,
            effect,
            required_control,
        )
        key = source.state_id, action
        previous = self._transitions.get(key)
        if previous is not None and previous != transition:
            self._residual = UnknownResidual(
                "transition.nondeterministic@1",
                "same_state_action_incompatible_response",
                (previous.target, transition.target),
            )
            return
        self._transitions[key] = transition

    def machine(self) -> FiniteMachine | UnknownResidual:
        if self._residual is not None:
            return self._residual
        if len(self._states) > self.boundary.max_states:
            return UnknownResidual(
                "exploration.incomplete@1",
                "state_budget_exceeded",
            )
        transitions = dict(self._transitions)
        for state in self._states.values():
            if state.terminal:
                for action in self.actions:
                    transitions.setdefault(
                        (state.state_id, action),
                        Transition(
                            state.state_id,
                            action,
                            state.state_id,
                            state.protected,
                            "terminal",
                        ),
                    )
        missing = tuple(
            (state_id, action)
            for state_id in self._states
            for action in self.actions
            if (state_id, action) not in transitions
        )
        if missing:
            return UnknownResidual(
                "exploration.incomplete@1",
                "missing_declared_transitions",
                tuple(f"{state_id}:{action!r}" for state_id, action in missing),
            )
        return FiniteMachine.build(
            states=self._states,
            actions=self.actions,
            transitions=transitions.values(),
            observations={
                state_id: observation.protected
                for state_id, observation in self._states.items()
            },
            accepting={
                state_id for state_id, observation in self._states.items() if observation.terminal
            },
            boundary=self.boundary,
        )

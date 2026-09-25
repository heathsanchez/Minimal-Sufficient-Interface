from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping, Sequence
import json
import os
from pathlib import Path
import subprocess
from typing import Hashable

from metalogic_arc3.protected_future import canonical_digest
from metalogic_arc3.semantic_path import (
    _bbox,
    _complement_translation,
    _find_board,
    _matrix,
    _selector_controls,
)


SCHEMA = "arc3.g6-event-cell-relation@1"
ROUTE = "RRRRUULLUUUL"
EVENT_STEPS = (2, 4, 6, 8, 10, 12)
REPLAY_COUNT = 2
ACTION_BUDGET = 12


def route_positions(start: tuple[int, int], route: str) -> tuple[tuple[int, int], ...]:
    deltas = {
        "U": (-1, 0),
        "D": (1, 0),
        "L": (0, -1),
        "R": (0, 1),
    }
    positions = [tuple(start)]
    for control in route:
        if control not in deltas:
            raise ValueError(f"unknown_route_control:{control}")
        row, column = positions[-1]
        delta_row, delta_column = deltas[control]
        positions.append((row + delta_row, column + delta_column))
    return tuple(positions)


def extract_cell_patch(
    grid: Sequence[Sequence[Hashable]],
    *,
    board_top: int,
    board_left: int,
    cell: tuple[int, int],
    cell_size: int,
) -> tuple[tuple[Hashable, ...], ...]:
    visible = _tuple_grid(grid)
    row, column = cell
    if row < 0 or column < 0 or cell_size < 1:
        raise ValueError("cell_bounds")
    top = board_top + row * cell_size
    left = board_left + column * cell_size
    if (
        top < 0
        or left < 0
        or top + cell_size > len(visible)
        or left + cell_size > len(visible[0])
    ):
        raise ValueError("cell_bounds")
    return tuple(
        tuple(visible[top + delta_row][left + delta_column] for delta_column in range(cell_size))
        for delta_row in range(cell_size)
    )


def _tuple_grid(value: Sequence[Sequence[Hashable]]) -> tuple[tuple[Hashable, ...], ...]:
    result = tuple(tuple(row) for row in value)
    if not result or not result[0] or any(len(row) != len(result[0]) for row in result):
        raise ValueError("rectangular_grid_required")
    return result


def canonical_patch_trace(
    patches: Iterable[Sequence[Sequence[Hashable]]],
) -> tuple[tuple[tuple[int, ...], ...], ...]:
    """Canonicalize a patch trace by equality pattern, not palette values."""
    patches = tuple(_tuple_grid(patch) for patch in patches)
    if not patches:
        raise ValueError("empty_patch_trace")
    descriptors: dict[Hashable, list[tuple[int, int, int]]] = {}
    for phase, patch in enumerate(patches):
        for row, line in enumerate(patch):
            for column, value in enumerate(line):
                descriptors.setdefault(value, []).append((phase, row, column))
    ordered = sorted(descriptors, key=lambda value: tuple(descriptors[value]))
    roles = {value: index for index, value in enumerate(ordered)}
    return tuple(
        tuple(tuple(roles[value] for value in row) for row in patch)
        for patch in patches
    )


def _pixel_components(crop: tuple[tuple[Hashable, ...], ...]):
    height, width = len(crop), len(crop[0])
    unseen = {(row, column) for row in range(height) for column in range(width)}
    components = []
    while unseen:
        seed = min(unseen)
        value = crop[seed[0]][seed[1]]
        unseen.remove(seed)
        component = {seed}
        queue = deque((seed,))
        while queue:
            row, column = queue.popleft()
            for neighbor in (
                (row - 1, column),
                (row + 1, column),
                (row, column - 1),
                (row, column + 1),
            ):
                if (
                    neighbor in unseen
                    and crop[neighbor[0]][neighbor[1]] == value
                ):
                    unseen.remove(neighbor)
                    component.add(neighbor)
                    queue.append(neighbor)
        components.append(component)
    return tuple(components)


def _shape(component: set[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    top = min(row for row, _ in component)
    left = min(column for _, column in component)
    return tuple(sorted((row - top, column - left) for row, column in component))


def _cell_pixels(cell: tuple[int, int], cell_size: int) -> set[tuple[int, int]]:
    row, column = cell
    return {
        (row * cell_size + delta_row, column * cell_size + delta_column)
        for delta_row in range(cell_size)
        for delta_column in range(cell_size)
    }


def _distance(
    component: set[tuple[int, int]],
    pixels: set[tuple[int, int]],
) -> int:
    return min(
        abs(left_row - right_row) + abs(left_column - right_column)
        for left_row, left_column in component
        for right_row, right_column in pixels
    )


def component_relation_descriptors(
    grid: Sequence[Sequence[Hashable]],
    *,
    board_top: int,
    board_left: int,
    board_rows: int,
    board_columns: int,
    cell_size: int,
    trace_cells: Iterable[tuple[int, int]],
) -> tuple[tuple[Hashable, ...], ...]:
    """Describe board components only by shape and relation to a route trace."""
    visible = _tuple_grid(grid)
    height = board_rows * cell_size
    width = board_columns * cell_size
    if board_top < 0 or board_left < 0 or board_top + height > len(visible):
        raise ValueError("board_bounds")
    if board_left + width > len(visible[0]):
        raise ValueError("board_bounds")
    crop = tuple(
        tuple(visible[board_top + row][board_left + column] for column in range(width))
        for row in range(height)
    )
    cells = tuple(tuple(cell) for cell in trace_cells)
    if not cells:
        raise ValueError("empty_trace_cells")
    pixel_sets = tuple(_cell_pixels(cell, cell_size) for cell in cells)
    descriptors = []
    for component in _pixel_components(crop):
        relations = tuple(
            (len(component & pixels), _distance(component, pixels))
            for pixels in pixel_sets
        )
        descriptors.append(("component", _shape(component), relations))
    return tuple(sorted(descriptors, key=canonical_digest))


def event_relation_signature(
    controls: str,
    trace_patches: Iterable[Sequence[Sequence[Hashable]]],
    component_relations: Iterable[Hashable],
) -> str:
    if len(controls) != 2 or any(control not in "UDLR" for control in controls):
        raise ValueError("event_control_pair")
    meaning = (
        "g6-event-cell-relation@1",
        controls,
        canonical_patch_trace(trace_patches),
        tuple(sorted(tuple(component_relations), key=canonical_digest)),
    )
    return canonical_digest(meaning)


def build_event_records(
    frames: Iterable[Sequence[Sequence[Hashable]]],
    *,
    positions: Iterable[tuple[int, int]],
    marker_events: Iterable[tuple[int, tuple[int, int]]],
    board_top: int,
    board_left: int,
    board_rows: int,
    board_columns: int,
    cell_size: int,
) -> list[dict[str, object]]:
    """Align each visible marker event to its three-cell two-control trace."""
    frames = tuple(_tuple_grid(frame) for frame in frames)
    positions = tuple(tuple(cell) for cell in positions)
    events = tuple((int(step), tuple(marker)) for step, marker in marker_events)
    if len(frames) != len(ROUTE) + 1 or len(positions) != len(frames):
        raise ValueError("route_frame_census")
    if tuple(step for step, _ in events) != EVENT_STEPS:
        raise ValueError("marker_event_steps")
    marker_positions = tuple(marker for _, marker in events)
    if any(len(marker) != 2 for marker in marker_positions) or len(set(marker_positions)) != len(events):
        raise ValueError("marker_event_positions")
    spatial_rank = {
        marker: rank for rank, marker in enumerate(sorted(marker_positions))
    }
    records = []
    previous_step = 0
    for step, marker in events:
        cells = positions[step - 2:step + 1]
        if len(cells) != 3 or any(
            row < 0 or row >= board_rows or column < 0 or column >= board_columns
            for row, column in cells
        ):
            raise ValueError("route_cell_bounds")
        patches = tuple(
            extract_cell_patch(
                frames[phase],
                board_top=board_top,
                board_left=board_left,
                cell=cell,
                cell_size=cell_size,
            )
            for phase, cell in zip(range(step - 2, step + 1), cells)
        )
        component_relations = component_relation_descriptors(
            frames[0],
            board_top=board_top,
            board_left=board_left,
            board_rows=board_rows,
            board_columns=board_columns,
            cell_size=cell_size,
            trace_cells=cells,
        )
        controls = ROUTE[previous_step:step]
        signature_inputs = {
            "controls": controls,
            "patch_trace": canonical_patch_trace(patches),
            "component_relations": component_relations,
        }
        records.append(
            {
                "route_step": step,
                "controls": controls,
                "cells": [list(cell) for cell in cells],
                "trace_patches": [[list(row) for row in patch] for patch in patches],
                "marker_position": list(marker),
                "marker_rank": spatial_rank[marker],
                "signature_inputs": signature_inputs,
                "relation_signature": event_relation_signature(
                    controls,
                    patches,
                    component_relations,
                ),
            }
        )
        previous_step = step
    return records


def _validate_replay(replay: Mapping[str, object]) -> None:
    if replay.get("route") != ROUTE or tuple(replay.get("event_steps", ())) != EVENT_STEPS:
        raise ValueError("replay_boundary")
    if (
        replay.get("target_writes") != 0
        or replay.get("submit_clicks") != 0
        or replay.get("action_count") != ACTION_BUDGET
    ):
        raise ValueError("scientific_boundary")
    events = tuple(replay.get("events", ()))
    if len(events) != len(EVENT_STEPS):
        raise ValueError("event_census")
    expected_controls = tuple(
        ROUTE[start:stop]
        for start, stop in zip((0,) + EVENT_STEPS[:-1], EVENT_STEPS)
    )
    marker_positions = tuple(tuple(row.get("marker_position", ())) for row in events)
    expected_ranks = {
        marker: rank for rank, marker in enumerate(sorted(marker_positions))
    }
    if (
        any(len(marker) != 2 for marker in marker_positions)
        or len(set(marker_positions)) != len(events)
        or set(row.get("marker_rank") for row in events) != set(range(len(events)))
    ):
        raise ValueError("marker_alignment")
    for row, step, controls, marker in zip(
        events, EVENT_STEPS, expected_controls, marker_positions
    ):
        if (
            row.get("route_step") != step
            or row.get("controls") != controls
            or row.get("marker_rank") != expected_ranks[marker]
            or len(row.get("cells", ())) != 3
            or not row.get("relation_signature")
        ):
            raise ValueError("event_evidence")


def classify_replays(replays: Iterable[Mapping[str, object]]) -> dict[str, object]:
    replays = tuple(replays)
    if len(replays) != REPLAY_COUNT:
        return {
            "status": "RESIDUAL",
            "classification": "NON_EVIDENCE",
            "residual": {"reason": "independent_replay_count"},
            "separated_control_pairs": [],
        }
    try:
        for replay in replays:
            _validate_replay(replay)
    except ValueError as error:
        return {
            "status": "RESIDUAL",
            "classification": "NON_EVIDENCE",
            "residual": {"reason": str(error)},
            "separated_control_pairs": [],
        }
    semantic_rows = tuple(
        tuple(
            (event["controls"], event["relation_signature"])
            for event in replay["events"]
        )
        for replay in replays
    )
    alignment_rows = tuple(
        tuple(
            (
                event["route_step"],
                tuple(event["marker_position"]),
                event["marker_rank"],
                tuple(tuple(cell) for cell in event["cells"]),
            )
            for event in replay["events"]
        )
        for replay in replays
    )
    if len(set(semantic_rows)) != 1 or len(set(alignment_rows)) != 1:
        return {
            "status": "RESIDUAL",
            "classification": "NON_EVIDENCE",
            "residual": {"reason": "independent_replay_drift"},
            "separated_control_pairs": [],
        }
    grouped: dict[str, set[str]] = {}
    for controls, signature in semantic_rows[0]:
        grouped.setdefault(str(controls), set()).add(str(signature))
    separated = sorted(
        controls for controls, signatures in grouped.items()
        if sum(1 for pair, _ in semantic_rows[0] if pair == controls) > 1
        and len(signatures) > 1
    )
    if separated:
        return {
            "status": "SEPARATED",
            "classification": "RESPONSE_SEPARATOR_ONLY",
            "separated_control_pairs": separated,
        }
    return {
        "status": "REJECTED",
        "classification": "WARRANTED_NEGATIVE",
        "separated_control_pairs": [],
    }


def validate_result(result: Mapping[str, object], *, executing_head: str):
    if result.get("schema") != SCHEMA:
        raise ValueError("event_cell_schema")
    if result.get("head") != executing_head:
        raise ValueError("stale_evidence_head")
    if (
        result.get("target_writes") != 0
        or result.get("submit_clicks") != 0
        or result.get("model_calls") != 0
        or result.get("source_inspection") is not False
    ):
        raise ValueError("scientific_boundary")
    if result.get("route") != ROUTE or tuple(result.get("event_steps", ())) != EVENT_STEPS:
        raise ValueError("declared_census")
    if result.get("action_budget_per_replay") != ACTION_BUDGET:
        raise ValueError("action_budget_declaration")
    if result.get("independent_replay_count") != len(tuple(result.get("replays", ()))):
        raise ValueError("independent_replay_count")
    classification = classify_replays(result.get("replays", ()))
    for field in ("status", "classification", "separated_control_pairs"):
        if result.get(field) != classification.get(field):
            raise ValueError("classification_mismatch")
    return result


def _public_field(frame, name: str):
    return frame[name] if isinstance(frame, dict) else getattr(frame, name)


def _source_head() -> str:
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    return subprocess.check_output(
        ("git", "rev-parse", "HEAD"),
        cwd=Path(__file__).resolve().parents[1],
        text=True,
    ).strip()


def run_replay(
    *,
    enter_g6=None,
    clicker=None,
    find_board=None,
    find_translation=None,
    selector_controls=None,
) -> dict[str, object]:
    """Run the qualified route once and collect visible zero-write evidence."""
    if enter_g6 is None:
        from arc3_public_g6_paired_route import enter_g6 as public_enter_g6

        enter_g6 = public_enter_g6
    if clicker is None:
        import arc3_public_all_blue_to_gray_g2 as ab

        clicker = ab.click
    find_board = _find_board if find_board is None else find_board
    find_translation = (
        _complement_translation if find_translation is None else find_translation
    )
    selector_controls = (
        _selector_controls if selector_controls is None else selector_controls
    )
    env, frame = enter_g6()
    if int(_public_field(frame, "levels_completed")) != 5:
        raise ValueError("g6_entry_drift")
    initial = _matrix(frame)
    board_top, board_left = find_board(initial)
    mover, _, _, _ = find_translation(initial, board_top, board_left)
    mover_top, mover_left, _, _ = _bbox(mover)
    start = ((mover_top - board_top) // 4, (mover_left - board_left) // 4)
    positions = route_positions(start, ROUTE)
    if any(row < 0 or row >= 7 or column < 0 or column >= 7 for row, column in positions):
        raise ValueError("qualified_route_bounds")
    controls = {
        label: (y, x)
        for (x, y), label in selector_controls(initial)
    }
    if set(controls) != {"U", "D", "L", "R"}:
        raise ValueError("missing_control")
    frames = [initial]
    marker_events = []
    for step, control in enumerate(ROUTE, start=1):
        before = frames[-1]
        frame = clicker(env, controls[control])
        after = _matrix(frame)
        changes = tuple(
            (row, column)
            for row in range(board_top)
            for column in range(len(after[0]))
            if before[row][column] != after[row][column]
        )
        if len(changes) > 1:
            raise ValueError("non_singleton_marker_response")
        if changes:
            marker_events.append((step, changes[0]))
        frames.append(after)
    events = build_event_records(
        frames,
        positions=positions,
        marker_events=marker_events,
        board_top=board_top,
        board_left=board_left,
        board_rows=7,
        board_columns=7,
        cell_size=4,
    )
    replay = {
        "route": ROUTE,
        "event_steps": list(EVENT_STEPS),
        "start_cell": list(start),
        "route_positions": [list(cell) for cell in positions],
        "board_origin": [board_top, board_left],
        "events": events,
        "action_count": len(ROUTE),
        "target_writes": 0,
        "submit_clicks": 0,
    }
    _validate_replay(replay)
    return replay


def build_result(*, enter_g6=None, head: str | None = None, runner=None):
    runner = run_replay if runner is None else runner
    replays = []
    base = {
        "schema": SCHEMA,
        "head": head or _source_head(),
        "route": ROUTE,
        "event_steps": list(EVENT_STEPS),
        "action_budget_per_replay": ACTION_BUDGET,
        "target_writes": 0,
        "submit_clicks": 0,
        "model_calls": 0,
        "source_inspection": False,
        "claim_boundary": (
            "exact public tn36 G6; qualified route RRRRUULLUUUL; six visible "
            "two-step marker events; dynamic three-cell patches plus static board-component "
            "relations; two hard restarts; zero target writes and submit clicks"
        ),
    }
    try:
        for _ in range(REPLAY_COUNT):
            replays.append(runner(enter_g6=enter_g6))
    except Exception as error:
        classification = classify_replays(replays)
        result = {
            **base,
            **classification,
            "replays": replays,
            "independent_replay_count": len(replays),
            "residual": {
                "reason": "replay_exception",
                "error": f"{type(error).__name__}:{error}",
            },
        }
        validate_result(result, executing_head=str(result["head"]))
        return result
    classification = classify_replays(replays)
    result = {
        **base,
        **classification,
        "replays": replays,
        "independent_replay_count": len(replays),
    }
    validate_result(result, executing_head=str(result["head"]))
    return result


def main():
    result = build_result()
    out = Path(
        os.environ.get("OUTDIR", "evidence/arc3-public-g6-event-cell-relation")
    ).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(f"ARC3_PUBLIC_G6_EVENT_CELL_RELATION={result['status']}")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

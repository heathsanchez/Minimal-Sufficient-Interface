from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from hashlib import sha256

from metalogic_arc3.future_arc import (
    align_marker_events,
    compress_observable_trace,
    observable_change_mask,
    project_goal_phase_transitions,
    project_route_after_waypoint,
)
from metalogic_arc3.protected_future import (
    CompiledCapability,
    ExplorationBoundary,
    FiniteMachine,
    Transition,
    compile_capability,
    refine_partition,
)
from metalogic_arc3.semantic_path import (
    _bar_rows,
    _bbox,
    _complement_translation,
    _find_board,
    _matrix,
    _selector_controls,
    _source_bits,
    _submit,
)


OUT = Path(os.environ.get("OUTDIR", "evidence/arc3-public-g6-future-quotient")).resolve()
OUT.mkdir(parents=True, exist_ok=True)
ROUTE = "RRRRUULLUUUL"
ACTIONS = ("U", "D", "L", "R")
DELTAS = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}
REQUIRED_FIELDS = {
    "parent",
    "head",
    "status",
    "classification",
    "boundary",
    "states",
    "transitions",
    "classes",
    "witnesses",
    "congruence",
    "residual",
    "action_count",
    "model_calls",
    "source_inspection",
    "target_writes",
}


def validate_result(result):
    missing = sorted(REQUIRED_FIELDS - set(result))
    if missing:
        raise ValueError("missing_evidence_fields:" + ",".join(missing))
    if result["status"] == "DIAGNOSTIC" and result["target_writes"] != 0:
        raise ValueError("diagnostic_target_write")
    if result["model_calls"] != 0 or result["source_inspection"] is not False:
        raise ValueError("hard_scientific_boundary")


def _git_head():
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
    ).strip()


def _board_problem(frame):
    visible = _matrix(frame)
    board_top, board_left = _find_board(visible)
    mover, _, delta_row, delta_col = _complement_translation(
        visible,
        board_top,
        board_left,
    )
    mover_top, mover_left, _, _ = _bbox(mover)
    start = ((mover_top - board_top) // 4, (mover_left - board_left) // 4)
    goal = (start[0] + delta_row // 4, start[1] + delta_col // 4)
    blocked = set()
    for row in range(7):
        for col in range(7):
            values = [
                visible[board_top + 4 * row + dr][board_left + 4 * col + dc]
                for dr in range(4)
                for dc in range(4)
            ]
            if values.count(6) >= 8:
                blocked.add((row, col))
    blocked.discard(start)
    blocked.discard(goal)
    return start, goal, blocked


def _navigation_machine(start, goal, blocked):
    states = tuple(
        (row, col)
        for row in range(7)
        for col in range(7)
        if (row, col) not in blocked
    )
    observations = {}
    transitions = []
    for state in states:
        neighborhood = []
        for action in ACTIONS:
            dr, dc = DELTAS[action]
            candidate = state[0] + dr, state[1] + dc
            neighborhood.append(
                "open" if candidate in states else "blocked"
            )
        observations[state] = (state == goal, tuple(neighborhood))
    for state in states:
        for action in ACTIONS:
            if state == goal:
                target, effect = goal, "terminal"
            else:
                dr, dc = DELTAS[action]
                candidate = state[0] + dr, state[1] + dc
                target = candidate if candidate in states else state
                effect = "move" if candidate in states else "blocked"
            transitions.append(
                Transition(
                    state,
                    action,
                    target,
                    observations[target],
                    effect,
                    action,
                )
            )
    return FiniteMachine.build(
        states=states,
        actions=ACTIONS,
        transitions=transitions,
        observations=observations,
        accepting={goal},
        boundary=ExplorationBoundary(ACTIONS, len(ROUTE), len(states)),
    )


def diagnose_frame(frame):
    start, goal, blocked = _board_problem(frame)
    machine = _navigation_machine(start, goal, blocked)
    quotient = refine_partition(machine)
    route_positions = [start]
    current = start
    transition_map = {
        (transition.source, transition.action): transition.target
        for transition in machine.transitions
    }
    for action in ROUTE:
        current = transition_map[(current, action)]
        route_positions.append(current)
    if current != goal:
        raise AssertionError("qualified_route_did_not_reach_goal")
    route_transition_classes = [
        {
            "source_class": quotient.class_of(route_positions[index]),
            "action": action,
            "target_class": quotient.class_of(route_positions[index + 1]),
        }
        for index, action in enumerate(ROUTE)
    ]
    return machine, quotient, route_positions, route_transition_classes


def _route_cell_supports(frame, route_positions):
    visible = _matrix(frame)
    board_top, board_left = _find_board(visible)
    return tuple(
        frozenset(
            visible[board_top + 4 * row + dr][board_left + 4 * col + dc]
            for dr in range(4)
            for dc in range(4)
        )
        for row, col in route_positions
    )


def _checker_waypoints(frame):
    visible = _matrix(frame)
    board_top, board_left = _find_board(visible)
    waypoints = set()
    for row in range(7):
        for col in range(7):
            patch = tuple(
                tuple(
                    visible[board_top + 4 * row + dr][board_left + 4 * col + dc]
                    for dc in range(4)
                )
                for dr in range(4)
            )
            even = {patch[dr][dc] for dr in range(4) for dc in range(4) if (dr + dc) % 2 == 0}
            odd = {patch[dr][dc] for dr in range(4) for dc in range(4) if (dr + dc) % 2 == 1}
            if len(even) == len(odd) == 1 and even != odd:
                waypoints.add((row, col))
    return frozenset(waypoints)


def run_goal_phase_candidate(enter_g6):
    import arc3_public_all_blue_to_gray_g2 as ab

    env, frame = enter_g6()
    start_level = int(frame.levels_completed)
    _, _, route_positions, _ = diagnose_frame(frame)
    targets = _bar_rows(_matrix(frame), "right")
    cell_supports = _route_cell_supports(frame, route_positions)
    program = project_goal_phase_transitions(
        ROUTE,
        cell_supports,
        target_arity=len(targets[0]),
    )
    if not isinstance(program, tuple):
        return {
            "status": "UNKNOWN",
            "residual": {
                "missing_interface": program.missing_interface,
                "reason": program.reason,
                "evidence": list(program.evidence),
            },
            "target_writes": 0,
            "action_count": 0,
        }

    codes = {}
    actions = 0
    for (x, y), label in _selector_controls(_matrix(frame)):
        frame = ab.click(env, (y, x))
        actions += 1
        codes[label] = _source_bits(_matrix(frame))
    columns = tuple(codes[action] for action in program)
    writes = []
    for row_index, target_row in enumerate(targets):
        for column_index, (x, y) in enumerate(target_row):
            desired = columns[column_index][row_index]
            current = 1 if _matrix(frame)[y][x] == 5 else 0
            if current != desired:
                frame = ab.click(env, (y, x))
                actions += 1
                writes.append({
                    "row": row_index,
                    "column": column_index,
                    "value": desired,
                })
    submit = _submit(_matrix(frame))
    before_submit = _matrix(frame)
    frame = ab.click(env, (submit[1], submit[0]))
    actions += 1
    after_submit = _matrix(frame)
    response_changes = [
        {
            "row": row,
            "column": col,
            "before": before_submit[row][col],
            "after": after_submit[row][col],
        }
        for row in range(len(before_submit))
        for col in range(len(before_submit[0]))
        if before_submit[row][col] != after_submit[row][col]
    ]
    progressed = int(frame.levels_completed) > start_level or str(frame.state).endswith("WIN")
    return {
        "status": "PROGRESSED" if progressed else "RESIDUAL",
        "program": list(program),
        "cell_supports": [sorted(support, key=repr) for support in cell_supports],
        "codes": {label: list(code) for label, code in sorted(codes.items())},
        "columns": [list(column) for column in columns],
        "writes": writes,
        "target_writes": len(writes),
        "action_count": actions,
        "start_level": start_level,
        "end_level": int(frame.levels_completed),
        "end_state": str(frame.state),
        "progressed": progressed,
        "terminal_response": {
            "visible_change_count": len(response_changes),
            "visible_changes": response_changes,
        },
    }


def run_observable_trace_candidate(enter_g6):
    import arc3_public_all_blue_to_gray_g2 as ab

    env, frame = enter_g6()
    start_level = int(frame.levels_completed)
    targets = _bar_rows(_matrix(frame), "right")
    initial_source = _source_bits(_matrix(frame))
    codes = {}
    actions = 0
    for (x, y), label in _selector_controls(_matrix(frame)):
        frame = ab.click(env, (y, x))
        actions += 1
        codes[label] = _source_bits(_matrix(frame))
    columns = compress_observable_trace(
        initial_source,
        (codes[action] for action in ROUTE),
        target_arity=len(targets[0]),
    )
    if not isinstance(columns, tuple):
        return {
            "status": "UNKNOWN",
            "residual": {
                "missing_interface": columns.missing_interface,
                "reason": columns.reason,
                "evidence": list(columns.evidence),
            },
            "target_writes": 0,
            "action_count": actions,
        }

    writes = []
    for row_index, target_row in enumerate(targets):
        for column_index, (x, y) in enumerate(target_row):
            desired = columns[column_index][row_index]
            current = 1 if _matrix(frame)[y][x] == 5 else 0
            if current != desired:
                frame = ab.click(env, (y, x))
                actions += 1
                writes.append({
                    "row": row_index,
                    "column": column_index,
                    "value": desired,
                })
    submit = _submit(_matrix(frame))
    frame = ab.click(env, (submit[1], submit[0]))
    actions += 1
    progressed = int(frame.levels_completed) > start_level or str(frame.state).endswith("WIN")
    return {
        "status": "PROGRESSED" if progressed else "RESIDUAL",
        "initial_observation": list(initial_source),
        "route_observations": [list(codes[action]) for action in ROUTE],
        "columns": [list(column) for column in columns],
        "codes": {label: list(code) for label, code in sorted(codes.items())},
        "writes": writes,
        "target_writes": len(writes),
        "action_count": actions,
        "start_level": start_level,
        "end_level": int(frame.levels_completed),
        "end_state": str(frame.state),
        "progressed": progressed,
    }


def run_marker_aligned_candidate(enter_g6):
    import arc3_public_all_blue_to_gray_g2 as ab

    env, frame = enter_g6()
    start_level = int(frame.levels_completed)
    visible = _matrix(frame)
    board_top, _ = _find_board(visible)
    targets = _bar_rows(visible, "right")
    controls = {
        label: (y, x)
        for (x, y), label in _selector_controls(visible)
    }
    events = []
    previous_boundary = _source_bits(visible)
    actions = 0
    for control in ROUTE:
        before = _matrix(frame)
        frame = ab.click(env, controls[control])
        actions += 1
        after = _matrix(frame)
        marker_changes = [
            (row, col)
            for row in range(board_top)
            for col in range(len(after[0]))
            if before[row][col] != after[row][col]
        ]
        if len(marker_changes) > 1:
            return {
                "status": "UNKNOWN",
                "residual": {
                    "missing_interface": "observer.event-marker@1",
                    "reason": "non_singleton_marker_response",
                    "evidence": [repr(marker_changes)],
                },
                "target_writes": 0,
                "action_count": actions,
            }
        if marker_changes:
            current_boundary = _source_bits(after)
            change = observable_change_mask(previous_boundary, current_boundary)
            if not isinstance(change, tuple):
                raise AssertionError(change)
            events.append((marker_changes[0], change))
            previous_boundary = current_boundary

    columns = align_marker_events(events, target_arity=len(targets[0]))
    if not isinstance(columns, tuple):
        return {
            "status": "UNKNOWN",
            "residual": {
                "missing_interface": columns.missing_interface,
                "reason": columns.reason,
                "evidence": list(columns.evidence),
            },
            "events": [
                {"position": list(position), "observation": list(observation)}
                for position, observation in events
            ],
            "target_writes": 0,
            "action_count": actions,
        }

    writes = []
    for row_index, target_row in enumerate(targets):
        for column_index, (x, y) in enumerate(target_row):
            desired = columns[column_index][row_index]
            current = 1 if _matrix(frame)[y][x] == 5 else 0
            if current != desired:
                frame = ab.click(env, (y, x))
                actions += 1
                writes.append({
                    "row": row_index,
                    "column": column_index,
                    "value": desired,
                })
    submit = _submit(_matrix(frame))
    frame = ab.click(env, (submit[1], submit[0]))
    actions += 1
    progressed = int(frame.levels_completed) > start_level or str(frame.state).endswith("WIN")
    return {
        "status": "PROGRESSED" if progressed else "RESIDUAL",
        "events": [
            {"position": list(position), "observation": list(observation)}
            for position, observation in events
        ],
        "columns": [list(column) for column in columns],
        "writes": writes,
        "target_writes": len(writes),
        "action_count": actions,
        "start_level": start_level,
        "end_level": int(frame.levels_completed),
        "end_state": str(frame.state),
        "progressed": progressed,
    }


def run_waypoint_suffix_candidate(enter_g6):
    import arc3_public_all_blue_to_gray_g2 as ab

    env, frame = enter_g6()
    start_level = int(frame.levels_completed)
    _, _, route_positions, _ = diagnose_frame(frame)
    targets = _bar_rows(_matrix(frame), "right")
    waypoints = _checker_waypoints(frame)
    program = project_route_after_waypoint(
        ROUTE,
        route_positions,
        waypoints=waypoints,
        target_arity=len(targets[0]),
    )
    if not isinstance(program, tuple):
        return {
            "status": "UNKNOWN",
            "waypoints": [list(point) for point in sorted(waypoints)],
            "residual": {
                "missing_interface": program.missing_interface,
                "reason": program.reason,
                "evidence": list(program.evidence),
            },
            "target_writes": 0,
            "action_count": 0,
        }

    codes = {}
    actions = 0
    for (x, y), label in _selector_controls(_matrix(frame)):
        frame = ab.click(env, (y, x))
        actions += 1
        codes[label] = _source_bits(_matrix(frame))
    columns = tuple(codes[action] for action in program)
    writes = []
    for row_index, target_row in enumerate(targets):
        for column_index, (x, y) in enumerate(target_row):
            desired = columns[column_index][row_index]
            current = 1 if _matrix(frame)[y][x] == 5 else 0
            if current != desired:
                frame = ab.click(env, (y, x))
                actions += 1
                writes.append({
                    "row": row_index,
                    "column": column_index,
                    "value": desired,
                })
    submit = _submit(_matrix(frame))
    frame = ab.click(env, (submit[1], submit[0]))
    actions += 1
    progressed = int(frame.levels_completed) > start_level or str(frame.state).endswith("WIN")
    return {
        "status": "PROGRESSED" if progressed else "RESIDUAL",
        "waypoints": [list(point) for point in sorted(waypoints)],
        "on_route_waypoint": list(next(point for point in route_positions if point in waypoints)),
        "program": list(program),
        "codes": {label: list(code) for label, code in sorted(codes.items())},
        "columns": [list(column) for column in columns],
        "writes": writes,
        "target_writes": len(writes),
        "action_count": actions,
        "start_level": start_level,
        "end_level": int(frame.levels_completed),
        "end_state": str(frame.state),
        "progressed": progressed,
    }


def main():
    from arc3_public_g6_paired_route import enter_g6

    _, frame = enter_g6()
    machine, quotient, route_positions, route_transition_classes = diagnose_frame(frame)
    compiled = compile_capability(
        machine,
        route_positions[0],
        (
            "observation.visible-board@1",
            "control.navigation@1",
            "terminal.goal-cell@1",
        ),
        lineage=("arc.visible-transition-trace@1", "protected-future-compiler@1"),
    )
    if not isinstance(compiled, CompiledCapability):
        raise AssertionError(
            f"navigation_compilation_failed:{compiled.missing_interface}:{compiled.reason}"
        )
    historical_files = tuple(
        name
        for name in (
            "goal-phase-ingress-negative.json",
            "observable-trace-negative.json",
            "marker-poststate-negative.json",
            "marker-prestate-negative.json",
            "marker-boundary-delta-negative.json",
            "waypoint-suffix-negative.json",
            "port-two-step-equivalence.json",
        )
        if (OUT / name).exists()
    )
    result = {
        "parent": "6fd192fc89babbfdfcbc8bbbac891c846ce70070",
        "head": _git_head(),
        "status": "RESIDUAL",
        "classification": "RESIDUAL",
        "hypothesis": (
            "the coarsest control-congruent future quotient of the visible G6 navigation "
            "machine reveals the semantic compression needed by the six target columns"
        ),
        "boundary": {
            "actions": list(ACTIONS),
            "max_depth": machine.boundary.max_depth,
            "max_states": machine.boundary.max_states,
            "route": ROUTE,
        },
        "states": [
            {"id": f"{row},{col}", "cell": [row, col], "observation": observation}
            for (row, col), observation in machine.observations
        ],
        "transitions": [
            {
                "source": f"{transition.source[0]},{transition.source[1]}",
                "action": transition.action,
                "target": f"{transition.target[0]},{transition.target[1]}",
                "effect": transition.effect,
                "required_control": transition.required_control,
            }
            for transition in machine.transitions
        ],
        "classes": [
            [[row, col] for row, col in block]
            for block in quotient.classes
        ],
        "witnesses": [
            {
                "left": list(left),
                "right": list(right),
                "word": list(word),
            }
            for left, right, word in quotient.witnesses
        ],
        "congruence": quotient.congruent,
        "quotient_id": quotient.quotient_id,
        "route_positions": [list(cell) for cell in route_positions],
        "route_transition_classes": route_transition_classes,
        "route_transition_class_count": len(
            {
                (row["source_class"], row["action"], row["target_class"])
                for row in route_transition_classes
            }
        ),
        "result_summary": {
            "navigation_state_count": len(machine.states),
            "navigation_class_count": len(quotient.classes),
            "route_step_count": len(ROUTE),
            "route_transition_class_count": len(
                {
                    (row["source_class"], row["action"], row["target_class"])
                    for row in route_transition_classes
                }
            ),
        },
        "falsified": (
            "full control-congruent navigation-state future equivalence supplies the "
            "six target-column identities"
        ),
        "tested_projection_families": [
            "full navigation future equivalence",
            "goal-phase ingress control response",
            "stutter-invariant coarse source trace",
            "marker-aligned post-action coarse source state",
            "marker-aligned pre-action coarse source state",
            "marker-aligned coarse source boundary change mask",
            "same-control two-step port-role future",
        ],
        "compiled_navigation_capability": {
            "interface": compiled.interface_id,
            "capability_id": compiled.capability_id,
            "quotient_id": compiled.quotient_id,
            "program": list(compiled.program),
            "control_program": list(compiled.control_program),
            "preserves": list(compiled.preserves),
            "lineage": list(compiled.lineage),
        },
        "historical_evidence": [
            {
                "path": name,
                "sha256": sha256((OUT / name).read_bytes()).hexdigest(),
                "qualification": "historical_not_regenerated_by_this_run",
            }
            for name in historical_files
        ],
        "verification": [],
        "independent_replay_count": 0,
        "residual": {
            "missing_interface": "target.projection@1",
            "reason": (
                "the generic quotient compiler recovers an executable navigation program, "
                "but no qualified relation maps its protected transition semantics to the "
                "six target-panel columns"
            ),
        },
        "action_count": 0,
        "model_calls": 0,
        "source_inspection": False,
        "target_writes": 0,
        "claim_boundary": (
            "exact public tn36 G6 initial visible navigation geometry; full 7x7 legal-motion "
            "machine; depth-12 protected-future refinement; board-derived goal cell as the "
            "accepting oracle; no target-panel projection and no target writes"
        ),
    }
    validate_result(result)
    (OUT / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True), flush=True)
    print(f"ARC3_PUBLIC_G6_FUTURE_QUOTIENT={result['status']}", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()

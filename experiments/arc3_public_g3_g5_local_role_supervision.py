from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from math import gcd
import json
import os
from pathlib import Path
import subprocess

from arc3_public_g6_event_cell_relation import (
    canonical_patch_trace,
    component_relation_descriptors,
    extract_cell_patch,
)
from arc3_public_g6_glyph_role_decoder import _endpoint_family
from metalogic_arc3.protected_future import UnknownResidual, canonical_digest


INTERFACE_ID = "event.history-conditioned-local-relation@1"
SCHEMA = "arc3.g3-g5-local-role-supervision@1"
RELATION_LADDER = ("glyph", "glyph_motion", "glyph_motion_components")
ACTION_BUDGET = 180


def _bits(value) -> tuple[int, ...]:
    try:
        result = tuple(int(bit) for bit in value)
    except (TypeError, ValueError):
        raise ValueError("output_bits") from None
    if len(result) != 6 or any(bit not in (0, 1) for bit in result):
        raise ValueError("output_bits")
    return result


def _normalized_trace_cells(cells: Iterable[Sequence[int]]) -> tuple[tuple[int, int], ...]:
    cells = tuple(tuple(int(value) for value in cell) for cell in cells)
    if not cells or any(len(cell) != 2 for cell in cells):
        raise ValueError("trace_cells")
    origin_row, origin_column = cells[0]
    return tuple(
        (row - origin_row, column - origin_column)
        for row, column in cells
    )


def canonical_local_relation(
    trace_patches,
    *,
    trace_cells,
    component_relations=(),
) -> str:
    """Content identity for a palette- and translation-invariant local route event."""
    meaning = (
        INTERFACE_ID,
        canonical_patch_trace(trace_patches),
        _normalized_trace_cells(trace_cells),
        tuple(sorted(tuple(row) for row in component_relations)),
    )
    return canonical_digest(meaning)


def _primitive_motion(cells) -> tuple[int, int]:
    cells = tuple(tuple(int(value) for value in cell) for cell in cells)
    if not cells or any(len(cell) != 2 for cell in cells):
        raise ValueError("trace_cells")
    delta_row = cells[-1][0] - cells[0][0]
    delta_column = cells[-1][1] - cells[0][1]
    divisor = gcd(abs(delta_row), abs(delta_column))
    if divisor:
        delta_row //= divisor
        delta_column //= divisor
    return delta_row, delta_column


def _endpoint_components(component_relations):
    result = []
    for descriptor in component_relations:
        descriptor = tuple(descriptor)
        if len(descriptor) != 3 or descriptor[0] != "component":
            raise ValueError("component_relation")
        relations = tuple(tuple(row) for row in descriptor[2])
        if not relations:
            raise ValueError("component_relation")
        result.append((descriptor[0], tuple(descriptor[1]), (relations[0], relations[-1])))
    return tuple(sorted(result, key=canonical_digest))


def local_relation_ladder(trace_patches, *, trace_cells, component_relations):
    patches = tuple(trace_patches)
    if len(patches) < 2:
        raise ValueError("trace_patch_census")
    families = _endpoint_family(patches[0], patches[-1])
    motion = _primitive_motion(trace_cells)
    components = _endpoint_components(component_relations)
    meanings = {
        "glyph": ("local-route-glyph@1", families),
        "glyph_motion": ("local-route-glyph-motion@1", families, motion),
        "glyph_motion_components": (
            "local-route-glyph-motion-components@1",
            families,
            motion,
            components,
        ),
    }
    return {name: canonical_digest(meanings[name]) for name in RELATION_LADDER}


def _residual(reason: str, evidence=()) -> UnknownResidual:
    return UnknownResidual(INTERFACE_ID, reason, tuple(str(item) for item in evidence))


def fit_relation_codebook(training_slots):
    slots = tuple(training_slots)
    census = sorted(
        (int(row.get("level", -1)), int(row.get("slot_index", -1)))
        for row in slots
    )
    expected = [(level, slot) for level in (3, 4, 5) for slot in range(6)]
    if census != expected:
        return _residual("warranted_slot_census", (repr(census),))

    grouped = defaultdict(list)
    for row in slots:
        level = int(row["level"])
        slot = int(row["slot_index"])
        if row.get("terminal_consequence") not in {"PROGRESS", "WIN"}:
            return _residual("missing_terminal_warrant", (f"G{level}:slot{slot}",))
        raw_relation_id = row.get("relation_id")
        if not isinstance(raw_relation_id, str) or not raw_relation_id:
            return _residual("missing_local_relation", (f"G{level}:slot{slot}",))
        relation_id = raw_relation_id
        try:
            output = _bits(row.get("output"))
        except ValueError as error:
            return _residual("invalid_warranted_output", (f"G{level}:slot{slot}:{error}",))
        grouped[relation_id].append((level, slot, output))

    collisions = []
    for relation_id, rows in sorted(grouped.items()):
        if len({output for _, _, output in rows}) > 1:
            collisions.extend(
                f"{relation_id}:G{level}:slot{slot}:{''.join(map(str, output))}"
                for level, slot, output in rows
            )
    if collisions:
        return _residual("nonfunctional_local_relation", collisions)

    return {
        relation_id: {
            "output": list(rows[0][2]),
            "source_levels": sorted({level for level, _, _ in rows}),
            "source_slots": [f"G{level}:slot{slot}" for level, slot, _ in rows],
        }
        for relation_id, rows in sorted(grouped.items())
    }


def _unknown_candidate(residual: UnknownResidual):
    return {
        "status": "UNKNOWN",
        "residual": {
            "missing_interface": residual.missing_interface,
            "reason": residual.reason,
            "evidence": list(residual.evidence),
        },
        "target_writes": 0,
        "submit_clicks": 0,
        "action_count": 0,
    }


def compile_supervised_candidate(
    training_slots,
    g6_relations,
    *,
    executor: Callable[[tuple[tuple[int, ...], ...]], Mapping[str, object]],
):
    codebook = fit_relation_codebook(training_slots)
    if isinstance(codebook, UnknownResidual):
        return _unknown_candidate(codebook)
    relations = tuple(str(relation) for relation in g6_relations)
    if len(relations) != 6:
        return _unknown_candidate(_residual("g6_relation_census", (str(len(relations)),)))
    missing = tuple(sorted({relation for relation in relations if relation not in codebook}))
    if missing:
        return _unknown_candidate(_residual("uncovered_g6_relation", missing))
    columns = tuple(tuple(codebook[relation]["output"]) for relation in relations)
    execution = dict(executor(columns))
    return {
        "status": "CANDIDATE",
        "codebook": codebook,
        "g6_relations": list(relations),
        "columns": [list(column) for column in columns],
        **execution,
    }


def _collect_training_slots(training, observations):
    levels = tuple(training.get("levels", ()))
    observed_levels = tuple(observations.get("levels", ()))
    if [row.get("level") for row in levels] != [3, 4, 5]:
        return _residual("warranted_slot_census", ("training_levels",))
    if [row.get("level") for row in observed_levels] != [3, 4, 5]:
        return _residual("warranted_slot_census", ("observed_levels",))
    slots = []
    for trained, observed in zip(levels, observed_levels):
        level = int(trained["level"])
        consequence = trained.get("terminal_warrant", {}).get("consequence")
        examples = tuple(trained.get("examples", ()))
        events = tuple(observed.get("slots", ()))
        if consequence not in {"PROGRESS", "WIN"} or len(examples) != 6 or len(events) != 6:
            return _residual("warranted_slot_census", (f"G{level}",))
        if trained.get("path") != observed.get("path"):
            return _residual("sequential_path_drift", (f"G{level}",))
        for index, (example, event) in enumerate(zip(examples, events)):
            controls = tuple(example.get("action", {}).get("controls", ()))
            if (
                example.get("slot_index") != index
                or event.get("slot_index") != index
                or controls != (event.get("control"),)
            ):
                return _residual("slot_alignment_drift", (f"G{level}:slot{index}",))
            slots.append(
                {
                    "level": level,
                    "slot_index": index,
                    "terminal_consequence": consequence,
                    "relations": dict(event.get("relations", {})),
                    "output": list(example.get("output", ())),
                }
            )
    if len(slots) != 18:
        return _residual("warranted_slot_census", (str(len(slots)),))
    return slots


def _select_transport_lens(training_slots, g6_events):
    attempts = []
    for lens in RELATION_LADDER:
        fitted = fit_relation_codebook(
            {**slot, "relation_id": slot.get("relations", {}).get(lens)}
            for slot in training_slots
        )
        if isinstance(fitted, UnknownResidual):
            attempts.append((lens, fitted.reason, tuple(fitted.evidence)))
            continue
        relations = tuple(event.get("relations", {}).get(lens) for event in g6_events)
        missing = tuple(sorted({str(item) for item in relations if item not in fitted}))
        if missing:
            attempts.append((lens, "uncovered_g6_relation", missing))
            continue
        return lens, fitted, tuple(str(item) for item in relations), attempts
    evidence = tuple(
        f"{lens}:{reason}:{'|'.join(items)}"
        for lens, reason, items in attempts
    )
    return _residual("no_functional_transport_lens", evidence)


def compile_observed_candidate(*, training, observations, g6_observation, executor):
    slots = _collect_training_slots(training, observations)
    if isinstance(slots, UnknownResidual):
        candidate = _unknown_candidate(slots)
        candidate["action_count"] = int(observations.get("action_count", 0)) + int(
            g6_observation.get("action_count", 0)
        )
        return candidate
    g6_events = tuple(g6_observation.get("events", ()))
    if len(g6_events) != 6:
        candidate = _unknown_candidate(_residual("g6_relation_census", (str(len(g6_events)),)))
        candidate["action_count"] = int(observations.get("action_count", 0)) + int(
            g6_observation.get("action_count", 0)
        )
        return candidate
    selected = _select_transport_lens(slots, g6_events)
    observation_actions = (
        sum(int(row.get("action_count", 0)) for row in training.get("levels", ()))
        + int(observations.get("action_count", 0))
        + int(g6_observation.get("action_count", 0))
    )
    if isinstance(selected, UnknownResidual):
        candidate = _unknown_candidate(selected)
        candidate["action_count"] = observation_actions
        candidate["training_slots"] = slots
        candidate["g6_events"] = list(g6_events)
        return candidate
    lens, codebook, relations, attempts = selected
    columns = tuple(tuple(codebook[relation]["output"]) for relation in relations)
    execution = dict(executor(columns))
    execution["action_count"] = observation_actions + int(execution.get("action_count", 0))
    candidate = {
        "status": "CANDIDATE",
        "selected_lens": lens,
        "prior_attempts": [list(row) for row in attempts],
        "codebook": codebook,
        "g6_relations": list(relations),
        "columns": [list(column) for column in columns],
        **execution,
    }
    candidate["semantic_id"] = canonical_digest(
        ("g3-g5-local-role-supervision-candidate@1", lens, codebook, relations, columns)
    )
    return candidate


def _advance_cell(cell, control):
    delta = {"U": (-1, 0), "D": (1, 0), "L": (0, -1), "R": (0, 1)}.get(control, (0, 0))
    return cell[0] + delta[0], cell[1] + delta[1]


def _observe_level(level, enter_level):
    import arc3_public_all_blue_to_gray_g2 as ab
    from metalogic_arc3.semantic_path import (
        SemanticPathSession,
        _bbox,
        _complement_translation,
        _find_board,
        _matrix,
        _multicolor_endpoint_transform,
        _scale_normalized_translation,
    )

    env, frame = enter_level()
    initial = _matrix(frame)
    plan = SemanticPathSession.start(frame).plan
    board_top, board_left = _find_board(initial)
    if level == 3:
        mover, _, _, _ = _complement_translation(initial, board_top, board_left)
    elif level == 4:
        mover, _, _, _ = _scale_normalized_translation(initial, board_top, board_left)
    elif level == 5:
        mover, _ = _multicolor_endpoint_transform(initial, board_top, board_left)
    else:
        raise ValueError("training_level")
    mover_top, mover_left, _, _ = _bbox(mover)
    current = ((mover_top - board_top) // 4, (mover_left - board_left) // 4)
    controls = {
        label: point for point, label in zip(plan.probes, plan.probe_directions)
    }
    if not set(plan.path).issubset(controls):
        raise ValueError(f"missing_path_control:G{level}")
    events = []
    for slot_index, control in enumerate(plan.path):
        before = _matrix(frame)
        destination = _advance_cell(current, control)
        if any(value < 0 or value >= 7 for value in destination):
            raise ValueError(f"route_bounds:G{level}:slot{slot_index}")
        x, y = controls[control]
        frame = ab.click(env, (y, x))
        after = _matrix(frame)
        patches = (
            extract_cell_patch(
                before,
                board_top=board_top,
                board_left=board_left,
                cell=current,
                cell_size=4,
            ),
            extract_cell_patch(
                after,
                board_top=board_top,
                board_left=board_left,
                cell=destination,
                cell_size=4,
            ),
        )
        components = component_relation_descriptors(
            initial,
            board_top=board_top,
            board_left=board_left,
            board_rows=7,
            board_columns=7,
            cell_size=4,
            trace_cells=(current, destination),
        )
        events.append(
            {
                "slot_index": slot_index,
                "control": control,
                "cells": [list(current), list(destination)],
                "trace_patches": [[list(row) for row in patch] for patch in patches],
                "relations": local_relation_ladder(
                    patches,
                    trace_cells=(current, destination),
                    component_relations=components,
                ),
            }
        )
        current = destination
    return {"level": level, "path": plan.path, "slots": events, "action_count": 6}


def _read_training():
    from arc3_public_consequence_training import replay_training_once

    return replay_training_once(warrant_ref="g3-g5-local-role-supervision@1")


def _read_observations():
    import arc3_public_panel_correspondence_g3 as g3
    from arc3_public_g4_scale_normalized_docking import enter_g4
    from arc3_public_g5_control_separator import enter_g5

    levels = (
        _observe_level(3, g3.enter_level3),
        _observe_level(4, enter_g4),
        _observe_level(5, enter_g5),
    )
    return {"levels": list(levels), "action_count": sum(row["action_count"] for row in levels)}


def _read_g6_observation():
    from arc3_public_g6_event_cell_relation import run_replay

    replay = run_replay()
    events = []
    for event in replay["events"]:
        components = event["signature_inputs"]["component_relations"]
        events.append(
            {
                "route_step": event["route_step"],
                "marker_rank": event["marker_rank"],
                "relations": local_relation_ladder(
                    event["trace_patches"],
                    trace_cells=event["cells"],
                    component_relations=components,
                ),
            }
        )
    events.sort(key=lambda row: row["marker_rank"])
    return {"events": events, "action_count": int(replay["action_count"])}


def _execute_projection(columns):
    from arc3_public_g6_glyph_role_decoder import _execute_projection as execute

    return execute(columns)


def run_candidate(*, training_reader=None, observation_reader=None, g6_reader=None, executor=None):
    training = (training_reader or _read_training)()
    observations = (observation_reader or _read_observations)()
    g6_observation = (g6_reader or _read_g6_observation)()
    return compile_observed_candidate(
        training=training,
        observations=observations,
        g6_observation=g6_observation,
        executor=executor or _execute_projection,
    )


def _source_head():
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    return subprocess.check_output(
        ("git", "rev-parse", "HEAD"),
        cwd=Path(__file__).resolve().parents[1],
        text=True,
    ).strip()


def _candidate_identity(candidate):
    return (
        candidate.get("semantic_id"),
        candidate.get("terminal"),
        candidate.get("progressed"),
        candidate.get("target_writes"),
        candidate.get("submit_clicks"),
        candidate.get("action_count"),
    )


def _validate_executed_candidate(candidate):
    if candidate.get("status") != "CANDIDATE" or not candidate.get("semantic_id"):
        raise ValueError("candidate_boundary")
    try:
        columns = tuple(_bits(column) for column in candidate.get("columns", ()))
        actions = int(candidate.get("action_count", -1))
        writes = int(candidate.get("target_writes", -1))
    except (TypeError, ValueError):
        raise ValueError("candidate_boundary") from None
    if (
        len(columns) != 6
        or not isinstance(candidate.get("progressed"), bool)
        or candidate.get("submit_clicks") != 1
        or not 0 <= writes <= 36
        or not 1 <= actions <= ACTION_BUDGET
    ):
        raise ValueError("candidate_boundary")
    return candidate


def build_result(*, head=None, runner=None):
    head = head or _source_head()
    runner = runner or run_candidate
    base = {
        "schema": SCHEMA,
        "head": head,
        "model_calls": 0,
        "source_inspection": False,
        "action_budget_per_candidate": ACTION_BUDGET,
        "claim_boundary": (
            "exact public tn36; 18 terminal-warranted G3-G5 slots; sequential visible "
            "local route relations; ordered structural refinement ladder; one G6 submit "
            "only after a total functional join; two exact replays only on progress"
        ),
    }
    try:
        candidate = runner()
    except Exception as error:
        result = {
            **base,
            "status": "RESIDUAL",
            "classification": "NON_EVIDENCE",
            "candidate": None,
            "verification": [],
            "target_writes": 0,
            "residual": {"reason": "candidate_exception", "error": f"{type(error).__name__}:{error}"},
        }
        validate_result(result, executing_head=head)
        return result
    if candidate.get("status") == "UNKNOWN":
        result = {
            **base,
            "status": "RESIDUAL",
            "classification": "EXACT_RESIDUAL",
            "candidate": candidate,
            "verification": [],
            "target_writes": 0,
            "residual": candidate.get("residual", {"reason": "unknown_local_relation"}),
        }
        validate_result(result, executing_head=head)
        return result
    if not candidate.get("progressed"):
        result = {
            **base,
            "status": "REJECTED",
            "classification": "WARRANTED_NEGATIVE",
            "candidate": candidate,
            "verification": [],
            "target_writes": int(candidate.get("target_writes", 0)),
        }
        validate_result(result, executing_head=head)
        return result
    verification = []
    try:
        for _ in range(2):
            verification.append(runner())
    except Exception as error:
        result = {
            **base,
            "status": "RESIDUAL",
            "classification": "NON_EVIDENCE",
            "candidate": candidate,
            "verification": verification,
            "target_writes": int(candidate.get("target_writes", 0)),
            "residual": {"reason": "verification_exception", "error": f"{type(error).__name__}:{error}"},
        }
        validate_result(result, executing_head=head)
        return result
    if any(
        row.get("status") != "CANDIDATE"
        or not row.get("progressed")
        or _candidate_identity(row) != _candidate_identity(candidate)
        for row in verification
    ):
        result = {
            **base,
            "status": "RESIDUAL",
            "classification": "NON_EVIDENCE",
            "candidate": candidate,
            "verification": verification,
            "target_writes": int(candidate.get("target_writes", 0)),
            "residual": {"reason": "verification_identity_drift"},
        }
        validate_result(result, executing_head=head)
        return result
    result = {
        **base,
        "status": "PROMOTED",
        "classification": "WARRANTED_POSITIVE",
        "candidate": candidate,
        "verification": verification,
        "target_writes": int(candidate.get("target_writes", 0)),
    }
    validate_result(result, executing_head=head)
    return result


def validate_result(result, *, executing_head):
    if result.get("schema") != SCHEMA:
        raise ValueError("result_schema")
    if result.get("head") != executing_head:
        raise ValueError("stale_evidence_head")
    if (
        result.get("model_calls") != 0
        or result.get("source_inspection") is not False
        or result.get("action_budget_per_candidate") != ACTION_BUDGET
    ):
        raise ValueError("scientific_boundary")
    status = result.get("status")
    candidate = result.get("candidate")
    if candidate is not None and int(candidate.get("action_count", -1)) > ACTION_BUDGET:
        raise ValueError("action_budget")
    if status == "RESIDUAL":
        if result.get("classification") not in {"EXACT_RESIDUAL", "NON_EVIDENCE"}:
            raise ValueError("residual_classification")
        if not result.get("residual", {}).get("reason"):
            raise ValueError("residual_reason")
        if result.get("classification") == "EXACT_RESIDUAL":
            if not candidate or candidate.get("status") != "UNKNOWN":
                raise ValueError("exact_residual_candidate")
            if candidate.get("target_writes") != 0 or candidate.get("submit_clicks") != 0:
                raise ValueError("unknown_side_effect")
    elif status == "REJECTED":
        if result.get("classification") != "WARRANTED_NEGATIVE" or result.get("verification"):
            raise ValueError("negative_boundary")
        if not candidate or candidate.get("status") != "CANDIDATE" or candidate.get("progressed"):
            raise ValueError("negative_candidate")
        _validate_executed_candidate(candidate)
    elif status == "PROMOTED":
        if result.get("classification") != "WARRANTED_POSITIVE" or len(result.get("verification", ())) != 2:
            raise ValueError("positive_boundary")
        if not candidate or not candidate.get("progressed"):
            raise ValueError("positive_candidate")
        _validate_executed_candidate(candidate)
        for replay in result.get("verification", ()):
            _validate_executed_candidate(replay)
    else:
        raise ValueError("result_status")
    return result


def main():
    result = build_result()
    out = Path(
        os.environ.get(
            "OUTDIR",
            "evidence/arc3-public-g3-g5-local-role-supervision",
        )
    ).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"ARC3_PUBLIC_G3_G5_LOCAL_ROLE_SUPERVISION={result['status']}")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

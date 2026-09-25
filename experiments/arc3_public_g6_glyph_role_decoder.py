from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
import json
import os
from pathlib import Path
import subprocess

from metalogic_arc3.protected_future import UnknownResidual, canonical_digest


ROLE_ORDER = (
    "endpoint.depart",
    "plain.before",
    "checker.enter",
    "checker.exit",
    "plain.after",
    "endpoint.arrive",
)


def canonical_glyph_family(cells):
    cells = {tuple(cell) for cell in cells}
    if not cells:
        return ("empty",)
    if any(len(cell) != 2 for cell in cells):
        raise ValueError("glyph_cell")
    top = min(row for row, _ in cells)
    left = min(column for _, column in cells)
    normalized = {
        (row - top, column - left) for row, column in cells
    }
    height = max(row for row, _ in normalized) + 1
    width = max(column for _, column in normalized) + 1
    if width == 1 and normalized == {(row, 0) for row in range(height)}:
        return ("line", "vertical")
    if height == 1 and normalized == {(0, column) for column in range(width)}:
        return ("line", "horizontal")
    for parity in (0, 1):
        checker = {
            (row, column)
            for row in range(height)
            for column in range(width)
            if (row + column) % 2 == parity
        }
        if height >= 2 and width >= 2 and normalized == checker:
            return ("checker",)
    if len(normalized) == height * width:
        if height == width:
            return ("solid", "square")
        return ("solid", "vertical" if height > width else "horizontal")
    return ("shape", height, width, tuple(sorted(normalized)))


def _grid(value: Sequence[Sequence[object]]) -> tuple[tuple[object, ...], ...]:
    result = tuple(tuple(row) for row in value)
    if not result or not result[0] or any(len(row) != len(result[0]) for row in result):
        raise ValueError("event_patch_grid")
    return result


def _endpoint_family(source, destination):
    source = _grid(source)
    destination = _grid(destination)
    if (len(source), len(source[0])) != (len(destination), len(destination[0])):
        raise ValueError("event_patch_shape")
    values = [value for patch in (source, destination) for row in patch for value in row]
    counts = Counter(values)
    background = min(counts, key=lambda value: (-counts[value], repr(value)))

    def foreground(patch):
        return {
            (row, column)
            for row, line in enumerate(patch)
            for column, value in enumerate(line)
            if value != background
        }

    source_cells = foreground(source)
    destination_cells = foreground(destination)
    return (
        canonical_glyph_family(source_cells),
        canonical_glyph_family(destination_cells),
    )


def event_role_records(events):
    events = tuple(events)
    if len(events) != len(ROLE_ORDER):
        raise ValueError("event_role_census")
    if set(row.get("marker_rank") for row in events) != set(range(6)):
        raise ValueError("event_marker_census")
    expected_families = (
        (("line", "vertical"), ("empty",)),
        (("empty",), ("empty",)),
        (("empty",), ("checker",)),
        (("checker",), ("empty",)),
        (("empty",), ("empty",)),
        (("empty",), ("line", "vertical")),
    )
    records = []
    for event, role, expected in zip(events, ROLE_ORDER, expected_families):
        patches = tuple(event.get("trace_patches", ()))
        controls = str(event.get("controls", ""))
        if len(patches) != 3 or len(controls) != 2 or any(control not in "UDLR" for control in controls):
            raise ValueError("event_role_census")
        families = _endpoint_family(patches[0], patches[2])
        if families != expected:
            raise ValueError("event_role_census")
        records.append(
            {
                "role": role,
                "families": [list(family) for family in families],
                "controls": controls,
                "marker_rank": int(event["marker_rank"]),
            }
        )
    return records


def _bits(value) -> tuple[int, ...]:
    try:
        result = tuple(int(bit) for bit in value)
    except (TypeError, ValueError):
        raise ValueError("code_bits") from None
    if len(result) != 6 or any(bit not in (0, 1) for bit in result):
        raise ValueError("code_bits")
    return result


def compile_role_codebook(solved_codes, g6_codes):
    assignments = (
        ("endpoint.depart", "g6", "R"),
        ("plain.before", "solved", "I"),
        ("checker.enter", "solved", "X"),
        ("checker.exit", "solved", "T"),
        ("plain.after", "solved", "S"),
        ("endpoint.arrive", "g6", "L"),
    )
    codebook = {}
    for role, source, label in assignments:
        try:
            if source == "g6":
                output = _bits(g6_codes[label])
                levels = (6,)
            else:
                row = solved_codes[label]
                output = _bits(row["output"])
                levels = tuple(int(level) for level in row["levels"])
                if not levels:
                    raise ValueError("missing_warrant_level")
        except (KeyError, TypeError, ValueError) as error:
            return UnknownResidual(
                "event.local-trace-role@1",
                "missing_or_conflicting_role_supervision",
                (f"{role}:{label}:{error}",),
            )
        codebook[role] = {
            "label": label,
            "output": list(output),
            "source": source,
            "levels": list(levels),
        }
    return codebook


def solved_codes_from_training(training):
    """Extract only terminal-warranted, unambiguous control codes."""
    levels = tuple(training.get("levels", ())) if isinstance(training, Mapping) else ()
    if [row.get("level") for row in levels] != [3, 4, 5]:
        return UnknownResidual(
            "event.local-trace-role@1",
            "missing_warranted_training_levels",
            (repr([row.get("level") for row in levels]),),
        )
    observations = {}
    sources = {}
    for level in levels:
        consequence = level.get("terminal_warrant", {}).get("consequence")
        if consequence not in {"PROGRESS", "WIN"}:
            return UnknownResidual(
                "event.local-trace-role@1",
                "missing_terminal_warrant",
                (f"G{level.get('level')}:{consequence}",),
            )
        for example in level.get("examples", ()):
            controls = tuple(example.get("action", {}).get("controls", ()))
            if len(controls) != 1 or not isinstance(controls[0], str):
                return UnknownResidual(
                    "event.local-trace-role@1",
                    "ambiguous_warranted_control",
                    (f"G{level['level']}:{controls!r}",),
                )
            label = controls[0]
            try:
                output = _bits(example.get("output"))
            except ValueError as error:
                return UnknownResidual(
                    "event.local-trace-role@1",
                    "invalid_warranted_control_code",
                    (f"G{level['level']}:{label}:{error}",),
                )
            observations.setdefault(label, set()).add(output)
            sources.setdefault(label, set()).add(int(level["level"]))
    conflicts = {
        label: tuple(sorted(outputs))
        for label, outputs in observations.items()
        if len(outputs) != 1
    }
    if conflicts:
        return UnknownResidual(
            "event.local-trace-role@1",
            "conflicting_warranted_control_code",
            tuple(f"{label}:{outputs!r}" for label, outputs in sorted(conflicts.items())),
        )
    return {
        label: {
            "output": list(next(iter(outputs))),
            "levels": sorted(sources[label]),
        }
        for label, outputs in sorted(observations.items())
    }


def _unknown_candidate(residual):
    return {
        "status": "UNKNOWN",
        "residual": {
            "missing_interface": residual.missing_interface,
            "reason": residual.reason,
            "evidence": list(residual.evidence),
        },
        "target_writes": 0,
        "submit_clicks": 0,
        "action_count": 16,
    }


def compile_observed_candidate(*, training, events, g6_codes, executor):
    solved_codes = solved_codes_from_training(training)
    if isinstance(solved_codes, UnknownResidual):
        return _unknown_candidate(solved_codes)
    try:
        roles = event_role_records(events)
    except ValueError as error:
        return _unknown_candidate(
            UnknownResidual(
                "event.local-trace-role@1",
                "unrecognized_event_role_census",
                (str(error),),
            )
        )
    codebook = compile_role_codebook(solved_codes, g6_codes)
    if isinstance(codebook, UnknownResidual):
        return _unknown_candidate(codebook)
    columns = project_spatial_columns(roles, codebook)
    if isinstance(columns, UnknownResidual):
        return _unknown_candidate(columns)
    execution = executor(columns)
    row = {
        "status": "CANDIDATE",
        "roles": roles,
        "codebook": codebook,
        "columns": [list(column) for column in columns],
        **execution,
    }
    row["semantic_id"] = candidate_semantic_id(row)
    _validate_candidate(row)
    return row


def _read_training():
    from arc3_public_consequence_training import replay_training_once

    return replay_training_once(warrant_ref="g6-glyph-role-decoder@1")


def _read_events():
    from arc3_public_g6_event_cell_relation import run_replay

    return run_replay()


def _read_g6_codes():
    from arc3_public_g6_consequence_projection import enter_public_g6
    from metalogic_arc3.semantic_path import _matrix, _source_bits

    session, frame, boundary = enter_public_g6()
    codes = {}
    for label in ("R", "L"):
        if label not in boundary.control_points:
            raise ValueError(f"missing_g6_control:{label}")
        frame = session.click(*boundary.control_points[label])
        codes[label] = list(_bits(_source_bits(_matrix(frame))))
    return {"codes": codes, "action_count": 2}


def _execute_projection(columns):
    from arc3_public_g6_consequence_projection import enter_public_g6

    session, start_frame, boundary = enter_public_g6()
    if len(columns) != len(boundary.target_cells):
        raise ValueError("target_column_count")
    frame = start_frame
    writes = []
    for column_index, (column, target_column) in enumerate(
        zip(columns, boundary.target_cells)
    ):
        if len(column) != len(target_column):
            raise ValueError("target_row_count")
        for row_index, (bit, (x, y)) in enumerate(zip(column, target_column)):
            if int(bit) != boundary.initial_columns[column_index][row_index]:
                frame = session.click(x, y)
                writes.append(
                    {"row": row_index, "column": column_index, "value": int(bit)}
                )
    terminal = session.click(*boundary.submit)
    start_level = int(getattr(start_frame, "levels_completed"))
    terminal_level = int(getattr(terminal, "levels_completed"))
    terminal_state = str(getattr(terminal, "state"))
    return {
        "progressed": terminal_level > start_level or terminal_state.endswith("WIN"),
        "terminal": [terminal_level, terminal_state],
        "target_writes": len(writes),
        "writes": writes,
        "submit_clicks": 1,
        "action_count": len(writes) + 1,
    }


def run_candidate(
    *,
    training_reader=None,
    event_reader=None,
    code_reader=None,
    executor=None,
):
    training_reader = _read_training if training_reader is None else training_reader
    event_reader = _read_events if event_reader is None else event_reader
    code_reader = _read_g6_codes if code_reader is None else code_reader
    executor = _execute_projection if executor is None else executor
    training = training_reader()
    event_observation = event_reader()
    code_observation = code_reader()
    observation_actions = int(event_observation.get("action_count", -1)) + int(
        code_observation.get("action_count", -1)
    )
    if observation_actions != 14:
        return _unknown_candidate(
            UnknownResidual(
                "event.local-trace-role@1",
                "observation_action_boundary_drift",
                (str(observation_actions),),
            )
        )

    def accounted_executor(columns):
        execution = dict(executor(columns))
        execution["action_count"] = int(execution.get("action_count", -1)) + observation_actions
        return execution

    return compile_observed_candidate(
        training=training,
        events=event_observation.get("events", ()),
        g6_codes=code_observation.get("codes", {}),
        executor=accounted_executor,
    )


def project_spatial_columns(records, codebook):
    if isinstance(codebook, UnknownResidual):
        return codebook
    records = tuple(records)
    if [row.get("role") for row in records] != list(ROLE_ORDER):
        raise ValueError("event_role_order")
    spatial = sorted(records, key=lambda row: row["marker_rank"])
    if [row["marker_rank"] for row in spatial] != list(range(6)):
        raise ValueError("event_marker_census")
    try:
        return tuple(_bits(codebook[row["role"]]["output"]) for row in spatial)
    except KeyError as error:
        return UnknownResidual(
            "event.local-trace-role@1",
            "unseen_event_role",
            (str(error),),
        )


def candidate_semantic_id(row):
    return canonical_digest(
        (
            "g6-glyph-role-candidate@1",
            row.get("roles"),
            row.get("codebook"),
            row.get("columns"),
        )
    )


def _candidate_replay_id(row):
    return canonical_digest(
        (
            "g6-glyph-role-replay@1",
            row.get("semantic_id"),
            row.get("terminal"),
            row.get("progressed"),
            row.get("target_writes"),
            row.get("writes", ()),
            row.get("submit_clicks"),
            row.get("action_count"),
        )
    )


def _validate_candidate(row):
    if row.get("status") != "CANDIDATE":
        raise ValueError("candidate_status")
    roles = tuple(row.get("roles", ()))
    if [item.get("role") for item in roles] != list(ROLE_ORDER):
        raise ValueError("candidate_roles")
    codebook = row.get("codebook", {})
    if set(codebook) != set(ROLE_ORDER):
        raise ValueError("candidate_codebook")
    expected = project_spatial_columns(roles, codebook)
    columns = tuple(_bits(column) for column in row.get("columns", ()))
    if isinstance(expected, UnknownResidual) or columns != expected:
        raise ValueError("candidate_columns")
    if (
        not isinstance(row.get("progressed"), bool)
        or row.get("submit_clicks") != 1
        or not 0 <= int(row.get("target_writes", -1)) <= 36
        or not 17 <= int(row.get("action_count", -1)) <= 50
    ):
        raise ValueError("candidate_boundary")
    if row.get("semantic_id") != candidate_semantic_id(row):
        raise ValueError("candidate_semantic_id")


def _source_head():
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    return subprocess.check_output(
        ("git", "rev-parse", "HEAD"),
        cwd=Path(__file__).resolve().parents[1],
        text=True,
    ).strip()


def build_result(*, head=None, runner=None):
    head = _source_head() if head is None else head
    runner = run_candidate if runner is None else runner
    base = {
        "schema": "arc3.g6-glyph-role-decoder@1",
        "head": head,
        "model_calls": 0,
        "source_inspection": False,
        "action_budget_per_candidate": 50,
        "claim_boundary": (
            "exact public tn36; solved G3-G5 warranted control codes; "
            "G6 palette/translation/scale-normalized nested glyph roles; "
            "one compiled candidate; two exact replays only on progress"
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
        if candidate.get("target_writes") != 0 or candidate.get("submit_clicks") != 0:
            raise ValueError("unknown_side_effect")
        result = {
            **base,
            "status": "RESIDUAL",
            "classification": "EXACT_RESIDUAL",
            "candidate": candidate,
            "verification": [],
            "target_writes": 0,
            "residual": candidate.get("residual", {"reason": "unknown_role_mapping"}),
        }
        validate_result(result, executing_head=head)
        return result
    _validate_candidate(candidate)
    if not candidate["progressed"]:
        result = {
            **base,
            "status": "REJECTED",
            "classification": "WARRANTED_NEGATIVE",
            "candidate": candidate,
            "verification": [],
            "target_writes": candidate["target_writes"],
        }
        validate_result(result, executing_head=head)
        return result
    verification = []
    try:
        for _ in range(2):
            replay = runner()
            _validate_candidate(replay)
            verification.append(replay)
    except Exception as error:
        result = {
            **base,
            "status": "RESIDUAL",
            "classification": "NON_EVIDENCE",
            "candidate": candidate,
            "verification": verification,
            "target_writes": candidate["target_writes"],
            "residual": {"reason": "verification_exception", "error": f"{type(error).__name__}:{error}"},
        }
        validate_result(result, executing_head=head)
        return result
    replay_id = _candidate_replay_id(candidate)
    if any(
        not row["progressed"] or _candidate_replay_id(row) != replay_id
        for row in verification
    ):
        result = {
            **base,
            "status": "RESIDUAL",
            "classification": "NON_EVIDENCE",
            "candidate": candidate,
            "verification": verification,
            "target_writes": candidate["target_writes"],
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
        "target_writes": candidate["target_writes"],
    }
    validate_result(result, executing_head=head)
    return result


def validate_result(result, *, executing_head):
    if result.get("schema") != "arc3.g6-glyph-role-decoder@1":
        raise ValueError("result_schema")
    if result.get("head") != executing_head:
        raise ValueError("stale_evidence_head")
    if (
        result.get("model_calls") != 0
        or result.get("source_inspection") is not False
        or result.get("action_budget_per_candidate") != 50
    ):
        raise ValueError("scientific_boundary")
    status = result.get("status")
    candidate = result.get("candidate")
    if status == "RESIDUAL":
        if result.get("classification") not in {"EXACT_RESIDUAL", "NON_EVIDENCE"}:
            raise ValueError("residual_classification")
        if not result.get("residual", {}).get("reason"):
            raise ValueError("residual_reason")
        if candidate and candidate.get("status") == "CANDIDATE":
            _validate_candidate(candidate)
        elif candidate and (
            candidate.get("status") != "UNKNOWN"
            or candidate.get("target_writes") != 0
            or candidate.get("submit_clicks") != 0
        ):
            raise ValueError("unknown_evidence")
        for row in result.get("verification", ()):
            _validate_candidate(row)
        return result
    if candidate is None:
        raise ValueError("missing_candidate")
    _validate_candidate(candidate)
    if result.get("target_writes") != candidate.get("target_writes"):
        raise ValueError("target_write_accounting")
    if status == "REJECTED":
        if (
            result.get("classification") != "WARRANTED_NEGATIVE"
            or candidate.get("progressed") is not False
            or result.get("verification") != []
        ):
            raise ValueError("negative_evidence")
        return result
    if status != "PROMOTED" or result.get("classification") != "WARRANTED_POSITIVE":
        raise ValueError("result_status")
    verification = tuple(result.get("verification", ()))
    if len(verification) != 2:
        raise ValueError("verification_count")
    for row in verification:
        _validate_candidate(row)
        if (
            not row.get("progressed")
            or _candidate_replay_id(row) != _candidate_replay_id(candidate)
        ):
            raise ValueError("verification_identity")
    return result


def main():
    result = build_result()
    out = Path(
        os.environ.get(
            "OUTDIR",
            "evidence/arc3-public-g6-glyph-role-decoder",
        )
    ).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(f"ARC3_PUBLIC_G6_GLYPH_ROLE_DECODER={result['status']}")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

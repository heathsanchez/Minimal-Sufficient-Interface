from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import json
import os
from pathlib import Path
import subprocess

from metalogic_arc3.protected_future import canonical_digest
from metalogic_arc3.semantic_path import _find_board, _matrix, _source_bits


SCHEMA = "arc3.g6-marker-commit-projection@1"
ROUTE = "RRRRUULLUUUL"
EVENT_STEPS = (2, 4, 6, 8, 10, 12)
ACTION_BUDGET = 50
VERIFICATION_REPLAYS = 2


def _bits(value: Sequence[int]) -> tuple[int, ...]:
    result = tuple(int(bit) for bit in value)
    if len(result) != 6 or any(bit not in (0, 1) for bit in result):
        raise ValueError("source_code")
    return result


def projection_from_trace(
    route: str,
    steps: Iterable[Mapping[str, object]],
    *,
    selector: str,
) -> tuple[tuple[tuple[int, ...], ...], list[dict[str, object]]]:
    """Project one source code from each visible marker-commit event."""
    if route != ROUTE or selector not in {"commit", "first"}:
        raise ValueError("projection_boundary")
    steps = tuple(steps)
    if len(steps) != len(route):
        raise ValueError("route_step_census")
    for index, (row, control) in enumerate(zip(steps, route), start=1):
        if row.get("step") != index or row.get("control") != control:
            raise ValueError("route_step_evidence")
        _bits(row.get("source_code", ()))
    observed_event_steps = tuple(
        int(row["step"])
        for row in steps
        if row.get("marker_position") is not None
    )
    if observed_event_steps != EVENT_STEPS:
        raise ValueError("marker_event_census")
    marker_positions = tuple(
        tuple(steps[step - 1]["marker_position"])
        for step in EVENT_STEPS
    )
    if (
        any(len(position) != 2 for position in marker_positions)
        or len(set(marker_positions)) != len(EVENT_STEPS)
    ):
        raise ValueError("marker_spatial_alignment")
    rank = {
        position: index for index, position in enumerate(sorted(marker_positions))
    }
    chronological = []
    previous = 0
    for step, position in zip(EVENT_STEPS, marker_positions):
        selected_step = step if selector == "commit" else step - 1
        selected = steps[selected_step - 1]
        chronological.append(
            {
                "route_step": step,
                "controls": route[previous:step],
                "marker_position": list(position),
                "marker_rank": rank[position],
                "selected_step": selected_step,
                "selected_control": selected["control"],
                "source_code": list(_bits(selected["source_code"])),
            }
        )
        previous = step
    events = sorted(chronological, key=lambda row: row["marker_rank"])
    columns = tuple(_bits(row["source_code"]) for row in events)
    return columns, events


def candidate_semantic_id(row: Mapping[str, object]) -> str:
    return canonical_digest(
        (
            "g6-marker-commit-candidate@1",
            row.get("selector"),
            row.get("columns"),
            row.get("events"),
        )
    )


def _candidate_identity(row: Mapping[str, object]) -> str:
    return canonical_digest(
        (
            "g6-marker-commit-replay@1",
            candidate_semantic_id(row),
            row.get("terminal"),
            row.get("progressed"),
            row.get("target_writes"),
            row.get("writes", ()),
            row.get("action_count"),
        )
    )


def _validate_candidate(row: Mapping[str, object], *, selector: str) -> None:
    if row.get("selector") != selector:
        raise ValueError("candidate_selector")
    columns = tuple(tuple(column) for column in row.get("columns", ()))
    if len(columns) != 6:
        raise ValueError("candidate_column_count")
    for column in columns:
        _bits(column)
    events = tuple(row.get("events", ()))
    if len(events) != 6 or [event.get("marker_rank") for event in events] != list(range(6)):
        raise ValueError("candidate_event_alignment")
    marker_positions = [tuple(event.get("marker_position", ())) for event in events]
    expected_controls = {
        step: ROUTE[start:step]
        for start, step in zip((0,) + EVENT_STEPS[:-1], EVENT_STEPS)
    }
    for column, event, marker_position in zip(columns, events, marker_positions):
        step = event.get("route_step")
        selected_step = step if selector == "commit" else step - 1
        if (
            step not in EVENT_STEPS
            or len(marker_position) != 2
            or event.get("controls") != expected_controls[step]
            or event.get("selected_step") != selected_step
            or event.get("selected_control") != ROUTE[selected_step - 1]
            or _bits(event.get("source_code", ())) != column
        ):
            raise ValueError("candidate_event_evidence")
    if marker_positions != sorted(marker_positions) or len(set(marker_positions)) != 6:
        raise ValueError("candidate_event_alignment")
    if (
        not isinstance(row.get("progressed"), bool)
        or row.get("submit_clicks") != 1
        or not 0 <= int(row.get("target_writes", -1)) <= 36
        or not 13 <= int(row.get("action_count", -1)) <= ACTION_BUDGET
    ):
        raise ValueError("candidate_scientific_boundary")
    if row.get("semantic_id") != candidate_semantic_id(row):
        raise ValueError("candidate_semantic_id")


def _source_head() -> str:
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    return subprocess.check_output(
        ("git", "rev-parse", "HEAD"),
        cwd=Path(__file__).resolve().parents[1],
        text=True,
    ).strip()


def run_candidate(*, selector: str = "commit", enter_g6=None) -> dict[str, object]:
    if enter_g6 is None:
        from arc3_public_g6_consequence_projection import enter_public_g6

        enter_g6 = enter_public_g6
    observation_session, frame, boundary = enter_g6()
    board_top, _ = _find_board(_matrix(frame))
    steps = []
    for step, control in enumerate(ROUTE, start=1):
        if control not in boundary.control_points:
            raise ValueError(f"missing_control:{control}")
        before = _matrix(frame)
        frame = observation_session.click(*boundary.control_points[control])
        after = _matrix(frame)
        marker_changes = tuple(
            (row, column)
            for row in range(board_top)
            for column in range(len(after[0]))
            if before[row][column] != after[row][column]
        )
        if len(marker_changes) > 1:
            raise ValueError("non_singleton_marker_response")
        steps.append(
            {
                "step": step,
                "control": control,
                "source_code": list(_bits(_source_bits(after))),
                "marker_position": (
                    list(marker_changes[0]) if marker_changes else None
                ),
            }
        )
    columns, events = projection_from_trace(ROUTE, steps, selector=selector)

    submission_session, start_frame, submission_boundary = enter_g6()
    if len(submission_boundary.target_cells) != 6:
        raise ValueError("target_column_count")
    writes = []
    frame = start_frame
    for column_index, (column, target_column) in enumerate(
        zip(columns, submission_boundary.target_cells)
    ):
        if len(target_column) != 6:
            raise ValueError("target_row_count")
        for row_index, (bit, (x, y)) in enumerate(zip(column, target_column)):
            if bit != submission_boundary.initial_columns[column_index][row_index]:
                frame = submission_session.click(x, y)
                writes.append(
                    {
                        "row": row_index,
                        "column": column_index,
                        "value": bit,
                    }
                )
    terminal = submission_session.click(*submission_boundary.submit)
    progressed = int(terminal.levels_completed) > int(start_frame.levels_completed)
    row = {
        "selector": selector,
        "columns": [list(column) for column in columns],
        "events": events,
        "progressed": progressed,
        "terminal": [int(terminal.levels_completed), str(terminal.state)],
        "target_writes": len(writes),
        "writes": writes,
        "submit_clicks": 1,
        "action_count": len(ROUTE) + len(writes) + 1,
    }
    row["semantic_id"] = candidate_semantic_id(row)
    _validate_candidate(row, selector=selector)
    return row


def _residual(
    base,
    reason: str,
    *,
    candidate=None,
    verification=None,
    ablation=None,
    error=None,
):
    return {
        **base,
        "status": "RESIDUAL",
        "classification": "NON_EVIDENCE",
        "candidate": candidate,
        "verification": list(verification or ()),
        "ablation": ablation,
        "target_writes": int(candidate.get("target_writes", 0)) if candidate else 0,
        "residual": {"reason": reason, "error": error},
    }


def build_result(*, head: str | None = None, runner=None, enter_g6=None):
    if runner is None:
        runner = lambda selector="commit": run_candidate(
            selector=selector,
            enter_g6=enter_g6,
        )
    base = {
        "schema": SCHEMA,
        "head": head or _source_head(),
        "route": ROUTE,
        "event_steps": list(EVENT_STEPS),
        "action_budget_per_candidate": ACTION_BUDGET,
        "model_calls": 0,
        "source_inspection": False,
        "claim_boundary": (
            "exact public tn36 G6; six singleton marker commits on route "
            "RRRRUULLUUUL; spatial marker alignment; source code at the event's "
            "second click; one candidate; two exact replays only on progress"
        ),
    }
    try:
        candidate = runner(selector="commit")
        _validate_candidate(candidate, selector="commit")
    except Exception as error:
        result = _residual(
            base,
            "candidate_exception",
            error=f"{type(error).__name__}:{error}",
        )
        validate_result(result, executing_head=str(result["head"]))
        return result
    if not candidate["progressed"]:
        result = {
            **base,
            "status": "REJECTED",
            "classification": "WARRANTED_NEGATIVE",
            "candidate": candidate,
            "verification": [],
            "ablation": None,
            "target_writes": candidate["target_writes"],
        }
        validate_result(result, executing_head=str(result["head"]))
        return result
    verification = []
    try:
        for _ in range(VERIFICATION_REPLAYS):
            row = runner(selector="commit")
            _validate_candidate(row, selector="commit")
            verification.append(row)
    except Exception as error:
        result = _residual(
            base,
            "verification_exception",
            candidate=candidate,
            verification=verification,
            error=f"{type(error).__name__}:{error}",
        )
        validate_result(result, executing_head=str(result["head"]))
        return result
    identity = _candidate_identity(candidate)
    if any(_candidate_identity(row) != identity for row in verification):
        result = _residual(
            base,
            "verification_identity_drift",
            candidate=candidate,
            verification=verification,
        )
        validate_result(result, executing_head=str(result["head"]))
        return result
    if not all(row["progressed"] for row in verification):
        result = _residual(
            base,
            "verification_no_progress",
            candidate=candidate,
            verification=verification,
        )
        validate_result(result, executing_head=str(result["head"]))
        return result
    try:
        ablation = runner(selector="first")
        _validate_candidate(ablation, selector="first")
    except Exception as error:
        result = _residual(
            base,
            "ablation_exception",
            candidate=candidate,
            verification=verification,
            error=f"{type(error).__name__}:{error}",
        )
        validate_result(result, executing_head=str(result["head"]))
        return result
    result = {
        **base,
        "status": "PROMOTED",
        "classification": "WARRANTED_POSITIVE",
        "candidate": candidate,
        "verification": verification,
        "ablation": ablation,
        "target_writes": candidate["target_writes"],
    }
    validate_result(result, executing_head=str(result["head"]))
    return result


def validate_result(result: Mapping[str, object], *, executing_head: str):
    if result.get("schema") != SCHEMA:
        raise ValueError("projection_schema")
    if result.get("head") != executing_head:
        raise ValueError("stale_evidence_head")
    if (
        result.get("model_calls") != 0
        or result.get("source_inspection") is not False
    ):
        raise ValueError("scientific_boundary")
    if (
        result.get("route") != ROUTE
        or tuple(result.get("event_steps", ())) != EVENT_STEPS
        or result.get("action_budget_per_candidate") != ACTION_BUDGET
    ):
        raise ValueError("declared_boundary")
    status = result.get("status")
    if status == "RESIDUAL":
        if result.get("classification") != "NON_EVIDENCE":
            raise ValueError("residual_classification")
        if not result.get("residual", {}).get("reason"):
            raise ValueError("residual_reason")
        candidate = result.get("candidate")
        if candidate is not None:
            _validate_candidate(candidate, selector="commit")
        for row in result.get("verification", ()):
            _validate_candidate(row, selector="commit")
        ablation = result.get("ablation")
        if ablation is not None:
            _validate_candidate(ablation, selector="first")
        expected_writes = candidate.get("target_writes", 0) if candidate else 0
        if result.get("target_writes") != expected_writes:
            raise ValueError("target_write_accounting")
        return result
    candidate = result.get("candidate", {})
    _validate_candidate(candidate, selector="commit")
    if result.get("target_writes") != candidate.get("target_writes"):
        raise ValueError("target_write_accounting")
    if status == "REJECTED":
        if (
            result.get("classification") != "WARRANTED_NEGATIVE"
            or candidate.get("progressed") is not False
            or result.get("verification") != []
            or result.get("ablation") is not None
        ):
            raise ValueError("negative_evidence")
        return result
    if status != "PROMOTED" or result.get("classification") != "WARRANTED_POSITIVE":
        raise ValueError("projection_status")
    verification = tuple(result.get("verification", ()))
    if len(verification) != VERIFICATION_REPLAYS:
        raise ValueError("verification_replay_count")
    identity = _candidate_identity(candidate)
    for row in verification:
        _validate_candidate(row, selector="commit")
        if not row.get("progressed") or _candidate_identity(row) != identity:
            raise ValueError("verification_identity")
    ablation = result.get("ablation", {})
    _validate_candidate(ablation, selector="first")
    return result


def main():
    result = build_result()
    out = Path(
        os.environ.get(
            "OUTDIR",
            "evidence/arc3-public-g6-marker-commit-projection",
        )
    ).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(f"ARC3_PUBLIC_G6_MARKER_COMMIT_PROJECTION={result['status']}")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

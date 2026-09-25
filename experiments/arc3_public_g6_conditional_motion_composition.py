from __future__ import annotations

from collections import defaultdict
import json
import os
from pathlib import Path
import subprocess

from arc3_public_g3_g5_local_role_supervision import (
    ACTION_BUDGET,
    _bits,
    _collect_training_slots,
    _execute_projection,
    _read_g6_observation,
    _read_observations,
    _read_training,
)
from metalogic_arc3.protected_future import UnknownResidual, canonical_digest


INTERFACE_ID = "event.conditional-motion-composition@1"
SCHEMA = "arc3.g6-conditional-motion-composition@1"
COMPOSITIONS = ("or", "and", "xor")
EXPECTED_G6_MOTIONS = (
    (-1, -1),
    (-1, 0),
    (0, -1),
    (-1, 0),
    (0, 1),
    (0, 1),
)


def _residual(reason, evidence=()):
    return UnknownResidual(INTERFACE_ID, reason, tuple(str(item) for item in evidence))


def _motion(row):
    try:
        value = tuple(int(item) for item in row["features"]["primitive_motion"])
    except (KeyError, TypeError, ValueError):
        raise ValueError("primitive_motion") from None
    if len(value) != 2:
        raise ValueError("primitive_motion")
    return value


def _fit_conditional_motion(training_slots, g6_events):
    slots = tuple(training_slots)
    census = sorted((int(row.get("level", -1)), int(row.get("slot_index", -1))) for row in slots)
    expected = [(level, slot) for level in (3, 4, 5) for slot in range(6)]
    if census != expected:
        return _residual("warranted_slot_census", (repr(census),))

    grouped = defaultdict(list)
    for row in slots:
        level = int(row["level"])
        slot = int(row["slot_index"])
        if row.get("terminal_consequence") not in {"PROGRESS", "WIN"}:
            return _residual("missing_terminal_warrant", (f"G{level}:slot{slot}",))
        motion = _motion(row)
        if motion == (0, 0):
            continue
        try:
            output = _bits(row.get("output"))
        except ValueError as error:
            return _residual("invalid_warranted_output", (f"G{level}:slot{slot}:{error}",))
        grouped[motion].append((level, slot, output))

    collisions = []
    for motion, rows in sorted(grouped.items()):
        if len({output for _, _, output in rows}) > 1:
            collisions.extend(
                f"{motion}:G{level}:slot{slot}:{''.join(map(str, output))}"
                for level, slot, output in rows
            )
    if collisions:
        return _residual("nonfunctional_nonstationary_motion", collisions)

    codebook = {motion: rows[0][2] for motion, rows in grouped.items()}
    g6_motions = tuple(_motion(event) for event in g6_events)
    if g6_motions != EXPECTED_G6_MOTIONS:
        return _residual("g6_motion_residual_census", (repr(g6_motions),))
    uncovered = tuple(sorted({motion for motion in g6_motions if motion not in codebook}))
    if uncovered != ((-1, -1),):
        return _residual("g6_motion_residual_census", (repr(uncovered),))
    for component in ((-1, 0), (0, -1)):
        if component not in codebook:
            return _residual("missing_diagonal_component", (repr(component),))
    return {
        "cardinal_codebook": codebook,
        "g6_motions": g6_motions,
        "uncovered": uncovered,
        "directly_covered": sum(motion in codebook for motion in g6_motions),
    }


def _compose(first, second, name):
    if name == "or":
        return tuple(left | right for left, right in zip(first, second))
    if name == "and":
        return tuple(left & right for left, right in zip(first, second))
    if name == "xor":
        return tuple(left ^ right for left, right in zip(first, second))
    raise ValueError("composition")


def _compile_columns(fitted, composition):
    codebook = fitted["cardinal_codebook"]
    diagonal = _compose(codebook[(-1, 0)], codebook[(0, -1)], composition)
    return tuple(
        diagonal if motion == (-1, -1) else codebook[motion]
        for motion in fitted["g6_motions"]
    )


def _unknown_candidate(residual, action_count):
    return {
        "status": "UNKNOWN",
        "residual": {
            "missing_interface": residual.interface_id,
            "reason": residual.reason,
            "evidence": list(residual.evidence),
        },
        "target_writes": 0,
        "submit_clicks": 0,
        "action_count": int(action_count),
    }


def run_candidate(composition, *, training_reader=None, observation_reader=None,
                  g6_reader=None, executor=None):
    training = (training_reader or _read_training)()
    observations = (observation_reader or _read_observations)()
    g6_observation = (g6_reader or _read_g6_observation)()
    observation_actions = (
        sum(int(row.get("action_count", 0)) for row in training.get("levels", ()))
        + int(observations.get("action_count", 0))
        + int(g6_observation.get("action_count", 0))
    )
    slots = _collect_training_slots(training, observations)
    if isinstance(slots, UnknownResidual):
        return _unknown_candidate(slots, observation_actions)
    fitted = _fit_conditional_motion(slots, tuple(g6_observation.get("events", ())))
    if isinstance(fitted, UnknownResidual):
        return _unknown_candidate(fitted, observation_actions)
    columns = _compile_columns(fitted, composition)
    execution = dict((executor or _execute_projection)(columns))
    execution["action_count"] = observation_actions + int(execution.get("action_count", 0))
    codebook = [
        {"motion": list(motion), "output": list(output)}
        for motion, output in sorted(fitted["cardinal_codebook"].items())
    ]
    candidate = {
        "status": "CANDIDATE",
        "composition": composition,
        "conditional_interface": {
            "nonstationary": "primitive_motion",
            "stationary": "endpoint_occupancy+source_port_mode",
            "directly_supervised_g6_columns": fitted["directly_covered"],
            "sole_residual": list(fitted["uncovered"][0]),
        },
        "cardinal_codebook": codebook,
        "g6_motions": [list(row) for row in fitted["g6_motions"]],
        "columns": [list(column) for column in columns],
        **execution,
    }
    candidate["semantic_id"] = canonical_digest((
        INTERFACE_ID, composition, tuple((tuple(row["motion"]), tuple(row["output"])) for row in codebook), columns
    ))
    return candidate


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
        candidate.get("semantic_id"), candidate.get("terminal"), candidate.get("progressed"),
        candidate.get("target_writes"), candidate.get("submit_clicks"), candidate.get("action_count"),
    )


def _validate_candidate(candidate):
    if candidate.get("status") != "CANDIDATE" or candidate.get("composition") not in COMPOSITIONS:
        raise ValueError("candidate_boundary")
    columns = tuple(_bits(column) for column in candidate.get("columns", ()))
    if (
        len(columns) != 6
        or not isinstance(candidate.get("progressed"), bool)
        or candidate.get("submit_clicks") != 1
        or not 0 <= int(candidate.get("target_writes", -1)) <= 36
        or not 1 <= int(candidate.get("action_count", -1)) <= ACTION_BUDGET
    ):
        raise ValueError("candidate_boundary")


def build_result(*, head=None, runner=None):
    head = head or _source_head()
    runner = runner or run_candidate
    base = {
        "schema": SCHEMA,
        "head": head,
        "model_calls": 0,
        "source_inspection": False,
        "action_budget_per_candidate": ACTION_BUDGET,
        "candidate_bound": len(COMPOSITIONS),
        "claim_boundary": (
            "exact public tn36; nonstationary primitive-motion law fitted on 18 exact "
            "terminal-warranted G3-G5 slots; five G6 columns held to direct supervision; "
            "OR/AND/XOR tested only for the sole diagonal residual"
        ),
    }
    attempts = []
    for composition in COMPOSITIONS:
        try:
            candidate = runner(composition)
        except Exception as error:
            result = {**base, "status": "RESIDUAL", "classification": "NON_EVIDENCE",
                      "attempts": attempts, "verification": [], "target_writes": sum(int(x.get("target_writes", 0)) for x in attempts),
                      "residual": {"reason": "candidate_exception", "error": f"{type(error).__name__}:{error}"}}
            validate_result(result, executing_head=head)
            return result
        if candidate.get("status") == "UNKNOWN":
            result = {**base, "status": "RESIDUAL", "classification": "EXACT_RESIDUAL",
                      "attempts": attempts + [candidate], "verification": [], "target_writes": 0,
                      "residual": candidate.get("residual", {"reason": "unknown_conditional_motion"})}
            validate_result(result, executing_head=head)
            return result
        _validate_candidate(candidate)
        attempts.append(candidate)
        if not candidate.get("progressed"):
            continue
        verification = []
        try:
            verification = [runner(composition), runner(composition)]
        except Exception as error:
            result = {**base, "status": "RESIDUAL", "classification": "NON_EVIDENCE",
                      "attempts": attempts, "verification": verification,
                      "target_writes": sum(int(x.get("target_writes", 0)) for x in attempts),
                      "residual": {"reason": "verification_exception", "error": f"{type(error).__name__}:{error}"}}
            validate_result(result, executing_head=head)
            return result
        if any(
            row.get("status") != "CANDIDATE" or not row.get("progressed")
            or _candidate_identity(row) != _candidate_identity(candidate)
            for row in verification
        ):
            result = {**base, "status": "RESIDUAL", "classification": "NON_EVIDENCE",
                      "attempts": attempts, "verification": verification,
                      "target_writes": sum(int(x.get("target_writes", 0)) for x in attempts),
                      "residual": {"reason": "verification_identity_drift"}}
            validate_result(result, executing_head=head)
            return result
        result = {**base, "status": "PROMOTED", "classification": "WARRANTED_POSITIVE",
                  "attempts": attempts, "winner": candidate, "verification": verification,
                  "target_writes": sum(int(x.get("target_writes", 0)) for x in attempts)}
        validate_result(result, executing_head=head)
        return result
    result = {**base, "status": "REJECTED", "classification": "WARRANTED_NEGATIVE",
              "attempts": attempts, "verification": [],
              "target_writes": sum(int(x.get("target_writes", 0)) for x in attempts)}
    validate_result(result, executing_head=head)
    return result


def validate_result(result, *, executing_head):
    if result.get("schema") != SCHEMA or result.get("head") != executing_head:
        raise ValueError("result_identity")
    if result.get("model_calls") != 0 or result.get("source_inspection") is not False:
        raise ValueError("scientific_boundary")
    if result.get("action_budget_per_candidate") != ACTION_BUDGET or result.get("candidate_bound") != 3:
        raise ValueError("scientific_boundary")
    for candidate in result.get("attempts", ()):
        if candidate.get("status") == "CANDIDATE":
            _validate_candidate(candidate)
    status = result.get("status")
    if status == "RESIDUAL":
        if result.get("classification") not in {"EXACT_RESIDUAL", "NON_EVIDENCE"} or not result.get("residual", {}).get("reason"):
            raise ValueError("residual_boundary")
        if result.get("classification") == "EXACT_RESIDUAL":
            last = result.get("attempts", ())[-1]
            if last.get("status") != "UNKNOWN" or last.get("target_writes") != 0 or last.get("submit_clicks") != 0:
                raise ValueError("unknown_side_effect")
    elif status == "REJECTED":
        if result.get("classification") != "WARRANTED_NEGATIVE" or len(result.get("attempts", ())) != 3 or result.get("verification"):
            raise ValueError("negative_boundary")
        if any(row.get("progressed") for row in result["attempts"]):
            raise ValueError("negative_boundary")
    elif status == "PROMOTED":
        winner = result.get("winner")
        if result.get("classification") != "WARRANTED_POSITIVE" or not winner or not winner.get("progressed") or len(result.get("verification", ())) != 2:
            raise ValueError("positive_boundary")
        if any(_candidate_identity(row) != _candidate_identity(winner) for row in result["verification"]):
            raise ValueError("positive_boundary")
    else:
        raise ValueError("result_status")
    return result


def main():
    result = build_result()
    out = Path(os.environ.get("OUTDIR", "evidence/arc3-public-g6-conditional-motion-composition")).resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"ARC3_PUBLIC_G6_CONDITIONAL_MOTION_COMPOSITION={result['status']}")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

"""Replay-gated retention around the immutable ARC-3 discovery harness.

The frozen harness generates and externally replays action programs. This
adapter sends only pre-promotion observations and the generated programs to a
Lean instance of SynthesisCore.develop/promoteIfReplayAdequate. Deployment can
occur only after Lean proves exact promotion of the generated candidate.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence


class QualificationError(RuntimeError):
    """The external evidence or shared-runtime gate did not qualify."""


def verify_git_commit(path: Path, expected: str) -> str:
    if len(expected) != 40 or any(c not in "0123456789abcdef" for c in expected):
        raise QualificationError(f"invalid frozen commit identifier: {expected!r}")
    resolved = Path(path).resolve()
    root = subprocess.run(
        ["git", "-C", str(resolved), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if root.returncode != 0 or Path(root.stdout.strip()).resolve() != resolved:
        raise QualificationError("frozen path is not the checkout root")
    completed = subprocess.run(
        ["git", "-C", str(resolved), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    actual = completed.stdout.strip()
    if completed.returncode != 0 or actual != expected:
        raise QualificationError(
            f"frozen checkout mismatch: expected {expected}, observed {actual or 'unavailable'}"
        )
    status = subprocess.run(
        ["git", "-C", str(resolved), "status", "--porcelain", "--untracked-files=all", "--ignored"],
        text=True,
        capture_output=True,
        check=False,
    )
    if status.returncode != 0 or status.stdout.strip():
        raise QualificationError("frozen checkout is not clean")
    submodules = subprocess.run(
        ["git", "-C", str(resolved), "submodule", "status", "--recursive"],
        text=True,
        capture_output=True,
        check=False,
    )
    bad_submodule = any(
        line and line[0] in "-+U" for line in submodules.stdout.splitlines()
    )
    if submodules.returncode != 0 or bad_submodule:
        raise QualificationError("frozen checkout has an unverified submodule state")
    return actual


@dataclass(frozen=True)
class GateRequest:
    cold_levels: int
    candidate_levels: int
    sham_levels: int
    candidate: tuple
    sham: tuple


@dataclass(frozen=True)
class GateApproval:
    program_sha256: str
    certificate_sha256: str | None = None
    marker: str = "ARC3_SHARED_GATE_PASS"


@dataclass(frozen=True)
class RetainedCapability:
    program: tuple
    program_sha256: str
    certificate_sha256: str | None
    gate_marker: str


def _canonical_program(program: Iterable[Any]) -> list[list[int]]:
    encoded = []
    for token in tuple(program):
        if type(token) is int:
            components = (token, 0, 0)
        elif isinstance(token, (tuple, list)) and len(token) == 3:
            components = tuple(token)
        else:
            raise QualificationError(f"unsupported action token: {token!r}")
        if any(type(value) is not int or value < 0 or value > (1 << 31) - 1
               for value in components):
            raise QualificationError(f"action token is outside the finite Nat boundary: {token!r}")
        encoded.append(list(components))
    if not encoded:
        raise QualificationError("empty programs cannot be promoted")
    return encoded


def program_digest(program: Iterable[Any]) -> str:
    payload = json.dumps(_canonical_program(program), separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _lean_program(name: str, program: Iterable[Any]) -> str:
    actions = ", ".join(f"⟨{kind}, {x}, {y}⟩" for kind, x, y in _canonical_program(program))
    return f"def {name} : List ActionToken := [{actions}]"


def render_lean_gate(*, cold_levels: int, candidate_levels: int,
                     sham_levels: int, candidate: Iterable[Any],
                     sham: Iterable[Any]) -> str:
    for name, value in (
        ("cold_levels", cold_levels),
        ("candidate_levels", candidate_levels),
        ("sham_levels", sham_levels),
    ):
        if not isinstance(value, int) or value < 0:
            raise QualificationError(f"{name} must be a nonnegative integer")
    candidate_def = _lean_program("candidateProgram", candidate)
    sham_def = _lean_program("shamProgram", sham)
    return f"""import LemmaSynthesis.SynthesisCore

namespace ARC3SharedRuntimeCertificate

structure ActionToken where
  kind : Nat
  x : Nat
  y : Nat
  deriving DecidableEq, Repr

{candidate_def}
{sham_def}

def coldLevels : Nat := {cold_levels}
def candidateReplayLevels : Nat := {candidate_levels}
def shamReplayLevels : Nat := {sham_levels}

inductive DeveloperArm | old | repaired
  deriving DecidableEq, Repr

inductive ProgramTag | sham | acquired
  deriving DecidableEq, Repr

open DeveloperArm ProgramTag

def univ : List DeveloperArm := [.old, .repaired]
def initialQ (_ : DeveloperArm) : Bool := false

def requiredCapability : DeveloperArm → Bool
  | .old => false
  | .repaired => true

def observedGain : ProgramTag → DeveloperArm → Bool
  | _, .old => false
  | .sham, .repaired => decide (shamReplayLevels > coldLevels)
  | .acquired, .repaired => decide (candidateReplayLevels > coldLevels)

def disc : ProgramTag → DeveloperArm → Bool
  | tag => observedGain tag

def candidates : List (SynthesisCore.Candidate DeveloperArm Bool ProgramTag) :=
  [ ⟨.sham, 0, disc .sham⟩
  , ⟨.acquired, 1, disc .acquired⟩ ]

def repairQ (tag : ProgramTag) (arm : DeveloperArm) : Bool × Bool :=
  (initialQ arm, disc tag arm)

def development :=
  SynthesisCore.develop univ initialQ requiredCapability candidates repairQ

def promoted :=
  SynthesisCore.promoteIfReplayAdequate univ requiredCapability repairQ development

def programFor : ProgramTag → List ActionToken
  | .sham => shamProgram
  | .acquired => candidateProgram

def promotedProgram := promoted.map programFor

theorem shared_develop_selects_acquired :
    development.map (fun outcome => outcome.selected) = some .acquired := by
  native_decide

theorem shared_replay_gate_promotes_acquired : promoted = some .acquired := by
  native_decide

theorem promoted_program_is_exact_generated_candidate :
    promotedProgram = some candidateProgram := by
  native_decide

def shamDevelopment :=
  SynthesisCore.develop univ initialQ requiredCapability
    [⟨.sham, 0, disc .sham⟩] repairQ

theorem sham_cannot_be_selected :
    shamDevelopment.map (fun outcome => outcome.selected) = none := by
  native_decide

def forgedOutcome : SynthesisCore.DevelopmentOutcome DeveloperArm ProgramTag :=
  {{ residual := (.old, .repaired), selected := .acquired, replayResiduals := [] }}

def failedRepairQ (_ : ProgramTag) (_ : DeveloperArm) : Bool × Bool :=
  (false, false)

theorem failed_replay_refuses_exact_selected_tag :
    SynthesisCore.promoteIfReplayAdequate
      univ requiredCapability failedRepairQ (some forgedOutcome) = none := by
  native_decide

#eval IO.println "ARC3_SHARED_GATE_PASS"

end ARC3SharedRuntimeCertificate
"""


class LeanGate:
    def __init__(self, *, lean: str, lean_path: Path, certificate_path: Path):
        self.lean = lean
        self.lean_path = Path(lean_path).resolve()
        self.certificate_path = Path(certificate_path).resolve()

    def __call__(self, request: GateRequest) -> GateApproval | None:
        source = render_lean_gate(
            cold_levels=request.cold_levels,
            candidate_levels=request.candidate_levels,
            sham_levels=request.sham_levels,
            candidate=request.candidate,
            sham=request.sham,
        )
        self.certificate_path.parent.mkdir(parents=True, exist_ok=True)
        self.certificate_path.write_text(source, encoding="utf-8")
        env = dict(os.environ)
        env["LEAN_PATH"] = str(self.lean_path)
        completed = subprocess.run(
            [self.lean, str(self.certificate_path)],
            text=True,
            capture_output=True,
            env=env,
            check=False,
        )
        output = completed.stdout + completed.stderr
        if completed.returncode != 0 or "ARC3_SHARED_GATE_PASS" not in output:
            return None
        return GateApproval(
            program_sha256=program_digest(request.candidate),
            certificate_sha256=hashlib.sha256(source.encode("utf-8")).hexdigest(),
        )


def _primitive_deployment(actions: Sequence[Any], budget: int) -> tuple:
    actions = tuple(actions)
    if not actions:
        raise QualificationError("empty public action alphabet")
    return (actions * ((budget + len(actions) - 1) // len(actions)))[:budget]


def _first_sham(development: Any, candidate: tuple) -> tuple:
    for record in development.evidence:
        suffix = tuple(record.get("suffix", ()))
        fully_executed_from_initial = (
            int(record.get("target", -1)) == 0
            and int(record.get("actions", -1)) >= len(suffix)
        )
        if (
            suffix
            and suffix != candidate
            and int(record.get("progress", 0)) <= 0
            and fully_executed_from_initial
        ):
            return suffix
    raise QualificationError("no fully executed zero-progress sham in frozen evidence")


def _initial(result: dict) -> str:
    value = result.get("initial_sha256")
    if not isinstance(value, str) or not value:
        raise QualificationError("external replay omitted initial-state hash")
    return value


def qualify_transfer(*, factory: Callable[[], Any], actions: Sequence[Any],
                     discover_levels: Callable[..., Any],
                     execute_stage: Callable[..., dict],
                     gate: Callable[[GateRequest], GateApproval | None],
                     budget: int, max_episodes: int, max_depth: int,
                     max_training_actions: int, max_levels: int) -> dict:
    """Discover, replay-gate, retain, then deploy on fresh environments."""
    primitive_program = _primitive_deployment(actions, budget)
    cold = execute_stage(
        factory(), (), primitive_program, 0, budget, stop_at_progress=False
    )
    development = discover_levels(
        factory, actions, budget, max_episodes, max_depth,
        max_training_actions, max_levels,
    )
    development_status = str(getattr(development, "status", ""))
    if development_status.startswith(("INCONCLUSIVE", "UNSUPPORTED")):
        raise QualificationError(
            "inconclusive frozen discovery: " + (development_status or "missing status")
        )
    if not development.options:
        raise QualificationError("frozen harness generated no witnessed option")
    candidate = tuple(development.options[0])
    sham = _first_sham(development, candidate)

    sham_replay = execute_stage(factory(), (), sham, 0, budget, stop_at_progress=False)
    candidate_replay = execute_stage(
        factory(), (), candidate, 0, budget, stop_at_progress=False
    )
    starts = {
        _initial(cold),
        _initial(sham_replay),
        _initial(candidate_replay),
        development.initial_sha256,
    }
    if len(starts) != 1:
        raise QualificationError("inconclusive unmatched pre-promotion starts")
    cold_levels = int(cold["levels_completed"])
    sham_levels = int(sham_replay["levels_completed"])
    candidate_levels = int(candidate_replay["levels_completed"])
    if candidate_levels <= cold_levels:
        raise QualificationError("candidate failed fresh pre-promotion replay")
    if sham_levels > cold_levels:
        raise QualificationError("selected sham unexpectedly improves over cold")

    request = GateRequest(
        cold_levels=cold_levels,
        candidate_levels=candidate_levels,
        sham_levels=sham_levels,
        candidate=candidate,
        sham=sham,
    )
    approval = gate(request)
    expected_digest = program_digest(candidate)
    if approval is None:
        raise QualificationError("shared Lean replay gate refused promotion")
    if approval.program_sha256 != expected_digest:
        raise QualificationError("gate approval does not name the generated candidate")
    certificate_sha256 = approval.certificate_sha256
    valid_certificate_binding = (
        isinstance(certificate_sha256, str)
        and len(certificate_sha256) == 64
        and all(char in "0123456789abcdef" for char in certificate_sha256)
        and approval.marker == "ARC3_SHARED_GATE_PASS"
    )
    if not valid_certificate_binding:
        raise QualificationError("gate approval lacks an exact certificate binding")

    retained = RetainedCapability(
        program=candidate,
        program_sha256=expected_digest,
        certificate_sha256=approval.certificate_sha256,
        gate_marker=approval.marker,
    )
    warm = execute_stage(
        factory(), (), retained.program, 0, budget, stop_at_progress=False
    )
    ablation = execute_stage(
        factory(), (), primitive_program, 0, budget, stop_at_progress=False
    )
    starts.update((_initial(warm), _initial(ablation)))
    if len(starts) != 1:
        raise QualificationError("inconclusive unmatched deployment starts")
    improved = int(warm["levels_completed"]) > cold_levels
    ablation_restores_failure = int(ablation["levels_completed"]) <= cold_levels
    if not improved:
        raise QualificationError("retained candidate failed fresh warm deployment")
    if not ablation_restores_failure:
        raise QualificationError("exact ablation did not restore baseline failure")

    return {
        "status": "VERIFIED_SHARED_RUNTIME_TRANSFER",
        "improved": True,
        "development": development.snapshot(),
        "cold": cold,
        "sham_replay": sham_replay,
        "candidate_replay": candidate_replay,
        "retained": asdict(retained),
        "warm": warm,
        "ablation": ablation,
        "controls": {
            "matching_initial_sha256": starts.pop(),
            "sham_refused": True,
            "failed_replay_refused_in_lean": True,
            "exact_ablation_restores_failure": True,
        },
    }

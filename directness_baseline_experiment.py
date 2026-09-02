"""Frozen matched replay for Experiment 1: the directness gate.

Scope: a bounded synthetic test of viable-PUSH prioritization, not evidence of
cross-domain or natural-task superiority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Mapping

from workflow_optimizer import (
    ActionClass,
    DevelopmentState,
    ProblemContract,
    Proposal,
    TerminalState,
    Verification,
    WorkflowController,
)


@dataclass(frozen=True)
class FrozenCase:
    id: str
    split: str
    budget: int
    proposals: tuple[Proposal, ...]
    outcomes: Mapping[str, Verification]


def _case(case_id: str, split: str, direct_id: str, distractor: ActionClass) -> FrozenCase:
    proposals = (
        Proposal(direct_id, ActionClass.PUSH, 3, 8),
        Proposal(f"{case_id}_side", distractor, 1, 1, information_value=2),
        Proposal(f"{case_id}_follow", ActionClass.PUSH, 2, 3),
    )
    outcomes = {
        direct_id: Verification(True, TerminalState.SOLVED, 10),
        f"{case_id}_side": Verification(True, TerminalState.IMPROVED, 0),
        f"{case_id}_follow": Verification(
            False, TerminalState.UNKNOWN, 0, "direct route still required"
        ),
    }
    return FrozenCase(case_id, split, 3, proposals, outcomes)


CASES = (
    _case("dev_a", "develop", "prove_existing_lemma", ActionClass.PROBE),
    _case("dev_b", "develop", "repair_known_test", ActionClass.PROBE),
    _case("hold_c", "heldout", "execute_feasible_plan", ActionClass.REFRAME),
    _case("hold_d", "heldout", "run_supported_solver", ActionClass.META),
)


def run_case(case: FrozenCase, controller: WorkflowController) -> DevelopmentState:
    contract = ProblemContract(
        target=f"solve {case.id}",
        verifier=f"frozen_table:{case.id}",
        budget=case.budget,
        success_criteria="terminal == SOLVED",
        allowed_evidence=("proposal id", "frozen verifier output"),
        forbidden_leakage=("held-out outcome during ranking",),
    )
    state = DevelopmentState(contract=contract, workflow=controller.name)
    return controller.run(state, case.proposals, lambda p: case.outcomes[p.id])


def run_experiment() -> dict:
    controllers = (
        WorkflowController("Pi0_value_per_cost", directness_gate=False),
        WorkflowController("Pi1_directness_gate", directness_gate=True),
    )
    rows = []
    for case in CASES:
        for controller in controllers:
            state = run_case(case, controller)
            rows.append(
                {
                    "case": case.id,
                    "split": case.split,
                    "workflow": controller.name,
                    "terminal": state.terminal.value,
                    "solved": state.terminal == TerminalState.SOLVED,
                    "spent": state.spent,
                    "proposal_order": [
                        e["proposal"]["id"] for e in state.memory.provenance
                    ],
                }
            )
    case_payload = json.dumps(
        [
            {
                "id": c.id,
                "split": c.split,
                "budget": c.budget,
                "proposals": [asdict(p) for p in c.proposals],
                "outcomes": {k: asdict(v) for k, v in c.outcomes.items()},
            }
            for c in CASES
        ],
        sort_keys=True,
    )
    return {
        "experiment": "directness_baseline_v1",
        "scope": "bounded synthetic matched replay",
        "case_sha256": hashlib.sha256(case_payload.encode()).hexdigest(),
        "rows": rows,
    }


def write_report(path: Path) -> dict:
    report = run_experiment()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


if __name__ == "__main__":
    print(
        json.dumps(
            write_report(Path("artifacts/directness_baseline_v1.json")),
            indent=2,
            sort_keys=True,
        )
    )

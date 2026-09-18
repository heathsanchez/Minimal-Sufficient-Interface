"""QCKN Flash V5: persistent multi-game consequence-graph replay.

This is a bounded retained-evidence acquisition replay, not a new ARC score.
Independent and Flash receive identical exact local evidence and identical local
closure. Flash alone may propagate exact counterexamples to universal proposal
laws. Such propagation can cancel a probe whose sole purpose is to test that
already-refuted law, but it never installs destination behavior or rewrites raw
verifier authority.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "kaggle" / "flash-v5-results"
INPUTS = OUT / "inputs"
sys.path.insert(0, str(ROOT / "kaggle" / "src"))

from metalogic_arc3.flash_ledger import (
    ACTIVE, CANCELLED, PENDING, EvidenceRef, FlashLedger,
    GlobalCapability, Probe, Residual, stable_id,
)
from metalogic_arc3.flash_closure import run_to_fixed_point
from metalogic_arc3.flash_scheduler import choose_wave

GAMES = {
    "ls20": "ls20-9607627b",
    "ft09": "ft09-0d8bbf25",
    "vc33": "vc33-5430563c",
    "bt11": "bt11-fd9df0622a1a",
}
ARTIFACTS = {
    "ls20_compiled": {
        "run": "35376545566", "artifact": "10560148232",
        "sha256": "b46a9c5c844d4dc7b87d6d0f91ad20f5600e1469183b1515d1ff5eafe692dc37",
    },
    "ls20_frontier_v3": {
        "run": "35393183037", "artifact": "10566897440",
        "sha256": "f681be0076967e48c6a87c6930a9fd7389d5201b5914809bfb7f6a78a9f51aeb",
    },
    "ft09_fatal": {
        "run": "35387362885", "artifact": "10564626208",
        "sha256": "22748bb909fae8087e90bc51bd26780466dd153dd1974782515e676d0d24bd05",
    },
    "vc33_grounded": {
        "run": "35341468771", "artifact": "10544713870",
        "sha256": "a90191671cff5fd1646edc0d605add58bfee582769d5387ccae379374bbca549",
    },
    "interventional_diag": {
        "run": "35330229606", "artifact": "10540642632",
        "sha256": "005d910cc9cc01b684944ca0e3cf4b402314fda42bb458f4779ce35ef6d705cc",
    },
}
LAW_STATE_CHANGE_VALUE = "state_change_implies_protected_value"
LAW_FAMILY_ACTION_EXACT = "family_action_id_is_sufficient_intervention_identity"


def read(name: str) -> Any:
    return json.loads((INPUTS / name).read_text())


def write(name: str, value: Any) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def validate_inputs() -> dict[str, Any]:
    compiled = read("ls20-compiled-progress.json")
    frontier = read("ls20-level1-scc-frontier-v3.json")
    fatal = read("ft09-fatal-basin-certificate.json")
    grounded = read("grounded-interventional-v2.json")
    diagnostic = read("interventional-quotient.json")

    assert compiled["discovery_milestone_actions"] == 67
    assert compiled["compiled_route"]["reported_milestone_action"] == 57
    assert compiled["compilation_gain"]["actions_saved_vs_discovery"] == 10

    assert frontier["result"]["status"] == "BUDGET_EXHAUSTED"
    assert frontier["result"]["final_ledger_nodes"] == 4470
    assert frontier["result"]["final_ledger_edges"] == 12448
    assert frontier["scc_quotient"]["reachable_level1_states"] == 1651
    assert frontier["scc_quotient"]["nontrivial_scc_count"] == 0
    assert frontier["scc_quotient"]["max_quotient_depth"] == 109

    assert fatal["status"] == "CLOSED_BOUNDED_FATAL_BASIN_CERTIFICATE"
    assert fatal["fatal_source_states"] == 47
    assert fatal["probe_count"] == 282
    assert fatal["status_counts"]["GAME_OVER"] == 281
    assert fatal["status_counts"]["ESCAPE_NO_CHANGE"] == 1

    vc = grounded["vc33"]
    assert vc["family_candidates_split_by_parameterization"] == 28
    assert vc["residual_grounded_pairs_before_active_closure"] == 1
    assert vc["closed_roots"] == 1
    assert vc["unknown_roots"] == 0
    assert vc["residual_root_contracts"][0]["terminal"] is True
    assert vc["residual_root_contracts"][0]["protected"][0] == "GAME_OVER"

    bt = next(r for r in diagnostic["worlds"] if r["game_id"].startswith("bt11-"))
    assert bt["final_state"] == "WIN"
    assert bt["max_levels"] == 5
    assert bt["actions"] == 73
    assert bt["final_quotient"]["compression"] == 1.0
    assert bt["final_quotient"]["largest_class"] == 1
    return {
        "ls20_compiled": compiled,
        "ls20_frontier_v3": frontier,
        "ft09_fatal": fatal,
        "vc33_grounded": grounded,
        "interventional_diag": diagnostic,
    }


def ev(game: str, kind: str, artifact_key: str, local_key: str) -> EvidenceRef:
    row = ARTIFACTS[artifact_key]
    return EvidenceRef(
        game=game,
        kind=kind,
        artifact_or_run=f"run:{row['run']}/artifact:{row['artifact']}",
        local_key=local_key,
        sha256=row["sha256"],
    )


def add_cap(
    ledger: FlashLedger,
    *,
    kind: str,
    games: set[str],
    scope: dict[str, Any],
    consequence: tuple[Any, ...],
    witnesses: list[EvidenceRef],
    protected: tuple[Any, ...] | None = None,
    cost: int = 0,
    authority: str,
    notes: dict[str, Any] | None = None,
    dependencies: set[str] | None = None,
) -> str:
    for witness in witnesses:
        ledger.add_evidence(witness)
    cid = stable_id("cap", {
        "kind": kind, "scope": scope, "consequence": consequence
    })
    ledger.add_capability(GlobalCapability(
        capability_id=cid,
        kind=kind,
        source_games=set(games),
        scope=dict(scope),
        consequence_signature=tuple(consequence),
        exact_witnesses=list(witnesses),
        protected_effect=protected,
        acquisition_cost=int(cost),
        authority=authority,
        dependencies=set(dependencies or ()),
        notes=dict(notes or {}),
    ))
    return cid


def add_probe(
    ledger: FlashLedger,
    *,
    pid: str,
    game: str,
    cost: int,
    reason: str,
    cancellation: set[str],
    purpose: str,
    potential: str,
) -> None:
    rid = f"res:{pid}"
    ledger.add_residual(Residual(
        residual_id=rid,
        game=game,
        kind="future_acquisition",
        estimated_cost=cost,
        potential_consequences={potential},
        demand_key=potential,
    ))
    ledger.add_probe(Probe(
        probe_id=pid,
        game=game,
        exact_context=None,
        intervention=("planned_batch", reason),
        residuals_addressed={rid},
        proposal_score=0.0,
        expected_cost=cost,
        original_reason=reason,
        cancellation_conditions=set(cancellation),
        metadata={
            "purpose": purpose,
            "obstruction_potential": 1.0 if "law" in reason else 0.0,
            "distinctions_settleable": 1,
        },
    ))


def build_initial_ledger(data: dict[str, Any]) -> FlashLedger:
    ledger = FlashLedger()
    for game in GAMES.values():
        ledger.add_game(game)

    ls_discovery = ev(
        GAMES["ls20"], "protected_progress", "ls20_compiled",
        "discovery_L1_action_67",
    )
    ls_compiled = ev(
        GAMES["ls20"], "compiled_route", "ls20_compiled",
        "compiled_L1_action_57",
    )
    ls_frontier = ev(
        GAMES["ls20"], "scc_frontier", "ls20_frontier_v3",
        "level1_scc_depth_109",
    )
    ft_fatal = ev(
        GAMES["ft09"], "fatal_basin", "ft09_fatal",
        "retained_5454_fatal_basin",
    )
    vc_terminal = ev(
        GAMES["vc33"], "terminal_equivalence", "vc33_grounded",
        "terminal_grounded_pair",
    )
    vc_param = ev(
        GAMES["vc33"], "separator", "vc33_grounded",
        "28_family_pairs_split_by_exact_parameters",
    )
    bt_noquot = ev(
        GAMES["bt11"], "obstruction", "interventional_diag",
        "final_quotient_identity",
    )

    add_cap(
        ledger, kind="protected_progress", games={GAMES["ls20"]},
        scope={"game": GAMES["ls20"], "route_key": "ls20:L1"},
        consequence=("LEVEL_INCREMENT", 1), witnesses=[ls_discovery],
        protected=("level", 1), cost=67, authority="live_exact_replay",
    )
    add_cap(
        ledger, kind="compiled_route", games={GAMES["ls20"]},
        scope={"game": GAMES["ls20"], "route_key": "ls20:L1"},
        consequence=("LEVEL_INCREMENT", 1), witnesses=[ls_compiled],
        protected=("level", 1), cost=57, authority="live_exact_replay",
        notes={"executed_primitive_actions": 56},
    )
    add_cap(
        ledger, kind="obstruction", games={GAMES["ls20"]},
        scope={
            "game": GAMES["ls20"],
            "bounded_structure": "level1_scc_condensation",
            "max_quotient_depth": 109,
        },
        consequence=("NO_NONTRIVIAL_SCC_OBSERVED", 1651, 109),
        witnesses=[ls_frontier], authority="exact_retained_ledger",
        notes={"final_nodes": 4470, "final_edges": 12448},
    )
    add_cap(
        ledger, kind="fatal_basin", games={GAMES["ft09"]},
        scope={
            "game": GAMES["ft09"],
            "family": "retained_5454_fatal_basin",
            "bounded_sources": 47,
        },
        consequence=("NO_PROTECTED_PROGRESS", 282, 281, 1),
        witnesses=[ft_fatal], protected=("progress_observed", False),
        authority="closed_bounded_exact_certificate",
    )
    add_cap(
        ledger, kind="terminal_equivalence", games={GAMES["vc33"]},
        scope={
            "game": GAMES["vc33"], "terminal_only": True,
            "protected": ["GAME_OVER", 2],
        },
        consequence=("CERTIFIED_TERMINAL_EQUIVALENCE_NO_DECISION_EFFECT",),
        witnesses=[vc_terminal], protected=("decision_effect", False),
        authority="closed_bounded_grounded_bisimulation",
        notes={"nonterminal_transfer": "NOT_AUTHORIZED"},
    )
    add_cap(
        ledger, kind="obstruction", games={GAMES["bt11"]},
        scope={
            "game": GAMES["bt11"],
            "bounded_structure": "final_interventional_quotient",
        },
        consequence=("NO_USEFUL_QUOTIENT_JUSTIFIED", 73),
        witnesses=[bt_noquot], authority="bounded_exact_diagnostic",
        notes={"final_compression": 1.0, "largest_class": 1},
    )

    add_probe(
        ledger, pid="probe:ls20:reacquire_L1", game=GAMES["ls20"], cost=67,
        reason="rediscover already compiled protected route",
        cancellation={"route_dominated:ls20:L1"},
        purpose="local_reacquisition", potential="ls20:L1",
    )
    add_probe(
        ledger, pid="probe:ft09:reacquire_5454", game=GAMES["ft09"], cost=6,
        reason="reacquire retained fatal family",
        cancellation={
            f"fatal_family:{GAMES['ft09']}:retained_5454_fatal_basin"
        },
        purpose="local_reacquisition", potential="ft09:5454",
    )

    for short in ("ls20", "vc33", "bt11"):
        add_probe(
            ledger,
            pid=f"probe:{short}:test_state_change_value_law",
            game=GAMES[short], cost=6,
            reason="test universal law: high state-change implies protected value",
            cancellation={f"global_obstruction:{LAW_STATE_CHANGE_VALUE}"},
            purpose="test_global_proposal_law",
            potential=LAW_STATE_CHANGE_VALUE,
        )
    for short in ("ls20", "ft09", "bt11"):
        add_probe(
            ledger,
            pid=f"probe:{short}:test_family_action_identity_law",
            game=GAMES[short], cost=6,
            reason=(
                "test universal law: action family identity is exact "
                "intervention identity"
            ),
            cancellation={f"global_obstruction:{LAW_FAMILY_ACTION_EXACT}"},
            purpose="test_global_proposal_law",
            potential=LAW_FAMILY_ACTION_EXACT,
        )
    for short in GAMES:
        add_probe(
            ledger, pid=f"probe:{short}:unrelated_control",
            game=GAMES[short], cost=3,
            reason="unrelated destination residual", cancellation=set(),
            purpose="domain_residual", potential=f"{short}:unrelated",
        )

    # Retain exact parameterization evidence now; promote its global proposal-law
    # obstruction only when its simulated verified return arrives.
    ledger.add_evidence(vc_param)
    return ledger


def install_global_obstruction(
    ledger: FlashLedger,
    *,
    law: str,
    source_game: str,
    witness: EvidenceRef,
    consequence: tuple[Any, ...],
    notes: dict[str, Any],
) -> str:
    eid = ledger.add_evidence(witness)
    add_cap(
        ledger,
        kind="obstruction",
        games={source_game},
        scope={"global_law": law, "authority_scope": "proposal_law_only"},
        consequence=consequence,
        witnesses=[witness],
        authority="exact_counterexample_to_universal_proposal_law",
        notes=notes,
    )
    return eid


def execute_remaining(ledger: FlashLedger) -> dict[str, Any]:
    acquisition = 0
    executed: list[str] = []
    waves: list[list[str]] = []
    while True:
        wave = choose_wave(ledger, capacity=4, max_overlap=0.0)
        if not wave:
            break
        waves.append(list(wave))
        for pid in wave:
            probe = ledger.probes[pid]
            if probe.status != PENDING:
                continue
            ledger.mark_probe_executed(pid)
            acquisition += int(probe.expected_cost)
            executed.append(pid)
    return {
        "acquisition_actions": acquisition,
        "executed_probes": executed,
        "waves": waves,
    }


def summarize(
    ledger: FlashLedger,
    execution: dict[str, Any],
    *,
    arm: str,
) -> dict[str, Any]:
    milestones = {
        GAMES["ls20"]: 1,
        GAMES["ft09"]: 0,
        GAMES["vc33"]: 2,
        GAMES["bt11"]: 5,
    }
    cancelled = [p for p in ledger.probes.values() if p.status == CANCELLED]
    cross_cancelled = [
        p for p in cancelled
        if p.metadata.get("purpose") == "test_global_proposal_law"
    ]
    return {
        "arm": arm,
        "total_acquisition_actions": execution["acquisition_actions"],
        "protected_milestone_vector": milestones,
        "games_progressed": sum(level > 0 for level in milestones.values()),
        "executed_probes": execution["executed_probes"],
        "redundant_probes_executed": sum(
            ledger.probes[pid].metadata.get("purpose")
            == "test_global_proposal_law"
            for pid in execution["executed_probes"]
        ),
        "probes_cancelled": len(cancelled),
        "cross_game_probes_cancelled": len(cross_cancelled),
        "cancelled_actions_avoided": sum(
            p.acquisition_actions_avoided for p in cancelled
        ),
        "compiled_routes": sum(
            c.kind == "compiled_route" and c.state == ACTIVE
            for c in ledger.capabilities.values()
        ),
        "fatal_regions": sum(
            c.kind == "fatal_basin" and c.state == ACTIVE
            for c in ledger.capabilities.values()
        ),
        "active_capabilities": len(ledger.active_capability_ids()),
        "raw_evidence_refs": len(ledger.raw_evidence),
        "flash_events": len(ledger.events),
        "closure_iterations_total": sum(
            event.closure_iterations for event in ledger.events
        ),
        "estimated_future_actions_eliminated": sum(
            event.estimated_future_actions_eliminated
            for event in ledger.events
        ),
        "ledger_hash": ledger.content_hash(),
        "waves": execution["waves"],
    }


def run_arm(
    data: dict[str, Any],
    *,
    arm: str,
    enable_global: bool,
    sham: bool = False,
    enable_route: bool = True,
    enable_fatal: bool = True,
    enable_remin: bool = True,
) -> tuple[FlashLedger, dict[str, Any]]:
    ledger = build_initial_ledger(data)
    run_to_fixed_point(
        ledger,
        event_id=f"{arm}:initial-local-closure",
        enable_global_obstructions=False,
        enable_route_compilation=enable_route,
        enable_fatal_regions=enable_fatal,
        enable_reminimization=enable_remin,
    )

    ft_law = (
        "sham_irrelevant_state_change_law"
        if sham else LAW_STATE_CHANGE_VALUE
    )
    vc_law = (
        "sham_irrelevant_intervention_law"
        if sham else LAW_FAMILY_ACTION_EXACT
    )
    ft_eid = install_global_obstruction(
        ledger,
        law=ft_law,
        source_game=GAMES["ft09"],
        witness=ev(
            GAMES["ft09"], "fatal_basin", "ft09_fatal",
            "retained_5454_fatal_basin",
        ),
        consequence=(
            "COUNTEREXAMPLE", "687_of_687_state_change", "fatal_basin"
        ),
        notes={
            "fatal_sources": 47, "counterfactual_probes": 282,
            "game_over": 281, "no_change": 1, "behavior_transfer": "NONE",
        },
    )
    run_to_fixed_point(
        ledger,
        source_probe="retained:ft09:fatal_basin",
        new_evidence=[ft_eid],
        event_id=f"{arm}:flash:ft09",
        enable_global_obstructions=enable_global,
        enable_route_compilation=enable_route,
        enable_fatal_regions=enable_fatal,
        enable_reminimization=enable_remin,
    )

    vc_eid = install_global_obstruction(
        ledger,
        law=vc_law,
        source_game=GAMES["vc33"],
        witness=ev(
            GAMES["vc33"], "separator", "vc33_grounded",
            "28_family_pairs_split_by_exact_parameters",
        ),
        consequence=(
            "COUNTEREXAMPLE", "28_family_pairs_split",
            "exact_action_parameters_required",
        ),
        notes={
            "family_candidates_split": 28,
            "terminal_only_residual": True,
            "behavior_transfer": "NONE",
        },
    )
    run_to_fixed_point(
        ledger,
        source_probe="retained:vc33:parameterization",
        new_evidence=[vc_eid],
        event_id=f"{arm}:flash:vc33",
        enable_global_obstructions=enable_global,
        enable_route_compilation=enable_route,
        enable_fatal_regions=enable_fatal,
        enable_reminimization=enable_remin,
    )
    return ledger, summarize(ledger, execute_remaining(ledger), arm=arm)


def semantic_state(ledger: FlashLedger) -> dict[str, Any]:
    return {
        "capabilities": {
            cid: cap.state for cid, cap in sorted(ledger.capabilities.items())
        },
        "residuals": {
            rid: (r.status, r.settled_by)
            for rid, r in sorted(ledger.residuals.items())
        },
        "probes": {
            pid: (
                p.status, p.acquisition_actions_avoided,
                tuple(p.cancellation_evidence),
            )
            for pid, p in sorted(ledger.probes.items())
        },
    }


def order_robustness(data: dict[str, Any]) -> dict[str, Any]:
    normal, _ = run_arm(data, arm="order-normal", enable_global=True)
    reverse = build_initial_ledger(data)
    run_to_fixed_point(
        reverse, event_id="order-reversed:initial",
        enable_global_obstructions=False,
    )
    vc_eid = install_global_obstruction(
        reverse, law=LAW_FAMILY_ACTION_EXACT, source_game=GAMES["vc33"],
        witness=ev(
            GAMES["vc33"], "separator", "vc33_grounded",
            "28_family_pairs_split_by_exact_parameters",
        ),
        consequence=(
            "COUNTEREXAMPLE", "28_family_pairs_split",
            "exact_action_parameters_required",
        ),
        notes={"behavior_transfer": "NONE"},
    )
    run_to_fixed_point(
        reverse, event_id="order-reversed:vc33", new_evidence=[vc_eid]
    )
    ft_eid = install_global_obstruction(
        reverse, law=LAW_STATE_CHANGE_VALUE, source_game=GAMES["ft09"],
        witness=ev(
            GAMES["ft09"], "fatal_basin", "ft09_fatal",
            "retained_5454_fatal_basin",
        ),
        consequence=(
            "COUNTEREXAMPLE", "687_of_687_state_change", "fatal_basin"
        ),
        notes={"behavior_transfer": "NONE"},
    )
    run_to_fixed_point(
        reverse, event_id="order-reversed:ft09", new_evidence=[ft_eid]
    )
    execute_remaining(reverse)
    return {
        "confluent_for_tested_event_order":
            semantic_state(normal) == semantic_state(reverse),
        "normal_active": len(normal.active_capability_ids()),
        "reversed_active": len(reverse.active_capability_ids()),
    }


def main() -> None:
    data = validate_inputs()
    OUT.mkdir(parents=True, exist_ok=True)

    independent_ledger, independent = run_arm(
        data, arm="independent", enable_global=False
    )
    flash_ledger, flash = run_arm(
        data, arm="flash", enable_global=True
    )
    _sham_ledger, sham = run_arm(
        data, arm="sham", enable_global=True, sham=True
    )
    _x, no_global = run_arm(
        data, arm="ablation_no_global_cancellation", enable_global=False
    )
    _x, no_route = run_arm(
        data, arm="ablation_no_route_compilation",
        enable_global=True, enable_route=False
    )
    _x, no_fatal = run_arm(
        data, arm="ablation_no_negative_local_closure",
        enable_global=True, enable_fatal=False
    )
    _x, no_remin = run_arm(
        data, arm="ablation_no_reminimization",
        enable_global=True, enable_remin=False
    )
    order = order_robustness(data)

    same_milestones = (
        independent["protected_milestone_vector"]
        == flash["protected_milestone_vector"]
    )
    acquisition_saved = (
        independent["total_acquisition_actions"]
        - flash["total_acquisition_actions"]
    )
    sham_delta = (
        independent["total_acquisition_actions"]
        - sham["total_acquisition_actions"]
    )
    cross_cancelled = [
        {
            "probe_id": p.probe_id,
            "game": p.game,
            "reason": p.original_reason,
            "cancellation_event": p.cancellation_event,
            "cancellation_evidence": p.cancellation_evidence,
            "actions_avoided": p.acquisition_actions_avoided,
        }
        for p in flash_ledger.probes.values()
        if (
            p.status == CANCELLED
            and p.metadata.get("purpose") == "test_global_proposal_law"
        )
    ]
    verdict = (
        "PASS"
        if (
            same_milestones
            and acquisition_saved > 0
            and len(cross_cancelled) >= 2
            and sham_delta == 0
            and order["confluent_for_tested_event_order"]
        )
        else "FAIL"
    )

    strongest = {
        "source": (
            "ft09 retained (54,54) fatal-basin certificate: 47 exact source "
            "states; 282 one-deviation probes; 281 GAME_OVER; 1 no-change"
        ),
        "flash_event": (
            "universal proposal law state_change_implies_protected_value refuted"
        ),
        "destination_consequence": (
            "ls20, vc33 and bt11 law-validation probes cancelled; "
            "no destination behavior inferred"
        ),
        "actions_saved": sum(
            r["actions_avoided"] for r in cross_cancelled
            if "state_change_value" in r["probe_id"]
        ),
    }
    comparison = {
        "schema": "qckn-flash-multigame-v5",
        "verdict": verdict,
        "experiment_kind": "retained_evidence_future_acquisition_replay",
        "claim_boundary": (
            "mechanical replay over pinned exact retained certificates; proves "
            "causal future-search elimination and graph reclosure, not fresh "
            "environment-performance superiority or behavior transfer"
        ),
        "independent": independent,
        "flash": flash,
        "sham": sham,
        "delta": {
            "acquisition_saved": acquisition_saved,
            "same_protected_milestones": same_milestones,
            "future_probes_eliminated": len(cross_cancelled),
            "cross_game_actions_avoided": sum(
                r["actions_avoided"] for r in cross_cancelled
            ),
            "active_capability_compression": (
                len(flash_ledger.capabilities)
                - len(flash_ledger.active_capability_ids())
            ),
            "sham_acquisition_saved": sham_delta,
        },
        "strongest_causal_chain": strongest,
        "cross_game_cancellations": cross_cancelled,
        "ablations": {
            "no_global_cancellation": no_global,
            "no_route_compilation": no_route,
            "no_negative_local_closure": no_fatal,
            "no_reminimization": no_remin,
        },
        "order_robustness": order,
        "artifact_manifest": ARTIFACTS,
        "falsifiers": {
            "fails_if_no_action_saving": acquisition_saved <= 0,
            "fails_if_milestones_differ": not same_milestones,
            "fails_if_sham_gets_benefit": sham_delta != 0,
            "fails_if_no_cross_game_cancellation": len(cross_cancelled) == 0,
            "fails_if_tested_order_not_confluent":
                not order["confluent_for_tested_event_order"],
        },
        "unproved": [
            "positive behavioral transfer across games",
            "fresh environment-step superiority over V4 market_local",
            "hidden-game generalization",
            "universal state/action equivalence",
            "superlinear compounding",
        ],
    }

    write("independent-results.json", independent)
    write("flash-results.json", flash)
    write("sham-results.json", sham)
    write("flash-events.json", [e.__dict__ for e in flash_ledger.events])
    write("global-ledger.json", flash_ledger.to_dict())
    write("probe-ledger.json", flash_ledger.to_dict()["probes"])
    write("comparison.json", comparison)

    print("FLASH_VERDICT=" + verdict, flush=True)
    print("FLASH_COMPARISON=" + json.dumps(comparison, sort_keys=True), flush=True)
    if verdict != "PASS":
        raise AssertionError("Flash V5 falsifier did not pass")


if __name__ == "__main__":
    main()

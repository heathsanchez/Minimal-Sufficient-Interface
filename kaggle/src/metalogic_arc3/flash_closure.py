from __future__ import annotations

from collections import defaultdict
from typing import Any

from .flash_ledger import (
    ACTIVE, PENDING, SETTLED,
    FlashEvent, FlashLedger, GlobalCapability,
    canonical_json, stable_id,
)


class NonConvergentClosure(RuntimeError):
    pass


def _evidence_ids(ledger: FlashLedger, capability_id: str) -> list[str]:
    seen: set[str] = set()
    stack = [capability_id]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        for dep in ledger.provenance.get(node, set()):
            if dep.startswith("ev-"):
                seen.add(dep)
            elif dep in ledger.capabilities:
                stack.append(dep)
    return sorted(x for x in seen if x.startswith("ev-"))


def _route_key(cap: GlobalCapability) -> str | None:
    value = cap.scope.get("route_key")
    return None if value is None else str(value)


def _equivalence_key(cap: GlobalCapability) -> str:
    return canonical_json({
        "kind": cap.kind,
        "scope": cap.scope,
        "consequence_signature": cap.consequence_signature,
        "protected_effect": cap.protected_effect,
        "authority": cap.authority,
    })


def _record_once(seq: list[str], value: str) -> None:
    if value not in seq:
        seq.append(value)


def _compress_duplicate_capabilities(ledger: FlashLedger, event: FlashEvent) -> bool:
    changed = False
    groups: dict[str, list[GlobalCapability]] = defaultdict(list)
    for cap in ledger.capabilities.values():
        if cap.state == ACTIVE and cap.kind != "separator":
            groups[_equivalence_key(cap)].append(cap)
    for rows in groups.values():
        if len(rows) < 2:
            continue
        rows.sort(key=lambda c: (c.acquisition_cost, c.capability_id))
        keeper = rows[0]
        for cap in rows[1:]:
            if ledger.reserve_capability(cap.capability_id):
                _record_once(event.capabilities_reserved, cap.capability_id)
                event.estimated_future_actions_eliminated += max(
                    0, int(cap.acquisition_cost) - int(keeper.acquisition_cost)
                )
                changed = True
    return changed


def _compile_shortest_routes(ledger: FlashLedger, event: FlashEvent) -> bool:
    changed = False
    groups: dict[str, list[GlobalCapability]] = defaultdict(list)
    for cap in ledger.capabilities.values():
        if cap.state != ACTIVE or cap.kind not in ("compiled_route", "protected_progress"):
            continue
        key = _route_key(cap)
        if key is not None:
            groups[key].append(cap)

    for key, rows in groups.items():
        rows.sort(key=lambda c: (c.acquisition_cost, c.capability_id))
        best = rows[0]
        if best.kind == "protected_progress":
            cid = stable_id("cap", {
                "kind": "compiled_route",
                "route_key": key,
                "source": best.capability_id,
                "cost": best.acquisition_cost,
            })
            if cid not in ledger.capabilities:
                compiled = GlobalCapability(
                    capability_id=cid,
                    kind="compiled_route",
                    source_games=set(best.source_games),
                    scope={**best.scope, "compiled_from": best.capability_id},
                    consequence_signature=best.consequence_signature,
                    exact_witnesses=list(best.exact_witnesses),
                    protected_effect=best.protected_effect,
                    acquisition_cost=int(best.acquisition_cost),
                    authority=best.authority,
                    destination_status=dict(best.destination_status),
                    dependencies={best.capability_id},
                    notes={"generated_by": "flash_route_compilation"},
                )
                ledger.add_capability(compiled)
                _record_once(event.capabilities_promoted, cid)
                _record_once(event.routes_compiled, cid)
                if ledger.reserve_capability(best.capability_id):
                    _record_once(event.capabilities_reserved, best.capability_id)
                changed = True
                best = compiled

        for cap in list(ledger.capabilities.values()):
            if (
                cap.state == ACTIVE
                and cap.capability_id != best.capability_id
                and cap.kind in ("compiled_route", "protected_progress")
                and _route_key(cap) == key
                and int(cap.acquisition_cost) > int(best.acquisition_cost)
            ):
                saving = int(cap.acquisition_cost) - int(best.acquisition_cost)
                if ledger.reserve_capability(cap.capability_id):
                    _record_once(event.capabilities_reserved, cap.capability_id)
                    event.estimated_future_actions_eliminated += saving
                    changed = True

        token = f"route_dominated:{key}"
        evidence = _evidence_ids(ledger, best.capability_id)
        for probe in ledger.probes.values():
            if probe.status == PENDING and token in probe.cancellation_conditions:
                if ledger.cancel_probe(
                    probe.probe_id, event_id=event.event_id, evidence_ids=evidence
                ):
                    _record_once(event.probes_cancelled, probe.probe_id)
                    event.estimated_future_actions_eliminated += probe.expected_cost
                    changed = True
    return changed


def _apply_fatal_regions(ledger: FlashLedger, event: FlashEvent) -> bool:
    """Fatal closure is exact-scope only; it never transfers destination authority."""
    changed = False
    for cap in sorted(ledger.capabilities.values(), key=lambda c: c.capability_id):
        if cap.state != ACTIVE or cap.kind != "fatal_basin":
            continue
        family = cap.scope.get("family")
        game = cap.scope.get("game")
        if not family or not game:
            continue
        token = f"fatal_family:{game}:{family}"
        evidence = _evidence_ids(ledger, cap.capability_id)
        for probe in ledger.probes.values():
            if (
                probe.status == PENDING
                and probe.game == game
                and token in probe.cancellation_conditions
            ):
                if ledger.cancel_probe(
                    probe.probe_id, event_id=event.event_id, evidence_ids=evidence
                ):
                    _record_once(event.probes_cancelled, probe.probe_id)
                    event.estimated_future_actions_eliminated += probe.expected_cost
                    changed = True
        _record_once(event.fatal_regions_added, cap.capability_id)
    return changed


def _apply_global_obstructions(ledger: FlashLedger, event: FlashEvent) -> bool:
    """Cancel only tests of a now-refuted universal proposal law.

    Source evidence may invalidate a representation/search law globally, but
    never installs or skips an unverified behavioral consequence in another
    destination game.
    """
    changed = False
    for cap in sorted(ledger.capabilities.values(), key=lambda c: c.capability_id):
        if cap.state != ACTIVE or cap.kind != "obstruction":
            continue
        law = cap.scope.get("global_law")
        if not law:
            continue
        token = f"global_obstruction:{law}"
        evidence = _evidence_ids(ledger, cap.capability_id)
        for probe in ledger.probes.values():
            if (
                probe.status == PENDING
                and token in probe.cancellation_conditions
                and probe.metadata.get("purpose") == "test_global_proposal_law"
            ):
                if ledger.cancel_probe(
                    probe.probe_id, event_id=event.event_id, evidence_ids=evidence
                ):
                    _record_once(event.probes_cancelled, probe.probe_id)
                    event.estimated_future_actions_eliminated += probe.expected_cost
                    changed = True
    return changed


def _apply_destination_transfer_results(ledger: FlashLedger, event: FlashEvent) -> bool:
    changed = False
    for cap in sorted(ledger.capabilities.values(), key=lambda c: c.capability_id):
        if cap.state != ACTIVE:
            continue

        if cap.kind == "transferable_capability_candidate":
            _record_once(event.transfer_proposals_created, cap.capability_id)

        elif cap.kind == "destination_verified_transfer":
            destination = str(cap.scope.get("destination_game", ""))
            transfer_key = str(cap.scope.get("transfer_key", ""))
            if not destination or not transfer_key:
                continue
            _record_once(event.transfer_proposals_verified, cap.capability_id)
            for residual_id in cap.scope.get("settles_residuals", []):
                if residual_id in ledger.residuals:
                    if ledger.settle_residual(residual_id, cap.capability_id):
                        _record_once(event.residuals_settled, residual_id)
                        changed = True
            token = f"transfer_verified:{destination}:{transfer_key}"
            evidence = _evidence_ids(ledger, cap.capability_id)
            for probe in ledger.probes.values():
                if (
                    probe.status == PENDING
                    and probe.game == destination
                    and token in probe.cancellation_conditions
                ):
                    if ledger.cancel_probe(
                        probe.probe_id, event_id=event.event_id, evidence_ids=evidence
                    ):
                        _record_once(event.probes_cancelled, probe.probe_id)
                        event.estimated_future_actions_eliminated += probe.expected_cost
                        changed = True

        elif cap.kind == "destination_refuted_transfer":
            destination = str(cap.scope.get("destination_game", ""))
            transfer_key = str(cap.scope.get("transfer_key", ""))
            _record_once(event.transfer_proposals_refuted, cap.capability_id)
            obstruction_id = stable_id("cap", {
                "kind": "obstruction",
                "transfer_key": transfer_key,
                "destination": destination,
                "source": cap.capability_id,
            })
            if obstruction_id not in ledger.capabilities:
                obstruction = GlobalCapability(
                    capability_id=obstruction_id,
                    kind="obstruction",
                    source_games=set(cap.source_games) | ({destination} if destination else set()),
                    scope={
                        "transfer_key": transfer_key,
                        "destination_game": destination,
                        "refutes_transfer": True,
                    },
                    consequence_signature=("TRANSFER_REFUTED", transfer_key, destination),
                    exact_witnesses=list(cap.exact_witnesses),
                    protected_effect=None,
                    acquisition_cost=0,
                    authority=cap.authority,
                    dependencies={cap.capability_id},
                    notes={"generated_by": "destination_transfer_refutation"},
                )
                ledger.add_capability(obstruction)
                _record_once(event.capabilities_promoted, obstruction_id)
                changed = True
    return changed


def _apply_separators(ledger: FlashLedger, event: FlashEvent) -> bool:
    changed = False
    for cap in sorted(ledger.capabilities.values(), key=lambda c: c.capability_id):
        if cap.state != ACTIVE or cap.kind != "separator":
            continue
        target = cap.scope.get("revokes_capability_id")
        if target and target in ledger.capabilities:
            if ledger.revoke_capability(str(target)):
                _record_once(event.capabilities_revoked, str(target))
                _record_once(event.quotients_split, str(target))
                changed = True
    return changed


def _cancel_settled_residual_probes(ledger: FlashLedger, event: FlashEvent) -> bool:
    changed = False
    for probe in ledger.probes.values():
        if probe.status != PENDING or not probe.residuals_addressed:
            continue
        if all(
            rid in ledger.residuals and ledger.residuals[rid].status == SETTLED
            for rid in probe.residuals_addressed
        ):
            evidence: list[str] = []
            for rid in sorted(probe.residuals_addressed):
                cap_id = ledger.residuals[rid].settled_by
                if cap_id:
                    evidence.extend(_evidence_ids(ledger, cap_id))
            if ledger.cancel_probe(
                probe.probe_id, event_id=event.event_id, evidence_ids=evidence
            ):
                _record_once(event.probes_cancelled, probe.probe_id)
                event.estimated_future_actions_eliminated += probe.expected_cost
                changed = True
    return changed


def run_to_fixed_point(
    ledger: FlashLedger,
    *,
    source_probe: str | None = None,
    new_evidence: list[str] | None = None,
    event_id: str | None = None,
    max_iterations: int = 32,
    enable_route_compilation: bool = True,
    enable_fatal_regions: bool = True,
    enable_global_obstructions: bool = True,
    enable_transfer: bool = True,
    enable_reminimization: bool = True,
) -> FlashEvent:
    if event_id is None:
        event_id = stable_id("flash", {
            "source_probe": source_probe,
            "new_evidence": sorted(new_evidence or []),
            "event_index": len(ledger.events),
        })
    event = FlashEvent(
        event_id=event_id,
        source_probe=source_probe,
        new_evidence=sorted(new_evidence or []),
        active_capabilities_before=len(ledger.active_capability_ids()),
    )

    rules = [_apply_separators]
    if enable_route_compilation:
        rules.append(_compile_shortest_routes)
    if enable_fatal_regions:
        rules.append(_apply_fatal_regions)
    if enable_global_obstructions:
        rules.append(_apply_global_obstructions)
    if enable_transfer:
        rules.append(_apply_destination_transfer_results)
    rules.append(_cancel_settled_residual_probes)
    if enable_reminimization:
        rules.append(_compress_duplicate_capabilities)

    for iteration in range(1, max_iterations + 1):
        changed = False
        for rule in rules:
            changed = bool(rule(ledger, event)) or changed
        event.closure_iterations = iteration
        if not changed:
            break
    else:
        raise NonConvergentClosure(
            f"flash closure did not converge within {max_iterations} iterations"
        )

    event.active_capabilities_after = len(ledger.active_capability_ids())
    ledger.events.append(event)
    return event

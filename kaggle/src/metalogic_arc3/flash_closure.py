from __future__ import annotations

from collections import defaultdict
from typing import Any

from .flash_ledger import FlashEvent, GlobalCapability, GlobalLedger

MAX_CLOSURE_ITERATIONS = 64


def _next_event_id(ledger: GlobalLedger) -> str:
    return f'flash-{len(ledger.events)+1:06d}'


def _promote_route_minima(ledger: GlobalLedger, event: FlashEvent) -> bool:
    changed = False
    groups: dict[tuple[Any, ...], list[GlobalCapability]] = defaultdict(list)
    for cap in ledger.capabilities.values():
        if cap.kind != 'compiled_route' or cap.state == 'REVOKED':
            continue
        key = (tuple(sorted(cap.source_games)), tuple(cap.protected_effect or ()), str(sorted(cap.scope.items())))
        groups[key].append(cap)
    for caps in groups.values():
        caps.sort(key=lambda c: (c.acquisition_cost, c.capability_id))
        champion = caps[0]
        if champion.state != 'ACTIVE':
            champion.state = 'ACTIVE'
            changed = True
        for loser in caps[1:]:
            if loser.state == 'ACTIVE':
                loser.state = 'RESERVE'
                changed = True
        if len(caps) > 1 and champion.capability_id not in event.routes_compiled:
            event.routes_compiled.append(champion.capability_id)
    return changed


def _apply_separators(ledger: GlobalLedger, event: FlashEvent) -> bool:
    changed = False
    for sep in list(ledger.capabilities.values()):
        if sep.kind != 'separator' or sep.state != 'ACTIVE':
            continue
        target = sep.notes.get('revokes')
        if target and target in ledger.capabilities and ledger.capabilities[target].state != 'REVOKED':
            ledger.revoke_capability(target, reason=f'separated by {sep.capability_id}')
            event.capabilities_revoked.append(target)
            event.quotients_split.append(target)
            changed = True
    return changed


def _close_residuals(ledger: GlobalLedger) -> bool:
    changed = False
    active_tokens = set()
    for cap in ledger.active_capabilities():
        active_tokens.update(str(x) for x in cap.notes.get('settles_residuals', ()))
    for residual in ledger.residuals.values():
        if residual.status == 'OPEN' and residual.residual_id in active_tokens:
            residual.status = 'SETTLED'
            changed = True
    return changed


def _cancel_by_certificates(ledger: GlobalLedger, event: FlashEvent) -> bool:
    changed = False
    active_tokens = set()
    for cap in ledger.active_capabilities():
        active_tokens.add(f'capability:{cap.capability_id}')
        for token in cap.notes.get('settles_tokens', ()):
            active_tokens.add(str(token))
    for probe in sorted(ledger.probes.values(), key=lambda p: p.probe_id):
        if probe.status != 'PENDING':
            continue
        matched = sorted(probe.cancellation_conditions & active_tokens)
        if not matched:
            continue
        saved = ledger.cancel_probe(probe.probe_id, evidence=matched[0], event_id=event.event_id)
        if saved:
            event.probes_cancelled.append(probe.probe_id)
            event.estimated_future_actions_eliminated += saved
            changed = True
    return changed


def _reminimize(ledger: GlobalLedger) -> bool:
    changed = False
    by_sig: dict[tuple[Any, ...], list[GlobalCapability]] = defaultdict(list)
    for cap in ledger.capabilities.values():
        if cap.state == 'REVOKED':
            continue
        key = (cap.kind, tuple(cap.consequence_signature), str(sorted(cap.scope.items())))
        by_sig[key].append(cap)
    for caps in by_sig.values():
        caps.sort(key=lambda c: (c.acquisition_cost, c.capability_id))
        for i, cap in enumerate(caps):
            wanted = 'ACTIVE' if i == 0 else 'RESERVE'
            if cap.state != wanted:
                cap.state = wanted
                changed = True
    return changed


def run_to_fixed_point(
    ledger: GlobalLedger,
    *,
    source_probe: str | None = None,
    new_evidence: list[str] | None = None,
) -> FlashEvent:
    event = FlashEvent(
        event_id=_next_event_id(ledger),
        source_probe=source_probe,
        new_evidence=list(new_evidence or []),
    )
    for iteration in range(1, MAX_CLOSURE_ITERATIONS + 1):
        changed = False
        changed |= _promote_route_minima(ledger, event)
        changed |= _apply_separators(ledger, event)
        changed |= _close_residuals(ledger)
        changed |= _cancel_by_certificates(ledger, event)
        changed |= _reminimize(ledger)
        event.closure_iterations = iteration
        if not changed:
            ledger.events.append(event)
            ledger.assert_provenance()
            return event
    raise RuntimeError('Flash closure failed to converge')


def validate_transfer_result(
    ledger: GlobalLedger,
    *,
    source_capability_id: str,
    destination_game: str,
    destination_evidence_id: str,
    verified: bool,
    exact_scope: dict[str, Any] | None = None,
    settles_tokens: list[str] | None = None,
) -> GlobalCapability:
    source = ledger.capabilities[source_capability_id]
    if destination_evidence_id not in ledger.raw_evidence:
        raise KeyError('destination evidence must already exist in raw authority bank')
    ref = ledger.raw_evidence[destination_evidence_id]
    if ref.game != destination_game:
        raise ValueError('destination authority game mismatch')
    suffix = 'verified' if verified else 'refuted'
    cid = f'transfer:{source_capability_id}:{destination_game}:{suffix}'
    source_game = sorted(source.source_games)[0]
    cap = GlobalCapability(
        capability_id=cid,
        kind='destination_verified_transfer' if verified else 'destination_refuted_transfer',
        source_games={source_game, destination_game},
        scope=dict(exact_scope or {}),
        consequence_signature=tuple(source.consequence_signature) + (suffix,),
        exact_witnesses=list(source.exact_witnesses) + [ref],
        protected_effect=source.protected_effect if verified else None,
        acquisition_cost=0,
        destination_status={destination_game: suffix},
        dependencies={source_capability_id},
        notes={'settles_tokens': list(settles_tokens or [])},
    )
    ledger.add_capability(cap)
    source.destination_status[destination_game] = suffix
    return cap

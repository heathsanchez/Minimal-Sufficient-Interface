from __future__ import annotations

from collections import defaultdict
import hashlib
import json
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


def transfer_obstruction_key(
    ledger: GlobalLedger,
    *,
    source_capability_id: str,
    destination_game: str,
    exact_scope: dict[str, Any] | None = None,
) -> str:
    source = ledger.capabilities[source_capability_id]
    payload = {
        'schema': 'qckn-consequence-transfer-refutation-v2',
        'source_kind': source.kind,
        'source_games': sorted(source.source_games),
        'source_scope': dict(source.scope),
        'source_consequence_signature': source.consequence_signature,
        'source_protected_effect': source.protected_effect,
        'destination_game': destination_game,
        'exact_scope': dict(exact_scope or {}),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':'), default=str).encode()
    return 'transfer-obstruction:' + hashlib.sha256(raw).hexdigest()


def transfer_proposal_blocked(
    ledger: GlobalLedger,
    *,
    source_capability_id: str,
    destination_game: str,
    exact_scope: dict[str, Any] | None = None,
) -> bool:
    key = transfer_obstruction_key(
        ledger,
        source_capability_id=source_capability_id,
        destination_game=destination_game,
        exact_scope=exact_scope,
    )
    row = ledger.obstructions.get(key)
    return bool(row and row.get('kind') == 'exact_transfer_refutation')


def _evidence_ref_payload(ref: Any) -> dict[str, Any]:
    return {
        'game': ref.game,
        'kind': ref.kind,
        'artifact_or_run': ref.artifact_or_run,
        'local_key': ref.local_key,
        'sha256': ref.sha256,
    }


def export_compiled_transfer_obstructions(ledger: GlobalLedger) -> str:
    rows: list[dict[str, Any]] = []
    for obstruction_key, row in sorted(ledger.obstructions.items()):
        if row.get('kind') != 'exact_transfer_refutation':
            continue
        evidence_id = row.get('destination_evidence_id')
        if evidence_id not in ledger.raw_evidence:
            raise ValueError('compiled obstruction missing destination evidence')
        rows.append({
            'obstruction_key': obstruction_key,
            'kind': 'exact_transfer_refutation',
            'source_capability_id': row['source_capability_id'],
            'source_consequence_signature': list(row['source_consequence_signature']),
            'destination_game': row['destination_game'],
            'exact_scope': dict(row.get('exact_scope') or {}),
            'destination_evidence_id': evidence_id,
            'destination_evidence': _evidence_ref_payload(
                ledger.raw_evidence[evidence_id]
            ),
            'capability_id': row.get('capability_id'),
        })
    payload = {
        'schema': 'qckn-transfer-obstructions-v1',
        'obstructions': rows,
    }
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=True,
    ) + '\n'


def import_compiled_transfer_obstructions(
    ledger: GlobalLedger,
    text: str,
) -> int:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError('invalid compiled obstruction present') from exc
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=True,
    ) + '\n'
    if canonical != text:
        raise ValueError('noncanonical compiled obstruction present')
    if payload.get('schema') != 'qckn-transfer-obstructions-v1':
        raise ValueError('compiled obstruction schema mismatch')
    rows = payload.get('obstructions')
    if not isinstance(rows, list):
        raise ValueError('compiled obstruction rows missing')

    imported = 0
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or row.get('kind') != 'exact_transfer_refutation':
            raise ValueError('invalid compiled obstruction row')
        source_id = str(row.get('source_capability_id') or '')
        if source_id not in ledger.capabilities:
            raise ValueError('compiled obstruction source capability missing')
        source = ledger.capabilities[source_id]
        if list(source.consequence_signature) != list(row.get('source_consequence_signature') or []):
            raise ValueError('compiled obstruction source consequence mismatch')

        destination_game = str(row.get('destination_game') or '')
        exact_scope = dict(row.get('exact_scope') or {})
        expected_key = transfer_obstruction_key(
            ledger,
            source_capability_id=source_id,
            destination_game=destination_game,
            exact_scope=exact_scope,
        )
        obstruction_key = str(row.get('obstruction_key') or '')
        if obstruction_key != expected_key or obstruction_key in seen:
            raise ValueError('compiled obstruction key mismatch')
        seen.add(obstruction_key)

        evidence_id = str(row.get('destination_evidence_id') or '')
        current_ref = ledger.raw_evidence.get(evidence_id)
        if current_ref is None:
            raise ValueError('destination evidence mismatch')
        if _evidence_ref_payload(current_ref) != row.get('destination_evidence'):
            raise ValueError('destination evidence mismatch')
        if current_ref.game != destination_game:
            raise ValueError('destination evidence mismatch')

        ledger.obstructions[obstruction_key] = {
            'kind': 'exact_transfer_refutation',
            'source_capability_id': source_id,
            'source_consequence_signature': list(source.consequence_signature),
            'destination_game': destination_game,
            'exact_scope': exact_scope,
            'destination_evidence_id': evidence_id,
            'capability_id': row.get('capability_id'),
        }
        imported += 1
    return imported


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
    if not verified:
        obstruction_key = transfer_obstruction_key(
            ledger,
            source_capability_id=source_capability_id,
            destination_game=destination_game,
            exact_scope=exact_scope,
        )
        ledger.obstructions[obstruction_key] = {
            'kind': 'exact_transfer_refutation',
            'source_capability_id': source_capability_id,
            'source_consequence_signature': list(source.consequence_signature),
            'destination_game': destination_game,
            'exact_scope': dict(exact_scope or {}),
            'destination_evidence_id': destination_evidence_id,
            'capability_id': cap.capability_id,
        }
    return cap

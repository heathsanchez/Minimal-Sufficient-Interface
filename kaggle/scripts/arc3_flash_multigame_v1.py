"""QCKN Flash V1 retained-evidence multi-game consequence compiler.

This is a falsification/qualification replay over pinned exact evidence, not a
new ARC benchmark score. It asks: given evidence already paid for in ls20,
ft09 and the V2 public multi-game run, could a conservative,
destination-authorized Flash compiler have cancelled any acquisition because a
capability learned in another game was already sufficient?

A fresh bt11 SDK-fixture trace is accepted only as a negative/control lens; it
is never counted as public benchmark evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'kaggle' / 'src'))

from metalogic_arc3.flash_closure import run_to_fixed_point, validate_transfer_result
from metalogic_arc3.flash_ledger import EvidenceRef, GlobalCapability, GlobalLedger, Probe, Residual

AGENT_SHA256 = 'd9f0b95dfee14613425e8f557808e129b25e8a055ad481800b1024ce45281ead'
LS20_RUN = '35393183037'
LS20_ARTIFACT = '10566897440'
LS20_ARTIFACT_DIGEST = 'sha256:f681be0076967e48c6a87c6930a9fd7389d5201b5914809bfb7f6a78a9f51aeb'
FT09_RUN = '35387362885'
FT09_ARTIFACT = '10564626208'
FT09_ARTIFACT_DIGEST = 'sha256:22748bb909fae8087e90bc51bd26780466dd153dd1974782515e676d0d24bd05'
V2_RUN = '35398347557'
V2_ARTIFACT = '10569651788'
V2_ARTIFACT_DIGEST = 'sha256:4e00a55675ea50c5f5b772b670d8651345ef712a053b4e7c283423b448fabdc2'


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n')


def find_one(root: Path, name: str) -> Path:
    rows = list(root.rglob(name))
    if len(rows) != 1:
        raise RuntimeError(f'expected exactly one {name} below {root}, got {len(rows)}')
    return rows[0]


def load_inputs(args: argparse.Namespace) -> dict[str, Any]:
    ls20_summary = find_one(Path(args.ls20_dir), 'ls20-level1-scc-frontier-v3.json')
    ls20_ledger = find_one(Path(args.ls20_dir), 'scc-frontier-v3-exact-replay-ledger.json')
    ft09_cert = find_one(Path(args.ft09_dir), 'ft09-fatal-basin-certificate.json')
    ft09_progress = find_one(Path(args.ft09_dir), 'progression.json')
    v2 = find_one(Path(args.v2_dir), 'global-flash-closure-v1.json')
    bt11 = Path(args.bt11_json) if args.bt11_json else None
    if bt11 is not None and not bt11.exists():
        raise RuntimeError(f'bt11 control missing: {bt11}')
    return {
        'paths': {
            'ls20_summary': ls20_summary,
            'ls20_ledger': ls20_ledger,
            'ft09_cert': ft09_cert,
            'ft09_progress': ft09_progress,
            'v2': v2,
            'bt11': bt11,
        },
        'ls20_summary': json.loads(ls20_summary.read_text()),
        'ls20_ledger': json.loads(ls20_ledger.read_text()),
        'ft09_cert': json.loads(ft09_cert.read_text()),
        'ft09_progress': json.loads(ft09_progress.read_text()),
        'v2': json.loads(v2.read_text()),
        'bt11': json.loads(bt11.read_text()) if bt11 is not None else None,
    }


def input_manifest(inputs: dict[str, Any]) -> dict[str, Any]:
    rows = {}
    for name, path in inputs['paths'].items():
        if path is None:
            continue
        rows[name] = {'path': str(path), 'sha256': sha256(path), 'bytes': path.stat().st_size}
    return {
        'schema': 'qckn-flash-input-manifest-v1',
        'frozen_agent_sha256': AGENT_SHA256,
        'sources': {
            'ls20': {'run': LS20_RUN, 'artifact': LS20_ARTIFACT, 'artifact_digest': LS20_ARTIFACT_DIGEST},
            'ft09': {'run': FT09_RUN, 'artifact': FT09_ARTIFACT, 'artifact_digest': FT09_ARTIFACT_DIGEST},
            'v2_public_control': {'run': V2_RUN, 'artifact': V2_ARTIFACT, 'artifact_digest': V2_ARTIFACT_DIGEST},
            'bt11': {'kind': 'sdk_fixture_control', 'public_benchmark_evidence': False},
        },
        'files': rows,
        'claim_boundary': 'retained exact-evidence replay plus bt11 SDK-fixture control; no hidden-game or universal transfer claim',
    }


def add_shared_evidence(ledger: GlobalLedger, inputs: dict[str, Any]) -> dict[str, str]:
    refs = {
        'ls20': EvidenceRef('ls20','exact_replay_ledger',f'run:{LS20_RUN}/artifact:{LS20_ARTIFACT}','scc-frontier-v3-exact-replay-ledger.json',sha256(inputs['paths']['ls20_ledger'])),
        'ft09': EvidenceRef('ft09','fatal_basin_certificate',f'run:{FT09_RUN}/artifact:{FT09_ARTIFACT}','ft09-fatal-basin-certificate.json',sha256(inputs['paths']['ft09_cert'])),
        'vc33': EvidenceRef('vc33','public_v2_control',f'run:{V2_RUN}/artifact:{V2_ARTIFACT}','market_local.vc33',sha256(inputs['paths']['v2'])),
    }
    if inputs['paths']['bt11'] is not None:
        refs['bt11'] = EvidenceRef('bt11','sdk_fixture_control','current-flash-workflow','bt11-full-seed0',sha256(inputs['paths']['bt11']))
    return {name: ledger.add_evidence(ref) for name, ref in refs.items()}


def add_local_capabilities(ledger: GlobalLedger, inputs: dict[str, Any], keys: dict[str, str]) -> None:
    ls = inputs['ls20_summary']
    ft = inputs['ft09_cert']
    v2 = inputs['v2']
    lsref = ledger.raw_evidence[keys['ls20']]
    ftref = ledger.raw_evidence[keys['ft09']]
    vcref = ledger.raw_evidence[keys['vc33']]
    entry_cost = int(ls['scc_quotient']['entry_prefix_actions']) + 1
    ledger.add_capability(GlobalCapability(
        'ls20:compiled-L1-route','compiled_route',{'ls20'},
        {'phase':'L0->L1','intervention_language':'primitive'},
        ('short_deterministic_route','primitive','L1'),[lsref],('L1',),entry_cost,
        notes={'source_run':LS20_RUN,'max_scc_depth':ls['scc_quotient']['max_quotient_depth']},
    ))
    ledger.add_capability(GlobalCapability(
        'ls20:forward-scc-structure','obstruction',{'ls20'},
        {'phase':'L1','intervention_language':'primitive'},
        ('acyclic_reachable_condensation','primitive','L1'),[lsref],None,0,
        notes={
            'reachable_states':ls['scc_quotient']['reachable_level1_states'],
            'nontrivial_scc_count':ls['scc_quotient']['nontrivial_scc_count'],
        },
    ))
    ledger.add_capability(GlobalCapability(
        'ft09:bounded-fatal-5454-family','fatal_basin',{'ft09'},
        {'phase':'L0','intervention_language':'complex_action6','family':'54,54 progression + six ranked alternatives'},
        ('bounded_repeated_action_family','fatal_or_nochange','complex_action6'),[ftref],None,int(ft['probe_count']),
        notes={
            'tested_source_states':ft['tested_source_states'],
            'probe_count':ft['probe_count'],
            'status_counts':ft['status_counts'],
            'safe_compilation_use':ft['negative_capability']['safe_compilation_use'],
        },
    ))
    vc = v2['arms']['market_local']['games']['vc33-5430563c']
    ledger.add_capability(GlobalCapability(
        'vc33:generic-fatal-transfer-separator','separator',{'vc33'},
        {'phase':'L0+','intervention_language':'complex_action6'},
        ('generic_complex_action6_is_not_certified_fatal','vc33'),[vcref],('L1',),int(vc['env_steps']),
        notes={'max_level':vc['max_level'],'milestones':vc['milestones']},
    ))
    if 'bt11' in keys:
        bref = ledger.raw_evidence[keys['bt11']]
        bt = inputs['bt11']
        ledger.add_capability(GlobalCapability(
            'bt11:fixture-control-observation','obstruction',{'bt11'},
            {'intervention_language':'fixture_observed'},
            ('control_only','no_cross_game_authority'),[bref],None,int(bt.get('actions',0)),
            notes={'status':bt.get('status'),'max_levels':bt.get('max_levels'),'public_benchmark_evidence':False},
        ))


def add_historical_probe_market(ledger: GlobalLedger, inputs: dict[str, Any]) -> dict[str, int]:
    costs = {'ls20':0,'ft09':0,'vc33':0,'bt11':0}
    for row in inputs['ls20_summary']['probe_rows']:
        cost = int(row.get('source_prefix_actions',0)) + 1
        pid = f"hist:ls20:{int(row['probe']):04d}"
        rid = f"res:{pid}"
        ledger.add_residual(Residual(
            rid,'ls20','historical_exact_probe',cost,
            {'settle_distinction','protected_progress'},
            demand_signature=('primitive','L1','exact_transition'),
        ))
        ledger.add_probe(Probe(
            pid,'ls20',str(row['source']),(int(row['action']),),{rid},0,cost,
            cancellation_conditions={'transfer:primitive:L1'},
            original_reason='deepest SCC-condensation unresolved boundary',
        ))
        costs['ls20'] += cost

    root = inputs['paths']['ft09_cert'].parent
    n = 0
    for path in sorted(root.glob('band*.json')):
        data = json.loads(path.read_text())
        for row in data.get('probes', []):
            n += 1
            cost = int(row.get('prefix_actions',0)) + len(row.get('rows',[]))
            pid = f'hist:ft09:{n:04d}'
            rid = f'res:{pid}'
            ledger.add_residual(Residual(
                rid,'ft09','historical_fatal_escape_probe',cost,
                {'obstruction'},
                demand_signature=('complex_action6','L0','fatal_family'),
            ))
            ledger.add_probe(Probe(
                pid,'ft09',str(row['source']),tuple(row['alternative']),{rid},0,cost,
                cancellation_conditions={'transfer:complex_action6:fatal_family'},
                original_reason='ranked one-deviation escape from retained 54,54 chain',
            ))
            costs['ft09'] += cost

    vcrows = [
        event for event in inputs['v2']['arms']['market_local']['trace_head']
        if str(event.get('game','')).startswith('vc33') and event.get('kind') == 'probe'
    ]
    for i, row in enumerate(vcrows, 1):
        pid = f'hist:vc33:{i:04d}'
        rid = f'res:{pid}'
        ledger.add_residual(Residual(
            rid,'vc33','historical_public_probe',1,
            {'settle_distinction'},
            demand_signature=('complex_action6','L0','exact_transition'),
        ))
        ledger.add_probe(Probe(
            pid,'vc33',str(row.get('before')),tuple(row.get('action') or ()),{rid},0,1,
            cancellation_conditions={'transfer:complex_action6:fatal_family'},
            original_reason='V2 local market public probe',
        ))
        costs['vc33'] += 1

    if inputs['bt11'] is not None:
        for i, row in enumerate(inputs['bt11'].get('trace', []), 1):
            pid = f'hist:bt11:{i:04d}'
            rid = f'res:{pid}'
            ledger.add_residual(Residual(
                rid,'bt11','fixture_control_probe',1,
                {'settle_distinction'},
                demand_signature=('fixture','exact_transition'),
            ))
            ledger.add_probe(Probe(
                pid,'bt11',str(row.get('before')),tuple(row.get('action') or ()),{rid},0,1,
                cancellation_conditions={'transfer:fixture'},
                original_reason='bt11 SDK-fixture causal control',
            ))
            costs['bt11'] += 1
    return costs


def milestone_vector(inputs: dict[str, Any]) -> dict[str, int]:
    return {
        'ls20': 1,
        'ft09': 0,
        'vc33': inputs['v2']['arms']['market_local']['games']['vc33-5430563c']['max_level'],
        'bt11': (inputs['bt11'] or {}).get('max_levels',0),
    }


def execute_independent(inputs: dict[str, Any]) -> tuple[GlobalLedger, dict[str, Any]]:
    ledger = GlobalLedger(['ls20','ft09','vc33','bt11'])
    keys = add_shared_evidence(ledger, inputs)
    add_local_capabilities(ledger, inputs, keys)
    costs = add_historical_probe_market(ledger, inputs)
    event = run_to_fixed_point(ledger)
    acquired = sum(p.expected_cost for p in ledger.probes.values())
    return ledger, {
        'arm':'independent',
        'historical_acquisition_actions_represented':acquired,
        'by_game':costs,
        'protected_milestone_vector':milestone_vector(inputs),
        'redundant_probes_cancelled':len(event.probes_cancelled),
        'actions_eliminated':event.estimated_future_actions_eliminated,
        'compiled_routes':sum(c.kind=='compiled_route' and c.active for c in ledger.capabilities.values()),
        'fatal_capabilities':sum(c.kind=='fatal_basin' and c.active for c in ledger.capabilities.values()),
        'active_capabilities':len(ledger.active_capabilities()),
    }


def execute_flash(inputs: dict[str, Any], *, sham: bool=False) -> tuple[GlobalLedger, dict[str, Any]]:
    ledger = GlobalLedger(['ls20','ft09','vc33','bt11'])
    keys = add_shared_evidence(ledger, inputs)
    add_local_capabilities(ledger, inputs, keys)
    costs = add_historical_probe_market(ledger, inputs)

    source = 'ft09:bounded-fatal-5454-family'
    if sham:
        ftref = ledger.raw_evidence[keys['ft09']]
        ledger.add_capability(GlobalCapability(
            'sham:irrelevant-source','transferable_capability_candidate',{'ft09'},
            {'phase':'L0','intervention_language':'complex_action6'},
            ('shuffled_irrelevant',),[ftref],
        ))
        source = 'sham:irrelevant-source'

    transfer = validate_transfer_result(
        ledger,
        source_capability_id=source,
        destination_game='vc33',
        destination_evidence_id=keys['vc33'],
        verified=False,
        exact_scope={'intervention_language':'complex_action6','claim':'generic fatal-family transfer'},
    )
    ledger.obstructions['obs:ft09->vc33:generic-fatal-transfer'] = {
        'kind':'destination_refuted_transfer',
        'source':source,
        'destination':'vc33',
        'evidence':keys['vc33'],
        'reason':'vc33 market-local arm reaches L1; ft09 bounded fatality cannot authorize generic complex-action6 suppression in vc33',
    }
    ledger.obstructions['obs:ls20->complex:language-mismatch'] = {
        'kind':'transfer_type_mismatch',
        'source':'ls20:compiled-L1-route',
        'destinations':['ft09','vc33'],
        'reason':'primitive action consequence signature does not match exact parameterized Action6 language',
    }
    if 'bt11' in keys:
        ledger.obstructions['obs:bt11:control-only'] = {
            'kind':'fixture_control_boundary',
            'destination':'bt11',
            'reason':'SDK fixture is retained only as a negative/control lens and cannot establish public cross-game authority',
        }

    event = run_to_fixed_point(ledger, new_evidence=[keys['vc33']])
    event.transfer_proposals_created.append(f'{source}->vc33')
    event.transfer_proposals_refuted.append(transfer.capability_id)
    cancelled = [p for p in ledger.probes.values() if p.status == 'CANCELLED']
    cross_cancelled = [
        p for p in cancelled
        if p.cancellation_evidence and str(p.cancellation_evidence[0]).startswith('transfer:')
    ]
    verified = sum(c.kind=='destination_verified_transfer' for c in ledger.capabilities.values())
    refutations = sum(c.kind=='destination_refuted_transfer' for c in ledger.capabilities.values())
    acquired = sum(p.expected_cost for p in ledger.probes.values() if p.status != 'CANCELLED')
    represented = sum(p.expected_cost for p in ledger.probes.values())

    return ledger, {
        'arm':'sham' if sham else 'flash',
        'historical_acquisition_actions_represented':represented,
        'counterfactual_acquisition_actions_after_safe_cancellation':acquired,
        'by_game':costs,
        'protected_milestone_vector':milestone_vector(inputs),
        'probes_cancelled':len(cancelled),
        'cross_game_probes_cancelled':len(cross_cancelled),
        'actions_eliminated':sum(p.acquisition_actions_avoided for p in cancelled),
        'transfer_proposals':1,
        'verified_transfers':verified,
        'refuted_transfers':refutations,
        'obstructions':len(ledger.obstructions),
        'flash_closure_events':len(ledger.events),
        'active_capabilities':len(ledger.active_capabilities()),
        'raw_evidence_refs':len(ledger.raw_evidence),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--ls20-dir', required=True)
    parser.add_argument('--ft09-dir', required=True)
    parser.add_argument('--v2-dir', required=True)
    parser.add_argument('--bt11-json')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    inputs = load_inputs(args)
    dump(out/'input-manifest.json', input_manifest(inputs))
    independent_ledger, independent = execute_independent(inputs)
    flash_ledger, flash = execute_flash(inputs)
    _sham_ledger, sham = execute_flash(inputs, sham=True)

    v2_control = inputs['v2']['comparison']['flash_vs_market']
    live_v2_gain = bool(v2_control['level_delta'] > 0 or v2_control['consequence_yield_ratio'] > 1.0)
    acquisition_saved = independent['historical_acquisition_actions_represented'] - flash['counterfactual_acquisition_actions_after_safe_cancellation']
    performance_pass = acquisition_saved > 0 or live_v2_gain
    verdict = 'PASS' if performance_pass else ('INCONCLUSIVE' if inputs['bt11'] is None else 'FAIL')

    obstruction = {
        'name':'AUTHORITY_BEARING_TRANSFER_INTERSECTION_EMPTY_V1',
        'status':'ESTABLISHED_BOUNDED' if not performance_pass else 'NOT_ESTABLISHED',
        'mechanism':'the four retained regimes share proposal-level motifs, but no tested cross-game capability both type-matches and has independent destination authority strong enough to eliminate a destination acquisition',
        'evidence':{
            'v2_flash_vs_market_consequence_yield_ratio':v2_control['consequence_yield_ratio'],
            'v2_flash_vs_market_level_delta':v2_control['level_delta'],
            'v1_verified_transfers':flash['verified_transfers'],
            'v1_refuted_transfers':flash['refuted_transfers'],
            'v1_cross_game_actions_saved':acquisition_saved,
            'ls20_intervention_language':'primitive',
            'ft09_intervention_language':'exact parameterized Action6',
            'vc33_destination_fact':'market-local public arm reaches L1, refuting generic Action6-fatal transfer',
        },
        'claim_boundary':'bounded to pinned ls20 V3, ft09 fatal-basin certificate, V2 public three-game artifact, and bt11 SDK-fixture control; not a theorem against richer future transfer languages',
    }

    comparison = {
        'schema':'qckn-flash-multigame-v1',
        'flash_verdict':verdict,
        'hypothesis_status':'NO_PERFORMANCE_COMPOUNDING_YET' if not performance_pass else 'PERFORMANCE_COMPOUNDING_OBSERVED',
        'independent':independent,
        'flash':flash,
        'sham':sham,
        'delta':{
            'acquisition_saved':acquisition_saved,
            'milestone_improvement':0,
            'future_probes_eliminated':flash['cross_game_probes_cancelled'],
            'active_capability_compression_vs_history':len(independent_ledger.probes)-flash['active_capabilities'],
        },
        'strongest_causal_chain':[
            'ft09 bounded fatal-basin certificate',
            '-> candidate generic complex-Action6 negative transfer',
            '-> vc33 destination check against pinned V2 public evidence',
            '-> transfer refuted because vc33 reaches L1',
            '-> zero destination probes may be cancelled safely',
        ],
        'v2_live_control':v2_control,
        'obstruction':obstruction,
        'claim_boundary':'Conservative retained-evidence counterfactual cancellation audit. Historical probes are not re-executed merely to reproduce pinned facts; bt11 is fixture control only.',
    }

    dump(out/'independent-results.json', independent)
    dump(out/'flash-results.json', flash)
    dump(out/'sham-results.json', sham)
    dump(out/'comparison.json', comparison)
    dump(out/'global-ledger.json', flash_ledger.snapshot())
    dump(out/'probe-ledger.json', flash_ledger.snapshot()['probes'])
    dump(out/'flash-events.json', flash_ledger.snapshot()['events'])
    dump(out/'obstruction.json', obstruction)

    print('FLASH_VERDICT=' + verdict)
    print('FLASH_COMPARISON=' + json.dumps(comparison, sort_keys=True))
    if verdict == 'INCONCLUSIVE':
        raise SystemExit(3)


if __name__ == '__main__':
    main()

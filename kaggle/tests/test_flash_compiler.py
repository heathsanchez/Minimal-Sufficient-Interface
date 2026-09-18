from __future__ import annotations
import json
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'kaggle' / 'src'))

from metalogic_arc3.flash_closure import run_to_fixed_point, validate_transfer_result
from metalogic_arc3.flash_ledger import EvidenceRef, GlobalCapability, GlobalLedger, Probe, Residual
from metalogic_arc3.flash_scheduler import choose_wave


class FlashCompilerTests(unittest.TestCase):
    def base(self):
        ledger = GlobalLedger(['a', 'b'])
        ea = EvidenceRef('a', 'exact', 'run-a', '1', 'aa')
        eb = EvidenceRef('b', 'exact', 'run-b', '1', 'bb')
        ka = ledger.add_evidence(ea)
        kb = ledger.add_evidence(eb)
        return ledger, ka, kb, ea, eb

    def test_deterministic_serialization_and_provenance(self):
        ledger, _ka, _kb, ea, _eb = self.base()
        ledger.add_capability(GlobalCapability('c', 'obstruction', {'a'}, {'x': 1}, ('fatal',), [ea]))
        self.assertEqual(ledger.content_hash(), ledger.content_hash())
        snap = ledger.snapshot()
        snap['capabilities']['c']['scope']['x'] = 9
        self.assertEqual(ledger.capabilities['c'].scope['x'], 1)
        ledger.assert_provenance()

    def test_fixed_point_compiles_route_and_cancels_probe(self):
        ledger, _ka, _kb, ea, _eb = self.base()
        ledger.add_capability(GlobalCapability('route67','compiled_route',{'a'},{'target':'L1'},('L1',),[ea],('L1',),67))
        ledger.add_capability(GlobalCapability('route57','compiled_route',{'a'},{'target':'L1'},('L1',),[ea],('L1',),57,notes={'settles_tokens':['route:L1']}))
        ledger.add_residual(Residual('r','a','route',10,{'protected_progress'}))
        ledger.add_probe(Probe('p','a','s',(1,),{'r'},0,10,cancellation_conditions={'route:L1'}))
        event = run_to_fixed_point(ledger)
        self.assertEqual(ledger.capabilities['route57'].state,'ACTIVE')
        self.assertEqual(ledger.capabilities['route67'].state,'RESERVE')
        self.assertEqual(ledger.probes['p'].status,'CANCELLED')
        self.assertEqual(event.estimated_future_actions_eliminated,10)

    def test_revocation_separator(self):
        ledger, _ka, _kb, ea, _eb = self.base()
        ledger.add_capability(GlobalCapability('q','state_equivalence_certificate',{'a'},{},('eq',),[ea]))
        ledger.add_capability(GlobalCapability('sep','separator',{'a'},{},('split',),[ea],notes={'revokes':'q'}))
        event = run_to_fixed_point(ledger)
        self.assertEqual(ledger.capabilities['q'].state,'REVOKED')
        self.assertIn('q',event.capabilities_revoked)

    def test_transfer_isolation_and_destination_authority(self):
        ledger, _ka, kb, ea, _eb = self.base()
        ledger.add_capability(GlobalCapability('src','fatal_basin',{'a'},{},('fatal-family',),[ea]))
        ledger.add_probe(Probe('pb','b','ctx',(6,1,1),set(),0,7,cancellation_conditions={'dest:verified'}))
        run_to_fixed_point(ledger)
        self.assertEqual(ledger.probes['pb'].status,'PENDING')
        cap = validate_transfer_result(
            ledger,
            source_capability_id='src',
            destination_game='b',
            destination_evidence_id=kb,
            verified=True,
            settles_tokens=['dest:verified'],
        )
        event = run_to_fixed_point(ledger,new_evidence=[kb])
        self.assertEqual(ledger.probes['pb'].status,'CANCELLED')
        self.assertIn(cap.capability_id,ledger.capabilities)
        self.assertEqual(event.estimated_future_actions_eliminated,7)

    def test_sham_does_not_cancel(self):
        ledger, _ka, _kb, ea, _eb = self.base()
        ledger.add_capability(GlobalCapability('sham','transferable_capability_candidate',{'a'},{},('irrelevant',),[ea]))
        ledger.add_probe(Probe('pb','b','ctx',(6,1,1),set(),0,7,cancellation_conditions={'dest:verified'}))
        run_to_fixed_point(ledger)
        self.assertEqual(ledger.probes['pb'].status,'PENDING')

    def test_order_robustness_for_independent_caps(self):
        def make(order):
            ledger, _ka, _kb, ea, eb = self.base()
            caps = {
                'x': GlobalCapability('x','obstruction',{'a'},{'k':'x'},('x',),[ea]),
                'y': GlobalCapability('y','obstruction',{'b'},{'k':'y'},('y',),[eb]),
            }
            for name in order:
                ledger.add_capability(caps[name])
                run_to_fixed_point(ledger)
            snap = ledger.snapshot()
            snap['events'] = []
            return json.dumps(snap,sort_keys=True)
        self.assertEqual(make(['x','y']),make(['y','x']))

    def test_scheduler_deterministic_and_no_double_payment(self):
        ledger, _ka, _kb, _ea, _eb = self.base()
        ledger.add_residual(Residual('r1','a','x',10,{'transfer'},demand_signature=('k',)))
        ledger.add_residual(Residual('r2','b','x',20,{'transfer'},demand_signature=('k',)))
        ledger.add_probe(Probe('p1','a',None,(1,),{'r1'},0,3))
        ledger.add_probe(Probe('p2','b',None,(2,),{'r2'},0,4))
        wave = choose_wave(ledger,width=2)
        self.assertEqual([p.probe_id for p in wave],['p2','p1'])
        ledger.probes['p2'].status='EXECUTED'
        self.assertEqual([p.probe_id for p in choose_wave(ledger,width=2)],['p1'])

    def test_refuted_transfer_compiles_exact_online_obstruction(self):
        from metalogic_arc3.flash_closure import (
            transfer_proposal_blocked,
            transfer_obstruction_key,
        )
        ledger, _ka, kb, ea, _eb = self.base()
        ledger.add_capability(GlobalCapability(
            'src','fatal_basin',{'a'},
            {'intervention_language':'complex_action6','claim':'generic fatal-family transfer'},
            ('fatal-family',),[ea]
        ))
        scope={'intervention_language':'complex_action6','claim':'generic fatal-family transfer'}

        self.assertFalse(transfer_proposal_blocked(
            ledger,
            source_capability_id='src',
            destination_game='b',
            exact_scope=scope,
        ))

        refuted = validate_transfer_result(
            ledger,
            source_capability_id='src',
            destination_game='b',
            destination_evidence_id=kb,
            verified=False,
            exact_scope=scope,
        )
        key = transfer_obstruction_key(
            ledger,
            source_capability_id='src',
            destination_game='b',
            exact_scope=scope,
        )
        self.assertIn(key, ledger.obstructions)
        self.assertEqual(ledger.obstructions[key]['capability_id'], refuted.capability_id)
        self.assertTrue(transfer_proposal_blocked(
            ledger,
            source_capability_id='src',
            destination_game='b',
            exact_scope=scope,
        ))

        changed_scope={'intervention_language':'complex_action6','claim':'different claim'}
        self.assertFalse(transfer_proposal_blocked(
            ledger,
            source_capability_id='src',
            destination_game='b',
            exact_scope=changed_scope,
        ))

    def test_obstruction_ablation_restores_destination_verification_path(self):
        from metalogic_arc3.flash_closure import (
            transfer_proposal_blocked,
            transfer_obstruction_key,
        )
        ledger, _ka, kb, ea, _eb = self.base()
        ledger.add_capability(GlobalCapability(
            'src','fatal_basin',{'a'},
            {'intervention_language':'complex_action6'},
            ('fatal-family',),[ea]
        ))
        scope={'intervention_language':'complex_action6','claim':'generic fatal-family transfer'}
        validate_transfer_result(
            ledger,
            source_capability_id='src',
            destination_game='b',
            destination_evidence_id=kb,
            verified=False,
            exact_scope=scope,
        )
        key = transfer_obstruction_key(
            ledger,
            source_capability_id='src',
            destination_game='b',
            exact_scope=scope,
        )
        self.assertTrue(transfer_proposal_blocked(
            ledger,
            source_capability_id='src',
            destination_game='b',
            exact_scope=scope,
        ))
        del ledger.obstructions[key]
        self.assertFalse(transfer_proposal_blocked(
            ledger,
            source_capability_id='src',
            destination_game='b',
            exact_scope=scope,
        ))

    def test_exact_transfer_refutation_survives_canonical_restart(self):
        from metalogic_arc3.flash_closure import (
            export_compiled_transfer_obstructions,
            import_compiled_transfer_obstructions,
            transfer_proposal_blocked,
        )
        source_ledger, _ka, kb, ea, eb = self.base()
        source_ledger.add_capability(GlobalCapability(
            'src','fatal_basin',{'a'},{'intervention_language':'complex_action6'},
            ('fatal-family',),[ea]
        ))
        scope={'intervention_language':'complex_action6','claim':'generic fatal-family transfer'}
        validate_transfer_result(
            source_ledger,
            source_capability_id='src',
            destination_game='b',
            destination_evidence_id=kb,
            verified=False,
            exact_scope=scope,
        )
        text = export_compiled_transfer_obstructions(source_ledger)

        restarted = GlobalLedger(['a','b'])
        ea2 = EvidenceRef('a','exact','run-a','1','aa')
        eb2 = EvidenceRef('b','exact','run-b','1','bb')
        restarted.add_evidence(ea2)
        restarted.add_evidence(eb2)
        restarted.add_capability(GlobalCapability(
            'src','fatal_basin',{'a'},{'intervention_language':'complex_action6'},
            ('fatal-family',),[ea2]
        ))
        imported = import_compiled_transfer_obstructions(restarted, text)
        self.assertEqual(imported, 1)
        self.assertTrue(transfer_proposal_blocked(
            restarted,
            source_capability_id='src',
            destination_game='b',
            exact_scope=scope,
        ))
        self.assertEqual(export_compiled_transfer_obstructions(restarted), text)

    def test_restart_rejects_stale_destination_evidence(self):
        from metalogic_arc3.flash_closure import (
            export_compiled_transfer_obstructions,
            import_compiled_transfer_obstructions,
        )
        source_ledger, _ka, kb, ea, _eb = self.base()
        source_ledger.add_capability(GlobalCapability(
            'src','fatal_basin',{'a'},{},('fatal-family',),[ea]
        ))
        scope={'claim':'generic fatal-family transfer'}
        validate_transfer_result(
            source_ledger,
            source_capability_id='src',
            destination_game='b',
            destination_evidence_id=kb,
            verified=False,
            exact_scope=scope,
        )
        text = export_compiled_transfer_obstructions(source_ledger)

        stale = GlobalLedger(['a','b'])
        ea2 = EvidenceRef('a','exact','run-a','1','aa')
        stale.add_evidence(ea2)
        stale.add_evidence(EvidenceRef('b','exact','run-b','1','STALE'))
        stale.add_capability(GlobalCapability(
            'src','fatal_basin',{'a'},{},('fatal-family',),[ea2]
        ))
        with self.assertRaisesRegex(ValueError, 'destination evidence mismatch'):
            import_compiled_transfer_obstructions(stale, text)

    def test_restart_rejects_noncanonical_obstruction_present(self):
        from metalogic_arc3.flash_closure import import_compiled_transfer_obstructions
        ledger, _ka, _kb, _ea, _eb = self.base()
        with self.assertRaisesRegex(ValueError, 'noncanonical compiled obstruction present'):
            import_compiled_transfer_obstructions(
                ledger,
                '{"schema": "qckn-transfer-obstructions-v1", "obstructions": []}',
            )


if __name__ == '__main__':
    unittest.main()

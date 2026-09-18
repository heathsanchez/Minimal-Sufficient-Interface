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


if __name__ == '__main__':
    unittest.main()

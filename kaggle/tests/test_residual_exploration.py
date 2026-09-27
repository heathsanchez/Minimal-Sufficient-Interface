from __future__ import annotations
import importlib
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from metalogic_arc3.developmental_controller import ProgressMemory
from metalogic_arc3.runtime import ActionToken, normalize_frame


def obs(value):
    return normalize_frame(dict(frame=[[[value]]], levels_completed=0,
                                state='NOT_FINISHED', available_actions=[1,2]))


class ResidualExplorationContracts(unittest.TestCase):
    def api(self):
        try:
            return importlib.import_module('metalogic_arc3.residual_exploration')
        except ModuleNotFoundError:
            self.fail('No goal-blocking residual consumer on the live controller')

    @staticmethod
    def catalog(_):
        return (ActionToken(1), ActionToken(2))

    def test_unknown_action_is_an_experiment_not_a_warranted_prediction(self):
        m=ProgressMemory(); a=obs(1); m.begin(a)
        d=self.api().frontier_continuation(m,a,self.catalog)
        self.assertEqual(d.action.source,'crystal_probe')
        self.assertEqual(d.status,'CANDIDATE')
        self.assertEqual(d.expected_targets,())
        self.assertEqual(m.machine().continuations,())
        self.assertEqual(m.last_residual['status'],'UNKNOWN')

    def test_observed_routes_are_composed_to_reach_unresolved_actions(self):
        m=ProgressMemory(); a,b=obs(1),obs(2); m.begin(a)
        m.observe(a,ActionToken(1),a)
        m.observe(a,ActionToken(2),b)
        m.begin(a)
        d=self.api().frontier_continuation(m,a,self.catalog)
        self.assertEqual(d.action.action_id,2)
        self.assertEqual(d.action.source,'crystal_probe_route')
        self.assertEqual(d.rank,2)
        self.assertTrue(d.support_refs)
        m.observe(a,d.action,b)
        e=self.api().frontier_continuation(m,b,self.catalog)
        self.assertEqual(e.action.action_id,1)
        self.assertEqual(e.action.source,'crystal_probe')

    def test_resource_limit_includes_the_final_unknown_probe(self):
        m=ProgressMemory(); a,b=obs(1),obs(2); m.begin(a)
        m.observe(a,ActionToken(1),a); m.observe(a,ActionToken(2),b);m.begin(a)
        self.assertIsNone(self.api().frontier_continuation(m,a,self.catalog,remaining_actions=1))
        self.assertEqual(m.last_residual['reason'],'insufficient_probe_budget')

    def test_closed_observed_loop_does_not_authorize_a_goal(self):
        m=ProgressMemory(); a=obs(1);m.begin(a)
        m.observe(a,ActionToken(1),a);m.observe(a,ActionToken(2),a)
        self.assertIsNone(self.api().frontier_continuation(m,a,self.catalog))
        self.assertIsNone(m.plan(a))
        self.assertTrue(any(r['reason']=='observed_frontier_exhausted_not_impossible' for r in m.residuals))

    def test_live_conflict_authorizes_expansion_only_after_kernel_obstruction(self):
        api=self.api(); ctl=api.ResidualController((1,2),archived_capabilities=(),trace_capabilities=())
        before=obs(1); after=obs(2)
        role=("procedure-effect-v2",1,None,None,0)
        ctl._previous=before; ctl._last_action=ActionToken(1,source="crystal_acquire")
        ctl._pending_acquisition_role=role; ctl._last_causal_role=("ACTION",1)
        ctl._process_previous_outcome(after)
        ctl.crystal.begin(before)
        ctl._previous=before; ctl._last_action=ActionToken(1,source="crystal_acquire")
        ctl._pending_acquisition_role=role; ctl._last_causal_role=("ACTION",1)
        terminal=normalize_frame(dict(frame=[[[3]]],levels_completed=1,
                                     state="NOT_FINISHED",available_actions=[1,2]))
        ctl._process_previous_outcome(terminal)
        self.assertTrue(ctl._future_kernels[role].expressive_obstruction)
        self.assertTrue(ctl._expansion_authorized(terminal))

    def test_earned_future_separator_changes_subsequent_role_identity(self):
        api=self.api(); ctl=api.ResidualController((1,2),archived_capabilities=(),trace_capabilities=())
        coarse=('procedure-effect-v3','ACTION',0)
        k=api.ProtectedFutureKernel()
        k.observe('PROGRESS','p',api.future_context(action_id=1,kind='ACTION'))
        k.observe('STUCK','n',api.future_context(action_id=2,kind='ACTION'))
        self.assertEqual(k.refine(('action_id','kind')),'action_id')
        ctl._future_kernels[coarse]=k
        o=obs(1)
        atoms=tuple(ctl._action_catalog(o))[:8]
        hypotheses=tuple(f'p{i}' for i in range(len(atoms)))
        actions=tuple((a.action_id,a.x,a.y) for a in atoms)
        # The learned separator must now distinguish action-role identity.
        roles=[]
        for a in actions:
            base=('procedure-effect-v2',a[0],a[1],a[2],o.levels_completed)
            kk=ctl._future_kernels.get(base)
            if kk and kk.separators:
                token=ActionToken(a[0],a[1],a[2])
                ctx=dict(api.future_context(**ctl._guard_features(ctl._causal_role(o,token))))
                base=base+tuple(('future-sep',name,ctx.get(name,'<UNKNOWN>')) for name in kk.separators)
            roles.append(base)
        self.assertTrue(any(any(part[0]=='future-sep' for part in r[5:]) for r in roles if len(r)>5))

    def test_separator_capability_survives_restart_and_ancestor_ablation_removes_reach(self):
        api=self.api(); ctl=api.ResidualController((1,),archived_capabilities=(),trace_capabilities=())
        coarse=('procedure-effect-v3','ACTION',0)
        cap={'id':'cap:mode','separator':'kind','role':coarse,'support':('s1','s2')}
        ctl._retained_separator_caps[(coarse,'kind')]=cap
        ctl.reset_episode()
        self.assertIn((coarse,'kind'),ctl._retained_separator_caps)
        ctl.ablate_separator_capability('cap:mode')
        self.assertNotIn((coarse,'kind'),ctl._retained_separator_caps)

    def test_dependent_acquisition_records_retained_parent_lineage(self):
        api=self.api(); ctl=api.ResidualController((1,),archived_capabilities=(),trace_capabilities=())
        o=obs(1); coarse=('procedure-effect-v3','ACTION',0)
        k=api.ProtectedFutureKernel(); k.separators=('kind',)
        ctl._future_kernels[coarse]=k
        ctl._retained_separator_caps[(coarse,'kind')]={'id':'cap:kind','separator':'kind','role':coarse,'support':('s',)}
        ctl._action_catalog=lambda _: (ActionToken(1),)
        token=ctl._crystal_acquisition_next(o)
        self.assertEqual(token.source,'crystal_acquire')
        self.assertEqual(ctl._pending_parent_caps,('cap:kind',))

    def test_ancestor_ablation_removes_future_cap_from_child_role(self):
        api=self.api(); ctl=api.ResidualController((1,),archived_capabilities=(),trace_capabilities=())
        o=obs(1); coarse=('procedure-effect-v3','ACTION',0)
        k=api.ProtectedFutureKernel(); k.separators=('kind',); ctl._future_kernels[coarse]=k
        ctl._retained_separator_caps[(coarse,'kind')]={'id':'cap:kind','separator':'kind','role':coarse,'support':('s',)}
        ctl._action_catalog=lambda _: (ActionToken(1),)
        ctl._crystal_acquisition_next(o)
        self.assertEqual(ctl._pending_parent_caps,('cap:kind',))
        ctl._pending_acquisition_role=None; ctl._pending_parent_caps=()
        ctl.ablate_separator_capability('cap:kind')
        ctl._crystal_acquisition_next(o)
        self.assertEqual(ctl._pending_parent_caps,())
        self.assertFalse(any(isinstance(x,tuple) and x and x[0]=='future-cap' for x in ctl._pending_acquisition_role[5:]))

    def test_preconflict_acquisition_quotient_pools_execution_coordinates(self):
        api=self.api(); ctl=api.ResidualController((6,),archived_capabilities=(),trace_capabilities=())
        o=obs(1)
        a=ctl._acquisition_coarse_role(ActionToken(6,1,2),o)
        b=ctl._acquisition_coarse_role(ActionToken(6,9,8),o)
        self.assertEqual(a,b)
        self.assertEqual(a,('procedure-effect-v3','CLICK',0))

    def test_legacy_controller_remains_an_available_ablation(self):
        api=self.api()
        from metalogic_arc3.developmental_controller import DevelopmentalController
        self.assertTrue(issubclass(api.ResidualController,DevelopmentalController))
        ctl=api.ResidualController((1,2),archived_capabilities=(),trace_capabilities=())
        token=ctl.observe_and_choose(dict(frame=[[[1]]],levels_completed=0,
                                         state='NOT_FINISHED',available_actions=[1,2]))
        self.assertEqual(token.source,'crystal_probe')

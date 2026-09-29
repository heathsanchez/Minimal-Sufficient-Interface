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



    def test_cross_marker_targets_are_frozen_across_marker_occlusion(self):
        api=self.api()
        def structural_frame(center, color, *, with_markers):
            h=w=32
            grid=[[5 for _ in range(w)] for _ in range(h)]
            if with_markers:
                def marker(r,col,marker_color):
                    for rr in range(r-1,r+2):
                        for cc in range(col-1,col+2):
                            grid[rr][cc]=4
                    grid[r][col]=marker_color
                for r,col in ((11,5),(11,17),(5,11),(17,11)):
                    marker(r,col,9)
                for r,col in ((8,3),(8,27),(3,15),(25,15)):
                    marker(r,col,11)
            r,col=center
            grid[r][col]=0
            for d in range(1,5):
                grid[r-d][col]=color; grid[r+d][col]=color
                grid[r][col-d]=color; grid[r][col+d]=color
            return dict(frame=[grid],levels_completed=0,state='NOT_FINISHED',
                        available_actions=[1,2,3,4,5])

        ctl=api.ResidualController(
            (1,2,3,4,5),archived_capabilities=(),trace_capabilities=())
        first=ctl.observe_and_choose(structural_frame((20,20),9,with_markers=True))
        self.assertEqual((first.action_id,first.source),(1,'crystal_cross_marker'))

        # Marker evidence is now absent, but the target relation was acquired
        # before motion and must remain stable while only the cross pose changes.
        second=ctl.observe_and_choose(structural_frame((17,20),9,with_markers=False))
        self.assertEqual((second.action_id,second.source),(1,'crystal_cross_marker'))
        third=ctl.observe_and_choose(structural_frame((14,20),9,with_markers=False))
        self.assertEqual((third.action_id,third.source),(1,'crystal_cross_marker'))
        fourth=ctl.observe_and_choose(structural_frame((11,20),9,with_markers=False))
        self.assertEqual((fourth.action_id,fourth.source),(3,'crystal_cross_marker'))
        fifth=ctl.observe_and_choose(structural_frame((11,17),9,with_markers=False))
        self.assertEqual((fifth.action_id,fifth.source),(3,'crystal_cross_marker'))
        sixth=ctl.observe_and_choose(structural_frame((11,14),9,with_markers=False))
        self.assertEqual((sixth.action_id,sixth.source),(3,'crystal_cross_marker'))
        switch=ctl.observe_and_choose(structural_frame((11,11),9,with_markers=False))
        self.assertEqual((switch.action_id,switch.source),(5,'crystal_cross_marker'))

        # After switch the active color changes; the second frozen target is
        # used without reacquiring any markers.
        other=ctl.observe_and_choose(structural_frame((20,15),11,with_markers=False))
        self.assertEqual((other.action_id,other.source),(1,'crystal_cross_marker'))

    def test_legacy_controller_remains_an_available_ablation(self):
        api=self.api()
        from metalogic_arc3.developmental_controller import DevelopmentalController
        self.assertTrue(issubclass(api.ResidualController,DevelopmentalController))
        ctl=api.ResidualController((1,2),archived_capabilities=(),trace_capabilities=())
        token=ctl.observe_and_choose(dict(frame=[[[1]]],levels_completed=0,
                                         state='NOT_FINISHED',available_actions=[1,2]))
        self.assertEqual(token.source,'crystal_probe')

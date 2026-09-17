from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'kaggle/src'))
from metalogic_arc3.memory_controller import MemoryGraphController
if importlib.util.find_spec('metalogic_arc3.consequence_controller') is None:
    Candidate = MemoryGraphController  # Run behavioral regressions against the old policy first.
else:
    from metalogic_arc3.consequence_controller import ConsequenceController as Candidate


def frame(grid=None, actions=(3,4), level=0, state='NOT_FINISHED'):
    if grid is None:
        grid = [[0]*8 for _ in range(8)]
    return dict(frame=[grid], available_actions=list(actions), levels_completed=level, state=state)


class ConsequenceAcquisitionContracts(unittest.TestCase):
    def policy(self, actions=(3,4), **kw):
        return Candidate(actions, archived_capabilities=(), **kw)

    def test_nonterminal_consequence_changes_next_experiment_before_any_reward(self):
        changed, unchanged = self.policy(), self.policy()
        self.assertEqual(changed.observe_and_choose(frame()).action_id, 3)
        self.assertEqual(unchanged.observe_and_choose(frame()).action_id, 3)
        grid = [[0]*8 for _ in range(8)]; grid[2][2]=7
        a=changed.observe_and_choose(frame(grid)).action_id
        b=unchanged.observe_and_choose(frame()).action_id
        self.assertNotEqual(a,b, 'nonterminal consequence was ignored')

    def test_visible_component_targets_precede_blind_lattice(self):
        grid=[[0]*64 for _ in range(64)]
        for y in range(17,22):
            for x in range(29,34): grid[y][x]=9
        p=self.policy((6,))
        first=p.observe_and_choose(frame(grid, (6,)))
        self.assertTrue(29 <= first.x <34 and 17 <= first.y <22,
                        'first intervention missed the isolated visible component')

    def test_unchanged_frame_does_not_refute_action_or_block_delayed_progress(self):
        p=self.policy(); count=0; won=False
        for _ in range(128):
            a=p.observe_and_choose(frame())
            count=count+1 if a.action_id==3 else 0
            if count==6:
                won=True;break
        self.assertTrue(won, 'no delayed-effect action sequence was explored')
        self.assertEqual(p.memory.refuted_count, 0)

    def test_visual_novelty_does_not_starve_other_interventions(self):
        p=self.policy(); used=set()
        for t in range(16):
            grid=[[0]*8 for _ in range(8)];grid[t//8][t%8]=7
            used.add(p.observe_and_choose(frame(grid)).action_id)
        self.assertEqual(used,{3,4})
        self.assertEqual(p.memory.capability_count,0, 'novelty is not verified progress')

    def test_contextual_effects_and_conflicting_histories_are_retained(self):
        p=self.policy()
        self.assertTrue(hasattr(p, 'effects'), 'no nonterminal evidence memory')
        e=p.effects
        a=(3,None,None)
        e.record('A',a,'B','shape',2,'history-one',False)
        e.record('A',a,'C','shape',1,'history-two',False)
        self.assertTrue(e.ambiguous('A',a))
        self.assertEqual(e.successors('A'), [])
        e.record('D',a,'E','shape',3,'other-history',False)
        self.assertEqual(e.attempts('D',a),1)
        self.assertEqual(e.attempts('A',a),2)

    def test_effect_memory_is_bounded(self):
        p=self.policy()
        self.assertTrue(hasattr(p, 'effects'), 'no bounded effect store')
        e=p.effects
        for n in range(e.limit+17):
            e.record(str(n),(3,None,None),str(n+1),'shape',1,'h',False)
        self.assertLessEqual(len(e.edges),e.limit)

    def test_reset_snapshot_restarts_the_same_consequential_present(self):
        p=self.policy()
        for _ in range(5):p.observe_and_choose(frame())
        p.reset_episode()
        self.assertTrue(hasattr(p,'snapshot_memory'), 'no consequence restart contract')
        snapshot=p.snapshot_memory()
        q=self.policy();q.restore_memory(snapshot)
        self.assertEqual(snapshot,q.snapshot_memory())
        self.assertEqual(p.observe_and_choose(frame()),q.observe_and_choose(frame()))

    def test_latest_animation_frame_supplies_visual_grounding(self):
        grid=[[0]*32 for _ in range(32)]
        for y in range(13,18):
            for x in range(21,26):grid[y][x]=2
        f=frame(grid,(6,));f['frame']=[[[0]*32 for _ in range(32)],grid]
        a=self.policy((6,)).observe_and_choose(f)
        self.assertTrue(21<=a.x<26 and 13<=a.y<18)

if __name__=='__main__':unittest.main(verbosity=2)

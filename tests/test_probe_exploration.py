import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experiments' / 'arc3_consequence'))
from agent import observation, run_episode
from probe_exploration import ProbeController, probe_consequence


def obs(v=0, state='NOT_FINISHED'):
    return {'frame': [[[v]]], 'levels_completed': 0, 'state': state,
            'available_actions': [1,2]}


class TinyEnv:
    """Action 1 is repeatably nonterminal/informative; action 2 is catastrophic."""
    def __init__(self):
        self.frame = obs(0)
        self.steps = 0
    @property
    def observation_space(self): return self.frame
    def step(self, action):
        self.steps += 1
        if action == 2:
            self.frame = obs(self.steps, 'GAME_OVER')
        else:
            self.frame = obs(self.steps % 2)
        return self.frame
    def reset(self):
        self.frame = obs(0); self.steps = 0; return self.frame


class ProbeExplorationTests(unittest.TestCase):
    def test_probe_is_observable_only(self):
        d = ProbeController((1,2), probe_enabled=True, retain_scripts=False)
        r = d.observe(obs(0), 1, obs(1))
        self.assertEqual(probe_consequence(r), (False, True, 1))

    def test_exact_ablation(self):
        warm = ProbeController((1,2), probe_enabled=True, retain_scripts=False)
        cold = ProbeController((1,2), probe_enabled=False, retain_scripts=False)
        self.assertTrue(warm.probe_enabled)
        self.assertFalse(cold.probe_enabled)
        self.assertEqual(warm.features, cold.features)

    def test_warm_retains_witnessed_safe_experiment_before_unseen(self):
        warm_env = TinyEnv(); cold_env = TinyEnv()
        warm = run_episode(warm_env, (1,2), 6,
                           ProbeController((1,2), probe_enabled=True, retain_scripts=False))
        cold = run_episode(cold_env, (1,2), 6,
                           ProbeController((1,2), probe_enabled=False, retain_scripts=False))
        self.assertGreater(warm['actions'], cold['actions'])
        self.assertEqual(cold['state'], 'GAME_OVER')
        self.assertGreaterEqual(len(warm['probe_log']), 2)

    def test_no_unevidenced_probe_feature_promotion(self):
        d = ProbeController((1,2), probe_enabled=True, retain_scripts=False)
        self.assertEqual(d.probe_features, ())
        d.observe(obs(0), 1, obs(1))
        self.assertEqual(d.probe_features, ())

if __name__ == '__main__': unittest.main()

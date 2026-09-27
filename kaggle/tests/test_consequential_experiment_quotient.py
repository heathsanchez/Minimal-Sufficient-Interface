"""Contracts for consequential experiment quotient control.

These are controller-constitution tests, not ARC score evidence.
"""
from __future__ import annotations
import unittest
from metalogic_arc3.residual_exploration import ResidualController
from metalogic_arc3.runtime import normalize_frame

def obs(actions=(1,2,3), level=0):
    return normalize_frame(dict(frame=[[[1]]], levels_completed=level,
        state='NOT_FINISHED', available_actions=list(actions)))

class ConsequentialExperimentQuotientContracts(unittest.TestCase):
    def controller(self):
        return ResidualController((1,2,3), archived_capabilities=(), trace_capabilities=())

    def test_probe_exhaustion_is_unknown_not_expand(self):
        c=self.controller()
        c._probe_spend_by_level[0]=c._genesis_threshold
        c._crystal_acquisition_next=lambda o: None
        c._genesis_next=lambda o: self.fail("EXPAND requires certified obstruction")
        c.crystal._compile=lambda: (None,{}, {}, {})
        c._action_catalog=lambda o: ()
        self.assertIsNone(c._next_retained(obs(())))
        self.assertGreater(len(c.crystal.residuals),0)

    def test_expand_requires_explicit_obstruction(self):
        c=self.controller()
        c._probe_spend_by_level[0]=c._genesis_threshold
        c._crystal_acquisition_next=lambda o: None
        c.crystal._compile=lambda: (None,{}, {}, {})
        c._action_catalog=lambda o: ()
        c._genesis_next=lambda o: "EXPANDED"
        self.assertIsNone(c._next_retained(obs(())))
        c.certify_expressive_obstruction(0, "finite-current-class-exhaustive")
        self.assertEqual(c._next_retained(obs(())), "EXPANDED")

if __name__=="__main__": unittest.main()

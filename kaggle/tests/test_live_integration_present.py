"""Integration must exist on the delivered hot path, not only in experiments."""
import unittest
from pathlib import Path

class LiveIntegrationPresent(unittest.TestCase):
    def test_continuation_compiler_is_in_delivered_source(self):
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root/'src/metalogic_arc3/developmental_controller.py').is_file(),
                        'Missing live ARC continuation compiler/controller')
        self.assertIn('DevelopmentalController', (root/'src/metalogic_arc3/agent_template.py').read_text())
        self.assertIn('developmental_controller', (root/'scripts/build_agent.py').read_text())

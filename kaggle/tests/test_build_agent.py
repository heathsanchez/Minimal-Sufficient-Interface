from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "kaggle" / "scripts" / "build_agent.py"


class BuildAgentContracts(unittest.TestCase):
    def test_build_is_deterministic_and_self_contained(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "agent-a.py"
            b = Path(tmp) / "agent-b.py"
            subprocess.run([sys.executable, str(SCRIPT), "--output", str(a)], check=True, cwd=ROOT)
            subprocess.run([sys.executable, str(SCRIPT), "--output", str(b)], check=True, cwd=ROOT)
            first, second = a.read_bytes(), b.read_bytes()
            self.assertEqual(first, second)
            self.assertEqual(hashlib.sha256(first).hexdigest(), hashlib.sha256(second).hexdigest())
            text = first.decode()
            self.assertIn("class MyAgent", text)
            self.assertIn("class OnlineController", text)
            self.assertIn("class TraceCapability", text)
            self.assertIn("class ArcMemoryGraph", text)
            self.assertIn("class MemoryGraphController", text)
            self.assertIn("BUILD_PROVENANCE", text)
            self.assertNotIn("from .runtime", text)
            self.assertNotIn("from .memory_graph", text)
            self.assertNotIn("from .memory_controller", text)
            self.assertNotIn("metalogic_arc3", text)
            for forbidden in ("requests", "openai", "anthropic", "subprocess", "socket", "urllib"):
                self.assertNotIn(forbidden, text.lower())
            compile(text, str(a), "exec")


if __name__ == "__main__":
    unittest.main(verbosity=2)

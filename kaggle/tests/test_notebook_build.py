from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD_AGENT = ROOT / "kaggle" / "scripts" / "build_agent.py"
BUILD_NOTEBOOK = ROOT / "kaggle" / "scripts" / "build_notebook.py"


class NotebookBuildContracts(unittest.TestCase):
    def test_notebook_is_offline_cpu_and_uses_gateway_pattern(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            agent = tmp / "my_agent.py"
            notebook = tmp / "submission.ipynb"
            metadata = tmp / "kernel-metadata.json"
            metadata.write_text(json.dumps({
                "id": "REPLACE_WITH_YOUR_USERNAME/metalogic-arc3",
                "title": "Metalogic ARC3",
                "code_file": "submission.ipynb",
                "language": "python",
                "kernel_type": "notebook",
                "is_private": False,
                "enable_gpu": False,
                "enable_internet": False,
                "dataset_sources": [],
                "competition_sources": ["arc-prize-2026-arc-agi-3"],
                "kernel_sources": []
            }))
            subprocess.run([sys.executable, str(BUILD_AGENT), "--output", str(agent)], check=True, cwd=ROOT)
            subprocess.run([
                sys.executable, str(BUILD_NOTEBOOK),
                "--agent", str(agent),
                "--output", str(notebook),
                "--metadata", str(metadata),
            ], check=True, cwd=ROOT)
            nb = json.loads(notebook.read_text())
            kaggle = nb["metadata"]["kaggle"]
            self.assertEqual(kaggle["accelerator"], "none")
            self.assertFalse(kaggle["isInternetEnabled"])
            self.assertFalse(kaggle["isGpuEnabled"])
            source = "\n".join(str(cell.get("source", "")) for cell in nb["cells"])
            self.assertIn("%%writefile /tmp/my_agent.py", source)
            self.assertIn("KAGGLE_IS_COMPETITION_RERUN", source)
            self.assertIn("http://gateway:8001/api/games", source)
            self.assertIn("python main.py --agent myagent", source)
            self.assertIn("submission.parquet", source)
            meta = json.loads(metadata.read_text())
            self.assertFalse(meta["enable_gpu"])
            self.assertFalse(meta["enable_internet"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

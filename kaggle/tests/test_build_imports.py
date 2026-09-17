from __future__ import annotations

import ast
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "kaggle" / "scripts" / "build_agent.py"
SPEC = importlib.util.spec_from_file_location("arc3_build_import_contract", SCRIPT)
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class BuildImportContracts(unittest.TestCase):
    def test_added_symbol_does_not_escape_vendoring(self):
        source = (
            "from .memory_graph import ActionKey, ArcMemoryGraph, ContextKey, ProgramKey\n"
            "x = 1\n"
        )
        cleaned = BUILDER.clean_module(
            source,
            ("from .memory_graph import ActionKey, ArcMemoryGraph, ContextKey\n",),
        )
        imports = [node for node in ast.walk(ast.parse(cleaned))
                   if isinstance(node, ast.ImportFrom) and node.level]
        self.assertEqual(imports, [])
        self.assertIn("x = 1", cleaned)

    def test_multiline_import_is_removed_but_external_imports_survive(self):
        source = (
            "from __future__ import annotations\n\n"
            "from .memory_graph import (\n    ActionKey,\n    ProgramKey,\n)\n"
            "from typing import Any\nx = 1\n"
        )
        cleaned = BUILDER.clean_module(source, ("from .memory_graph import ActionKey\n",))
        imports = [node for node in ast.walk(ast.parse(cleaned))
                   if isinstance(node, ast.ImportFrom) and node.level]
        self.assertEqual(imports, [])
        self.assertIn("from typing import Any", cleaned)
        self.assertIn("x = 1", cleaned)

    def test_only_explicitly_vendored_modules_are_removed(self):
        source = "from .not_vendored import Other\nx = 1\n"
        cleaned = BUILDER.clean_module(source, ("from .memory_graph import ActionKey\n",))
        self.assertIn("from .not_vendored import Other", cleaned)


if __name__ == "__main__":
    unittest.main(verbosity=2)

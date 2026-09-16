from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "scripts" / "play_local.py").read_text()


class PlayLocalSourceContracts(unittest.TestCase):
    def test_supports_pinned_offline_environment_directory(self):
        self.assertIn("--offline-environments-dir", SOURCE)
        self.assertIn("OperationMode.OFFLINE", SOURCE)
        self.assertIn("environments_dir=", SOURCE)

    def test_preserves_exact_versioned_game_id_for_arc_make(self):
        self.assertIn("resolved_game_ids", SOURCE)
        self.assertIn("arc.make(game_id", SOURCE)
        self.assertNotIn("game_ids = [env.game_id.split(\"-\")[0]", SOURCE)

    def test_dynamic_agent_module_is_registered_before_exec(self):
        registration = "sys.modules[spec.name] = module"
        execution = "spec.loader.exec_module(module)"
        self.assertIn(registration, SOURCE)
        self.assertIn(execution, SOURCE)
        self.assertLess(SOURCE.index(registration), SOURCE.index(execution))

    def test_smoke_marker_is_emitted(self):
        self.assertIn("ARC3_PUBLIC_SMOKE=PASS", SOURCE)


if __name__ == "__main__":
    unittest.main()

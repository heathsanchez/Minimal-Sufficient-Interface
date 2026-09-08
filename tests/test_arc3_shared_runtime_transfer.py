import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace

MODULE_DIR = Path(__file__).resolve().parents[1] / "experiments" / "arc3_shared_runtime"
sys.path.insert(0, str(MODULE_DIR))

from shared_runtime_transfer import (  # noqa: E402
    GateApproval,
    QualificationError,
    RetainedCapability,
    program_digest,
    qualify_transfer,
    render_lean_gate,
    verify_git_commit,
)


class SharedRuntimeTransferTests(unittest.TestCase):
    def setUp(self):
        self.candidate = ((9, 17, 3), (9, 17, 3))
        self.sham = ((8, 2, 5),)
        self.actions = ((8, 2, 5), (9, 1, 1), (9, 17, 3))

    def test_retained_capability_state_is_immutable(self):
        retained = RetainedCapability(
            program=self.candidate,
            program_sha256=program_digest(self.candidate),
            certificate_sha256="certificate",
            gate_marker="ARC3_SHARED_GATE_PASS",
        )
        with self.assertRaises(FrozenInstanceError):
            retained.program = self.sham

    def development(self):
        candidate = self.candidate
        sham = self.sham
        return SimpleNamespace(
            options=[candidate],
            prefix=candidate,
            evidence=[
                {"target": 0, "suffix": sham, "progress": 0, "actions": 1, "status": "OBSERVED"},
                {"target": 0, "suffix": candidate, "progress": 1, "actions": 2, "status": "PROGRESS_WITNESSED"},
            ],
            initial_sha256="same-start",
            status="TRAINING_BOUND_EXHAUSTED",
            snapshot=lambda: {
                "status": "TRAINING_BOUND_EXHAUSTED",
                "levels_witnessed": 1,
                "training_actions": 19,
                "training_episodes": 7,
            },
        )

    def harness(self, events):
        calls = {"candidate": 0}

        def factory():
            return object()

        def discover(*_args, **_kwargs):
            events.append("discover")
            return self.development()

        def execute(_env, _prefix, suffix, _target, _budget, **_kwargs):
            suffix = tuple(suffix)
            if suffix == self.candidate:
                calls["candidate"] += 1
                arm = "candidate-replay" if calls["candidate"] == 1 else "warm-deploy"
                levels = 1
            elif suffix == self.sham:
                arm = "sham-replay"
                levels = 0
            else:
                arm = "primitive"
                levels = 0
            events.append(arm)
            return {
                "status": "PROGRESS_WITNESSED" if levels else "OBSERVED",
                "initial_sha256": "same-start",
                "levels_completed": levels,
                "actions": len(suffix),
                "progress": levels,
                "state": "NOT_FINISHED",
                "trace_sha256": hashlib.sha256(repr(suffix).encode()).hexdigest(),
            }

        return factory, discover, execute

    def test_generated_gate_uses_supplied_program_not_known_bt33_sequence(self):
        source = render_lean_gate(
            cold_levels=0,
            candidate_levels=2,
            sham_levels=0,
            candidate=self.candidate,
            sham=self.sham,
        )
        self.assertIn("SynthesisCore.develop", source)
        self.assertIn("SynthesisCore.promoteIfReplayAdequate", source)
        self.assertIn("⟨9, 17, 3⟩", source)
        self.assertEqual(source.count("⟨9, 17, 3⟩"), 2)

    def test_generated_gate_rejects_non_natural_action_tokens(self):
        invalid_programs = ((True,), ((9, -1, 3),), ((9, 1 << 40, 3),))
        for program in invalid_programs:
            with self.subTest(program=program):
                with self.assertRaises(QualificationError):
                    render_lean_gate(
                        cold_levels=0,
                        candidate_levels=1,
                        sham_levels=0,
                        candidate=program,
                        sham=self.sham,
                    )

    def test_generated_gate_kernel_checks(self):
        lean = shutil.which("lean")
        if lean is None:
            self.skipTest("Lean is qualified in the dedicated ARC3 workflow")
        source = render_lean_gate(
            cold_levels=0,
            candidate_levels=1,
            sham_levels=0,
            candidate=self.candidate,
            sham=self.sham,
        )
        with tempfile.TemporaryDirectory() as directory:
            certificate = Path(directory) / "Certificate.lean"
            certificate.write_text(source)
            env = dict(os.environ)
            env["LEAN_PATH"] = os.environ.get(
                "LEAN_PATH", str(Path(__file__).resolve().parents[1] / "lean")
            )
            completed = subprocess.run(
                [lean, str(certificate)], text=True, capture_output=True, env=env
            )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("ARC3_SHARED_GATE_PASS", completed.stdout)

    def test_gate_precedes_retention_and_warm_deployment(self):
        events = []
        factory, discover, execute = self.harness(events)

        def gate(request):
            events.append("lean-gate")
            return GateApproval(
                program_sha256=program_digest(request.candidate),
                certificate_sha256="a" * 64,
            )

        result = qualify_transfer(
            factory=factory,
            actions=self.actions,
            discover_levels=discover,
            execute_stage=execute,
            gate=gate,
            budget=20,
            max_episodes=30,
            max_depth=4,
            max_training_actions=200,
            max_levels=2,
        )

        self.assertEqual(
            events,
            ["primitive", "discover", "sham-replay", "candidate-replay", "lean-gate", "warm-deploy", "primitive"],
        )
        self.assertEqual(result["retained"]["program_sha256"], program_digest(self.candidate))
        self.assertTrue(result["improved"])
        self.assertEqual(result["warm"]["levels_completed"], 1)
        self.assertEqual(result["ablation"]["levels_completed"], 0)

    def test_gate_rejection_prevents_retention_and_deployment(self):
        events = []
        factory, discover, execute = self.harness(events)

        def reject(_request):
            events.append("lean-gate")
            return None

        with self.assertRaises(QualificationError):
            qualify_transfer(
                factory=factory,
                actions=self.actions,
                discover_levels=discover,
                execute_stage=execute,
                gate=reject,
                budget=20,
                max_episodes=30,
                max_depth=4,
                max_training_actions=200,
                max_levels=2,
            )
        self.assertNotIn("warm-deploy", events)

    def test_gate_approval_without_certificate_binding_is_refused(self):
        events = []
        factory, discover, execute = self.harness(events)

        def unbound(request):
            events.append("lean-gate")
            return GateApproval(program_sha256=program_digest(request.candidate))

        with self.assertRaisesRegex(QualificationError, "certificate binding"):
            qualify_transfer(
                factory=factory,
                actions=self.actions,
                discover_levels=discover,
                execute_stage=execute,
                gate=unbound,
                budget=20,
                max_episodes=30,
                max_depth=4,
                max_training_actions=200,
                max_levels=2,
            )
        self.assertNotIn("warm-deploy", events)

    def test_wrong_program_approval_is_refused(self):
        events = []
        factory, discover, execute = self.harness(events)

        def wrong(_request):
            events.append("lean-gate")
            return GateApproval(program_sha256="0" * 64)

        with self.assertRaises(QualificationError):
            qualify_transfer(
                factory=factory,
                actions=self.actions,
                discover_levels=discover,
                execute_stage=execute,
                gate=wrong,
                budget=20,
                max_episodes=30,
                max_depth=4,
                max_training_actions=200,
                max_levels=2,
            )
        self.assertNotIn("warm-deploy", events)

    def test_inconclusive_discovery_is_rejected_even_with_an_earlier_option(self):
        events = []
        factory, _, execute = self.harness(events)
        development = self.development()
        development.status = "INCONCLUSIVE_UNMATCHED_START_OR_PREFIX"

        with self.assertRaisesRegex(QualificationError, "inconclusive frozen discovery"):
            qualify_transfer(
                factory=factory,
                actions=self.actions,
                discover_levels=lambda *_args: development,
                execute_stage=execute,
                gate=lambda _request: None,
                budget=20,
                max_episodes=30,
                max_depth=4,
                max_training_actions=200,
                max_levels=2,
            )
        self.assertNotIn("sham-replay", events)

    def test_partially_executed_zero_progress_proposal_is_not_a_sham(self):
        events = []
        factory, _, execute = self.harness(events)
        development = self.development()
        development.evidence[0]["actions"] = 0

        with self.assertRaisesRegex(QualificationError, "fully executed zero-progress sham"):
            qualify_transfer(
                factory=factory,
                actions=self.actions,
                discover_levels=lambda *_args: development,
                execute_stage=execute,
                gate=lambda _request: None,
                budget=20,
                max_episodes=30,
                max_depth=4,
                max_training_actions=200,
                max_levels=2,
            )
        self.assertNotIn("sham-replay", events)

    def test_wrong_or_dirty_frozen_checkpoint_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "config", "user.email", "test@example.invalid"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(repo), "config", "user.name", "Test"], check=True
            )
            tracked = repo / "tracked.txt"
            tracked.write_text("frozen\n")
            subprocess.run(["git", "-C", str(repo), "add", "tracked.txt"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-qm", "frozen"], check=True)
            actual = subprocess.check_output(
                ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
            ).strip()
            self.assertEqual(verify_git_commit(repo, actual), actual)
            with self.assertRaises(QualificationError):
                verify_git_commit(repo, "0" * 40)
            tracked.write_text("mutated\n")
            with self.assertRaises(QualificationError):
                verify_git_commit(repo, actual)
            subprocess.run(["git", "-C", str(repo), "checkout", "--", "tracked.txt"], check=True)
            untracked = repo / "untracked.py"
            untracked.write_text("raise RuntimeError('shadow')\n")
            with self.assertRaises(QualificationError):
                verify_git_commit(repo, actual)
            untracked.unlink()
            (repo / ".git" / "info" / "exclude").write_text("ignored.py\n")
            (repo / "ignored.py").write_text("raise RuntimeError('ignored shadow')\n")
            with self.assertRaises(QualificationError):
                verify_git_commit(repo, actual)


if __name__ == "__main__":
    unittest.main()

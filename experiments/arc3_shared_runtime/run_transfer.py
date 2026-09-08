"""Run the shared replay-gated runtime around the frozen bt33 harness."""
import argparse
import importlib.metadata
import json
import logging
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from shared_runtime_transfer import (  # noqa: E402
    LeanGate,
    QualificationError,
    qualify_transfer,
    verify_git_commit,
)

FROZEN_HARNESS_COMMIT = "68e37033f3ae1e86e992dfe8d982aef9133612aa"
UPSTREAM_ARC_COMMIT = "f12822c4d550121c35a275008d964afbbed47d2f"
FROZEN_SHARED_RUNTIME_COMMIT = "4f03be5acc34ce23775c19cd7f291ba001bf8b67"
ARC_PACKAGE_VERSION = "0.9.9"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frozen-harness", required=True)
    parser.add_argument("--upstream-arc", required=True)
    parser.add_argument("--shared-runtime", required=True)
    parser.add_argument("--lean-path", required=True)
    parser.add_argument("--game", default="bt33-a7c3f9d18b4e")
    parser.add_argument("--max-actions", type=int, default=120)
    parser.add_argument("--max-episodes", type=int, default=512)
    parser.add_argument("--max-depth", type=int, default=32)
    parser.add_argument("--max-training-actions", type=int, default=3000)
    parser.add_argument("--max-levels", type=int, default=3)
    parser.add_argument("--stride", type=int, default=8)
    parser.add_argument("--max-grounded-actions", type=int, default=256)
    parser.add_argument("--lean", default="lean")
    parser.add_argument("--certificate", default="arc3-shared-runtime-certificate.lean")
    parser.add_argument("--output", default="arc3-shared-runtime-transfer.json")
    args = parser.parse_args()

    frozen = Path(args.frozen_harness).resolve()
    upstream = Path(args.upstream_arc).resolve()
    shared_runtime = Path(args.shared_runtime).resolve()
    verify_git_commit(frozen, FROZEN_HARNESS_COMMIT)
    verify_git_commit(upstream, UPSTREAM_ARC_COMMIT)
    verify_git_commit(shared_runtime, FROZEN_SHARED_RUNTIME_COMMIT)
    observed_version = importlib.metadata.version("arc-agi")
    if observed_version != ARC_PACKAGE_VERSION:
        raise QualificationError(
            f"arc-agi mismatch: expected {ARC_PACKAGE_VERSION}, observed {observed_version}"
        )

    frozen_modules = frozen / "experiments" / "arc3_consequence"
    sys.path.insert(0, str(frozen_modules))
    from arc_agi import Arcade, OperationMode
    from agent import observation
    from compositional_development import discover_levels
    from finite_consequence import digest
    from multi_level_development import execute_stage
    from parameterized_actions import action_catalog, decode

    logger = logging.getLogger("arc3-shared-runtime")
    logger.addHandler(logging.NullHandler())
    logger.setLevel(logging.WARNING)
    environments_dir = upstream / "test_environment_files"

    def factory():
        arcade = Arcade(
            operation_mode=OperationMode.OFFLINE,
            environments_dir=str(environments_dir),
            logger=logger,
        )
        env = arcade.make(args.game)
        if env is None:
            raise QualificationError("environment unavailable: " + args.game)

        class Adapter:
            @property
            def observation_space(self):
                return env.observation_space

            @property
            def action_space(self):
                return env.action_space

            def reset(self):
                return env.reset()

            def step(self, action):
                kind, data = decode(action)
                return env.step(kind, data=data)

            def close(self):
                return arcade.close_scorecard()

        return Adapter()

    first = factory()
    public_initial_sha256 = digest(observation(first.observation_space))
    actions, unsupported = action_catalog(
        first.action_space,
        first.observation_space,
        args.stride,
        args.max_grounded_actions,
    )
    first.close()
    if not actions:
        raise QualificationError(
            "unsupported public action interface: " + repr(tuple(unsupported))
        )

    gate = LeanGate(
        lean=args.lean,
        lean_path=Path(args.lean_path),
        certificate_path=Path(args.certificate),
    )
    result = qualify_transfer(
        factory=factory,
        actions=actions,
        discover_levels=discover_levels,
        execute_stage=execute_stage,
        gate=gate,
        budget=args.max_actions,
        max_episodes=args.max_episodes,
        max_depth=args.max_depth,
        max_training_actions=args.max_training_actions,
        max_levels=args.max_levels,
    )
    result.update(
        {
            "game": args.game,
            "mode": "offline",
            "competition_submission": False,
            "model_calls": 0,
            "public_initial_sha256": public_initial_sha256,
            "grounded_actions": len(actions),
            "unsupported_action_ids": tuple(unsupported),
            "bounds": {
                "max_actions": args.max_actions,
                "max_episodes": args.max_episodes,
                "max_depth": args.max_depth,
                "max_training_actions": args.max_training_actions,
                "max_levels": args.max_levels,
                "stride": args.stride,
                "max_grounded_actions": args.max_grounded_actions,
            },
            "frozen_sources": {
                "shared_runtime_parent": FROZEN_SHARED_RUNTIME_COMMIT,
                "arc3_harness": FROZEN_HARNESS_COMMIT,
                "upstream_arc": UPSTREAM_ARC_COMMIT,
                "arc_agi": ARC_PACKAGE_VERSION,
            },
        }
    )
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print(result["retained"]["gate_marker"])
    summary = {
        "status": result["status"],
        "game": result["game"],
        "grounded_actions": result["grounded_actions"],
        "candidate_sha256": result["retained"]["program_sha256"],
        "certificate_sha256": result["retained"]["certificate_sha256"],
        "cold_levels": result["cold"]["levels_completed"],
        "replay_levels": result["candidate_replay"]["levels_completed"],
        "warm_levels": result["warm"]["levels_completed"],
        "ablation_levels": result["ablation"]["levels_completed"],
        "improved": result["improved"],
    }
    print("ARC3_SHARED_RUNTIME_TRANSFER=" + json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except QualificationError as error:
        print("ARC3_SHARED_RUNTIME_REJECTED=" + str(error), file=sys.stderr)
        raise SystemExit(2)

from __future__ import annotations

import argparse
from pathlib import Path

MODULE = r'''from __future__ import annotations

from pathlib import Path
from typing import Any

from inference.agent.flash_agent import _action_dict
from inference.agent.quotient_atlas_v4 import QuotientAtlasV4Agent
from inference.agent.runtime_state import load_runtime_state
from inference.agent.tool_agent import AnalyzerTurnResult

FROZEN_RUN = 35811403514
FROZEN_HEAD = "32e173c1e53d59595eccaeb232466e2e2bf34ac5"
FROZEN_ARTIFACT = 10730520693
FROZEN_DIGEST = "sha256:06818d392456c7979f252a2d6bf9ab66059a6d0e1102145ef62e2704a21002b9"
LAW = "repeat:changed_continue=>protected_progress"
BOOTSTRAP = {
    1: [("MOUSE", 3, 3)] * 4,
    2: [("MOUSE", 3, 3)] * 8,
}


class FrozenGenesisV4bAgent(QuotientAtlasV4Agent):
    """Admit sealed V3 lineage, then test fresh consequence-law transfer at level 3+.

    Levels 1-2 are deterministic historical replay and can never earn transfer
    credit.  The fresh test starts only after the environment reaches level 3.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._fg_session = None
        self._fg_bootstrap_failed = False
        self._fg_admitted = False
        self._fg_fresh_started = False

    def _ensure_session(self, state_path: Path) -> None:
        super()._ensure_session(state_path)
        if self._fg_session != self._session_runtime_dir:
            self._fg_session = self._session_runtime_dir
            self._fg_bootstrap_failed = False
            self._fg_admitted = False
            self._fg_fresh_started = False
            self._dt_append("FROZEN_GENESIS_RESET", {
                "source_run": FROZEN_RUN,
                "source_head": FROZEN_HEAD,
                "source_artifact": FROZEN_ARTIFACT,
                "source_digest": FROZEN_DIGEST,
                "fresh_boundary": "level>=3",
            })

    def _bootstrap_level(self, state_path, level, valid_actions, step_env):
        program = BOOTSTRAP[int(level)]
        used = 0
        progressed = False
        for key in program:
            before, _ = load_runtime_state(state_path)
            if before is None or int(before.level) != int(level):
                progressed = before is not None and int(before.level) > int(level)
                break
            raw = step_env({"actions": [_action_dict(key)]})
            if not isinstance(raw, dict) or not raw.get("executed"):
                self._fg_bootstrap_failed = True
                self._dt_append("FROZEN_REPLAY_MISMATCH", {
                    "level": int(level), "used": used,
                    "reason": "historical bootstrap action did not execute",
                })
                break
            used += int(raw.get("executed_count") or 1)
            effect = self._record(before, valid_actions, "frozen:mouse(3,3)", raw, "frozen-lineage-replay")
            self._dt_append("FROZEN_REPLAY_ACTION", {
                "level": int(level), "index": used,
                "effect": effect,
                "transfer_credit": False,
            })
            if raw.get("level_completed") or raw.get("run_complete"):
                progressed = True
                break
            if raw.get("game_over") or not raw.get("board_changed"):
                self._fg_bootstrap_failed = True
                self._dt_append("FROZEN_REPLAY_MISMATCH", {
                    "level": int(level), "used": used,
                    "effect": effect,
                    "reason": "sealed successful prefix failed to replay exactly",
                })
                break

        after, _ = load_runtime_state(state_path)
        if after is not None and int(after.level) > int(level):
            progressed = True

        expected = len(program)
        if not progressed or used != expected:
            self._fg_bootstrap_failed = True
            self._dt_append("FROZEN_REPLAY_MISMATCH", {
                "level": int(level), "used": used, "expected": expected,
                "progressed": bool(progressed),
                "reason": "bootstrap did not reproduce the sealed prefix boundary",
            })
        else:
            self._dt_append("FROZEN_REPLAY_PASS", {
                "level": int(level), "actions": used,
                "transfer_credit": False,
            })
        return used, progressed

    def _admit_frozen_capability(self):
        if self._fg_admitted:
            return
        self._fg_admitted = True
        self._qa_live = {
            "first_level": 1,
            "verified_level": 2,
            "witnesses": ["mouse:leftmost"],
            "source": "sealed-v3-lineage",
        }
        self._dt_append("ATLAS_CAPABILITY", {
            "identity": "consequence-law",
            "law": LAW,
            "first_level": 1,
            "verified_level": 2,
            "historical_role_witnesses": ["mouse:uncompiled-coordinate", "mouse:leftmost"],
            "executable_witness": "mouse:leftmost",
            "source_run": FROZEN_RUN,
            "source_artifact": FROZEN_ARTIFACT,
            "source_digest": FROZEN_DIGEST,
            "fresh_transfer_boundary": 3,
            "promotion": "admitted prior evidence; not earned by bootstrap replay",
        })

    def analyze(self, state_path: Path, action_num: int, valid_actions=None, step_env=None,
                transcript_path=None, analysis_step=None, transcript_updated=None,
                request_timeout_seconds=None, should_stop=None):
        self._ensure_session(state_path)
        frame, _ = load_runtime_state(state_path)
        if frame is None or step_env is None:
            return super().analyze(
                state_path, action_num, valid_actions=valid_actions, step_env=step_env,
                transcript_path=transcript_path, analysis_step=analysis_step,
                transcript_updated=transcript_updated,
                request_timeout_seconds=request_timeout_seconds, should_stop=should_stop)

        level = int(frame.level)

        # Historical replay only. No learning or transfer credit is possible here.
        if level in BOOTSTRAP and not self._fg_bootstrap_failed:
            used, progressed = self._bootstrap_level(
                state_path, level, valid_actions, step_env
            )
            return AnalyzerTurnResult(
                step_executed=bool(used),
                reasoning=(
                    "Replayed the sealed V3 bootstrap prefix; this phase is excluded "
                    "from transfer credit."
                ),
            )

        if level >= 3 and not self._fg_bootstrap_failed:
            self._admit_frozen_capability()
            if not self._fg_fresh_started:
                self._fg_fresh_started = True
                self._dt_append("FRESH_TRANSFER_BOUNDARY", {
                    "level": level,
                    "law": LAW,
                    "model_calls_before_boundary": 0,
                })

            before_level = level
            used, _ = self._run_stable_role(
                state_path, frame, valid_actions, "mouse:leftmost",
                step_env, max_steps=32
            )
            after, _ = load_runtime_state(state_path)
            after_level = int(after.level) if after is not None else before_level
            progressed = after_level > before_level
            self._dt_append("TRANSFER_EXECUTE", {
                "identity": "consequence-law",
                "law": LAW,
                "witness_role": "mouse:leftmost",
                "source": "sealed-v3-lineage",
                "source_run": FROZEN_RUN,
                "level": before_level,
                "actions": int(used),
                "progressed": bool(progressed),
                "model_call": False,
                "fresh_transfer": True,
            })
            return AnalyzerTurnResult(
                step_executed=bool(used),
                reasoning=(
                    "Executed the admitted consequence-keyed capability at the fresh "
                    "transfer boundary with no model call."
                ),
            )

        # Fail closed scientifically: any recovery is marked as model-assisted and
        # cannot satisfy the compiled-transfer gate.
        self._dt_append("FROZEN_GENESIS_FALLBACK", {
            "level": level,
            "reason": "bootstrap evidence failed; transfer claim invalid",
        })
        return super().analyze(
            state_path, action_num, valid_actions=valid_actions, step_env=step_env,
            transcript_path=transcript_path, analysis_step=analysis_step,
            transcript_updated=transcript_updated,
            request_timeout_seconds=request_timeout_seconds, should_stop=should_stop)
'''


def patch(root: Path) -> None:
    root = root.resolve()
    agent_dir = root / "inference" / "agent"
    solver = root / "inference" / "framework" / "solver.py"
    if not (agent_dir / "quotient_atlas_v4.py").is_file():
        raise SystemExit("apply quotient_atlas_v4_patch.py first")

    target = agent_dir / "frozen_genesis_v4b.py"
    target.write_text(MODULE, encoding="utf-8")

    text = solver.read_text(encoding="utf-8")
    old_import = "from inference.agent.quotient_atlas_v4 import QuotientAtlasV4Agent\n"
    new_import = "from inference.agent.frozen_genesis_v4b import FrozenGenesisV4bAgent\n"
    if old_import not in text and new_import not in text:
        raise SystemExit("V4a import anchor changed")
    text = text.replace(old_import, new_import, 1)

    old_ctor = "        return QuotientAtlasV4Agent(\n"
    new_ctor = "        return FrozenGenesisV4bAgent(\n"
    if old_ctor not in text and new_ctor not in text:
        raise SystemExit("V4a constructor anchor changed")
    text = text.replace(old_ctor, new_ctor, 1)
    solver.write_text(text, encoding="utf-8")

    compile(target.read_text(), str(target), "exec")
    compile(solver.read_text(), str(solver), "exec")
    print("FROZEN_GENESIS_V4B_PATCH=PASS")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    patch(p.parse_args().root)


if __name__ == "__main__":
    main()

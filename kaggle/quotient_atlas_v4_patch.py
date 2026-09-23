from __future__ import annotations
import argparse
from pathlib import Path

MODULE = r'''from __future__ import annotations
from pathlib import Path
from typing import Any
from inference.agent.consequence_first_leaderboard import ConsequenceFirstLeaderboardAgent
from inference.agent.runtime_state import load_runtime_state
from inference.agent.tool_agent import AnalyzerTurnResult

LAW = "repeat:changed_continue=>protected_progress"
STABLE = (0, True, "CONTINUE")

class QuotientAtlasV4Agent(ConsequenceFirstLeaderboardAgent):
    """V4a: capability identity is consequence-law, raw roles are witnesses."""
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._qa_effects = {}
        self._qa_stage = None
        self._qa_live = None
        self._qa_failed = set()

    def _ensure_session(self, state_path: Path) -> None:
        old = getattr(self, "_session_runtime_dir", None)
        super()._ensure_session(state_path)
        if old != self._session_runtime_dir:
            self._qa_effects = {}
            self._qa_stage = None
            self._qa_live = None
            self._qa_failed = set()
            self._dt_append("QUOTIENT_ATLAS_RESET", {
                "principle": "capability identity is protected consequence, not raw role",
                "law": LAW,
                "boundary": "requires >=2 stable changed-continue steps before protected progress on two distinct levels",
            })

    def _record(self, frame, valid_actions, role, raw, phase):
        effect = super()._record(frame, valid_actions, role, raw, phase)
        self._qa_effects.setdefault((int(frame.level), role), []).append(effect)
        return effect

    def _infer(self, role, level):
        es = self._qa_effects.get((int(level), role), [])
        if not es or not (es[-1][0] == 1 and es[-1][1] is True and es[-1][2] in ("LEVEL", "WIN")):
            return None
        tail = 0
        for e in reversed(es[:-1]):
            if e == STABLE:
                tail += 1
            else:
                break
        return tail if tail >= 2 else None

    def _stage_or_promote(self, role, source_level):
        tail = self._infer(role, source_level)
        if tail is None:
            self._dt_append("QUOTIENT_RESIDUAL", {
                "level": int(source_level), "role": role,
                "reason": "progress did not instantiate the frozen recurrence law",
            })
            return
        ev = {"level": int(source_level), "role": role, "stable_tail": int(tail)}
        if self._qa_stage is None:
            self._qa_stage = {"first_level": int(source_level), "witnesses": [role], "evidence": [ev]}
            self._dt_append("ATLAS_STAGE", {
                "identity": "consequence-law", "law": LAW, **ev,
            })
            return
        if role not in self._qa_stage["witnesses"]:
            self._qa_stage["witnesses"].append(role)
        self._qa_stage["evidence"].append(ev)
        if int(source_level) != self._qa_stage["first_level"] and self._qa_live is None:
            self._qa_live = {
                "first_level": self._qa_stage["first_level"],
                "verified_level": int(source_level),
                "witnesses": list(self._qa_stage["witnesses"]),
            }
            self._dt_append("ATLAS_CAPABILITY", {
                "identity": "consequence-law", "law": LAW,
                "first_level": self._qa_live["first_level"],
                "verified_level": self._qa_live["verified_level"],
                "witnesses": self._qa_live["witnesses"],
                "guard": "witness role resolves; bounded 16-step execution; fail closed",
            })
        elif self._qa_live is not None:
            if role not in self._qa_live["witnesses"]:
                self._qa_live["witnesses"].append(role)
            self._dt_append("ATLAS_REQUALIFY", {"law": LAW, **ev})

    def _revoke(self, role, frame, reason):
        if self._qa_live is not None and role in self._qa_live.get("witnesses", []):
            self._qa_failed.add((int(frame.level), role))
            self._dt_append("QUOTIENT_RESIDUAL", {
                "level": int(frame.level), "law": LAW, "witness_role": role,
                "reason": reason,
            })
        super()._revoke(role, frame, reason)

    def analyze(self, state_path: Path, action_num: int, valid_actions=None, step_env=None,
                transcript_path=None, analysis_step=None, transcript_updated=None,
                request_timeout_seconds=None, should_stop=None):
        self._ensure_session(state_path)
        frame, _ = load_runtime_state(state_path)
        if frame is not None and step_env is not None and self._qa_live is not None:
            level = int(frame.level)
            for role in reversed(self._qa_live.get("witnesses", [])):
                if (level, role) in self._qa_failed or self._resolve_role(frame, role) is None:
                    continue
                used, _ = self._run_stable_role(state_path, frame, valid_actions, role, step_env, max_steps=16)
                if not used:
                    continue
                after, _ = load_runtime_state(state_path)
                after_level = int(after.level) if after is not None else level
                progressed = after_level != level
                if not progressed and int(used) >= 16:
                    self._qa_failed.add((level, role))
                    self._dt_append("QUOTIENT_RESIDUAL", {
                        "level": level, "law": LAW, "witness_role": role,
                        "reason": "16-step bounded compiled recurrence did not reach protected progress",
                    })
                self._dt_append("TRANSFER_EXECUTE", {
                    "identity": "consequence-law", "law": LAW, "witness_role": role,
                    "level": level, "actions": int(used), "progressed": bool(progressed),
                    "model_call": False,
                })
                return AnalyzerTurnResult(step_executed=True,
                    reasoning="Executed consequence-keyed capability without a model call.")
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
    if not (agent_dir / "consequence_first_leaderboard.py").is_file():
        raise SystemExit("apply consequence_first_leaderboard_patch.py first")
    target = agent_dir / "quotient_atlas_v4.py"
    target.write_text(MODULE, encoding="utf-8")
    text = solver.read_text(encoding="utf-8")
    old_i = "from inference.agent.consequence_first_leaderboard import ConsequenceFirstLeaderboardAgent\n"
    new_i = "from inference.agent.quotient_atlas_v4 import QuotientAtlasV4Agent\n"
    if old_i not in text and new_i not in text:
        raise SystemExit("V3 import anchor changed")
    text = text.replace(old_i, new_i, 1)
    old_c = "        return ConsequenceFirstLeaderboardAgent(\n"
    new_c = "        return QuotientAtlasV4Agent(\n"
    if old_c not in text and new_c not in text:
        raise SystemExit("V3 constructor anchor changed")
    text = text.replace(old_c, new_c, 1)
    solver.write_text(text, encoding="utf-8")
    compile(target.read_text(), str(target), "exec")
    compile(solver.read_text(), str(solver), "exec")
    print("QUOTIENT_ATLAS_V4_PATCH=PASS")

def main():
    p = argparse.ArgumentParser(); p.add_argument("--root", type=Path, required=True)
    patch(p.parse_args().root)

if __name__ == "__main__": main()

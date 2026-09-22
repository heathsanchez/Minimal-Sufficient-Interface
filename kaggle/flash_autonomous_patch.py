from __future__ import annotations

import argparse
from pathlib import Path

MODULE = r'''from __future__ import annotations

from collections import Counter, deque
from itertools import cycle, islice
from pathlib import Path
from typing import Any

from inference.agent.runtime_state import Frame, load_runtime_state
from inference.agent.tool_agent import AnalyzerTurnResult
from inference.agent.action_names import to_engine_action, to_model_action
from inference.agent.flash_agent import FlashToolAgent, _action_dict


_ACTION_ORDER = ("DOWN", "LEFT", "RIGHT", "SPACE", "UP")


def _components(grid: tuple[tuple[int, ...], ...]) -> list[tuple[int,int,int,int,int,int]]:
    if not grid:
        return []
    rows, cols = len(grid), len(grid[0])
    total = rows * cols
    seen = set()
    out = []
    for r in range(rows):
        for c in range(cols):
            if (r,c) in seen:
                continue
            color = grid[r][c]
            q = deque([(r,c)])
            seen.add((r,c))
            cells = []
            while q:
                rr,cc = q.popleft()
                cells.append((rr,cc))
                for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
                    nr,nc = rr+dr,cc+dc
                    if 0 <= nr < rows and 0 <= nc < cols and (nr,nc) not in seen and grid[nr][nc] == color:
                        seen.add((nr,nc)); q.append((nr,nc))
            # Background and letterbox are large connected regions.  Do not
            # exclude colors by frequency: on sparse boards a real target can
            # be the second-most-common color and would be silently erased.
            if len(cells) > max(16, total // 4):
                continue
            rs=[x[0] for x in cells]; cs=[x[1] for x in cells]
            out.append((min(cs), min(rs), max(cs), max(rs), color, len(cells)))
    return sorted(out, key=lambda x:(x[0],x[1],x[4],x[5]))


class AutonomousFlashToolAgent(FlashToolAgent):
    """Flash with a deterministic residual probe before any model call.

    The probe is deliberately domain-light:
      * discrete actions: try the first unrefuted legal action under a frozen order;
      * mouse-only state: click the leftmost small non-background component.

    If one probe changes the board without terminal failure, repeat that same
    action until a boundary.  Success is staged as a candidate and must still
    pass the Metatron shadow qualification before it can become a reusable
    capability.  Failure is recorded and the next probe/model handles the
    residual.
    """

    def _probe_key(self, frame: Frame, valid_actions: list[str] | None):
        # HarnessSolver supplies engine labels (ACTION3/ACTION6), while the
        # probe language is model-facing (LEFT/MOUSE). Normalize at the adapter
        # boundary so mouse games do not silently fall through to malformed
        # generic actions.
        valid = {
            to_model_action(to_engine_action(str(x)) or str(x))
            for x in (valid_actions or [])
            if str(x).strip()
        }
        rejected = {
            tuple(dict(e["payload"]).get("action", ()))
            for e in self._dt_events("PROBE_REJECT")
            if int(dict(e["payload"]).get("level", -1)) == int(frame.level)
        }
        if valid == {"MOUSE"}:
            for x0,y0,x1,y1,color,area in _components(frame.grid):
                # Click component center in row/col coordinates.
                key = ("MOUSE", (y0+y1)//2, (x0+x1)//2)
                if key not in rejected:
                    return key
            return None

        ordered = [a for a in _ACTION_ORDER if a in valid] + sorted(valid - set(_ACTION_ORDER))
        for action in ordered:
            key=(action,)
            if key not in rejected:
                return key
        return None

    def _probe_residual(self, frame: Frame, valid_actions: list[str] | None, step_env):
        key = self._probe_key(frame, valid_actions)
        if key is None:
            return None

        first = step_env({"actions":[_action_dict(key)]})
        if not isinstance(first, dict) or not first.get("executed"):
            return None

        if first.get("game_over"):
            self._dt_append("PROBE_REJECT", {
                "level": int(frame.level), "action": key, "reason": "GAME_OVER"
            })
            return AnalyzerTurnResult(step_executed=True, reasoning="Flash probe falsified.")

        used = [key] * int(first.get("executed_count") or 1)
        final = first

        if not first.get("level_completed") and not first.get("run_complete") and first.get("board_changed"):
            # Progressive compilation candidate: same action until the next
            # environment boundary. step_env itself stops at level completion.
            tail = tuple(islice(cycle((key,)), 63))
            final = step_env({"actions":[_action_dict(k) for k in tail]})
            if isinstance(final, dict):
                used.extend([key] * int(final.get("executed_count") or 0))

        if isinstance(final, dict) and (final.get("level_completed") or final.get("run_complete")):
            program = tuple(used)
            source_level = int(frame.level)
            self._stage_and_maybe_promote(program, source_level)
            self._dt_completed_programs.append(program)
            self._dt_append("PROBE_COMPILE", {
                "source_level": source_level,
                "action": key,
                "program_len": len(program),
                "qualified_after_probe": True,
            })
            return AnalyzerTurnResult(
                step_executed=True,
                reasoning="Flash resolved residual by probe, qualified it, and compiled it; no model call."
            )

        if isinstance(final, dict) and final.get("game_over"):
            self._dt_append("PROBE_REJECT", {
                "level": int(frame.level), "action": key, "reason": "GAME_OVER_AFTER_REPEAT"
            })
            return AnalyzerTurnResult(step_executed=True, reasoning="Flash probe falsified after repeat.")

        self._dt_append("PROBE_INCONCLUSIVE", {
            "level": int(frame.level), "action": key,
        })
        return AnalyzerTurnResult(step_executed=True, reasoning="Flash probe was inconclusive.")

    def analyze(
        self,
        state_path: Path,
        action_num: int,
        valid_actions: list[str] | None = None,
        step_env=None,
        transcript_path: Path | None = None,
        analysis_step: int | None = None,
        transcript_updated=None,
        request_timeout_seconds: float | None = None,
        should_stop=None,
    ) -> AnalyzerTurnResult | None:
        self._ensure_session(state_path)
        frame, _ = load_runtime_state(state_path)

        # First preserve Flash's strongest invariant: execute a qualified
        # capability directly if one already resolves the current residual.
        active = self._active_flash_capability(frame)
        if active is not None and step_env is not None:
            capability_event, generator, certified_steps = active
            keys = tuple(islice(cycle(generator), certified_steps))
            raw = step_env({"actions":[_action_dict(k) for k in keys]})
            if isinstance(raw, dict):
                self._record_direct_progress(
                    before_frame=frame,
                    capability_event=capability_event,
                    action_keys=keys,
                    raw=raw,
                )
                if raw.get("executed"):
                    return AnalyzerTurnResult(
                        step_executed=True,
                        reasoning="Flash direct-executed a qualified capability; zero model call."
                    )

        # If no capability exists, buy one minimal piece of information before
        # paying the model.
        if frame is not None and step_env is not None:
            probe = self._probe_residual(frame, valid_actions, step_env)
            if probe is not None:
                return probe

        # Only the genuinely unresolved residual reaches Duck/Qwen.
        return super().analyze(
            state_path,
            action_num,
            valid_actions=valid_actions,
            step_env=step_env,
            transcript_path=transcript_path,
            analysis_step=analysis_step,
            transcript_updated=transcript_updated,
            request_timeout_seconds=request_timeout_seconds,
            should_stop=should_stop,
        )
'''


def patch(root: Path) -> None:
    root = root.resolve()
    agent_dir = root / "inference" / "agent"
    solver = root / "inference" / "framework" / "solver.py"
    if not (agent_dir / "flash_agent.py").is_file():
        raise SystemExit("apply flash_ducktape_patch.py first")

    (agent_dir / "flash_autonomous.py").write_text(MODULE, encoding="utf-8")

    text = solver.read_text(encoding="utf-8")
    old_import = "from inference.agent.flash_agent import FlashToolAgent\n"
    new_import = "from inference.agent.flash_autonomous import AutonomousFlashToolAgent\n"
    if old_import not in text and new_import not in text:
        raise SystemExit("Flash solver import anchor changed")
    text = text.replace(old_import, new_import, 1)

    old_ctor = "        return FlashToolAgent(\n"
    new_ctor = "        return AutonomousFlashToolAgent(\n"
    if old_ctor not in text and new_ctor not in text:
        raise SystemExit("Flash constructor anchor changed")
    text = text.replace(old_ctor, new_ctor, 1)
    solver.write_text(text, encoding="utf-8")

    compile((agent_dir / "flash_autonomous.py").read_text(), str(agent_dir / "flash_autonomous.py"), "exec")
    compile(solver.read_text(), str(solver), "exec")
    print("FLASH_AUTONOMOUS_PATCH=PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    patch(args.root)


if __name__ == "__main__":
    main()

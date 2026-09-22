from __future__ import annotations

import argparse
from pathlib import Path

MODULE = r'''from __future__ import annotations

from collections import Counter, deque
from pathlib import Path
from typing import Any

from inference.agent.action_names import to_engine_action, to_model_action
from inference.agent.flash_agent import FlashToolAgent, _action_dict
from inference.agent.runtime_state import Frame, load_runtime_state
from inference.agent.tool_agent import AnalyzerTurnResult


def _components(grid):
    if not grid:
        return []
    rows, cols = len(grid), len(grid[0])
    total = rows * cols
    seen = set()
    out = []
    for r in range(rows):
        for c in range(cols):
            if (r, c) in seen:
                continue
            color = grid[r][c]
            q = deque([(r, c)])
            seen.add((r, c))
            cells = []
            while q:
                rr, cc = q.popleft()
                cells.append((rr, cc))
                for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
                    nr, nc = rr + dr, cc + dc
                    if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in seen and grid[nr][nc] == color:
                        seen.add((nr, nc))
                        q.append((nr, nc))
            if len(cells) > max(16, total // 4):
                continue
            rs = [x[0] for x in cells]
            cs = [x[1] for x in cells]
            out.append({
                "x0": min(cs), "y0": min(rs), "x1": max(cs), "y1": max(rs),
                "color": color, "area": len(cells),
            })
    return out


def _valid(valid_actions):
    names = []
    for raw in valid_actions or []:
        name = to_model_action(to_engine_action(str(raw)) or str(raw))
        if name and name not in names:
            names.append(name)
    return names


def _effect(raw):
    if raw.get("run_complete"):
        terminal = "WIN"
    elif raw.get("game_over"):
        terminal = "GAME_OVER"
    elif raw.get("level_completed"):
        terminal = "LEVEL"
    else:
        terminal = "CONTINUE"
    return (
        1 if (raw.get("level_completed") or raw.get("run_complete")) else 0,
        bool(raw.get("board_changed")),
        terminal,
    )


class ConsequenceNucleusAgent(FlashToolAgent):
    """Consequence-first ARC controller.

    Lineage records episodes. Executable memory stores only causal roles that
    continue to work across distinct levels. Mouse capabilities are symbolic
    selectors such as mouse:leftmost, never remembered coordinates.

    The system first tests whether an intervention has a stable consequence.
    Only then may it repeat/compile it. A failure creates a residual and removes
    the live law rather than adding an exception to the policy.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._cn_level_seen = {}
        self._cn_tried = {}
        self._cn_staged = {}
        self._cn_live = {}
        self._cn_lineage_count = 0
        self._cn_ledger = {}

    def _ensure_session(self, state_path: Path) -> None:
        previous = self._session_runtime_dir
        super()._ensure_session(state_path)
        if previous != self._session_runtime_dir:
            self._cn_level_seen = {}
            self._cn_tried = {}
            self._cn_staged = {}
            self._cn_live = {}
            self._cn_lineage_count = 0
            self._cn_ledger = {}
            self._dt_append("NUCLEUS_RESET", {"principle": "remember what works, not what worked"})

    def _surface_summary(self, frame: Frame, valid_actions):
        comps = _components(frame.grid)
        areas = sorted(c["area"] for c in comps)
        boxes = sorted((c["x1"]-c["x0"]+1, c["y1"]-c["y0"]+1) for c in comps)
        return {
            "shape": tuple(frame.shape),
            "component_count": len(comps),
            "area_multiset": tuple(areas[:12]),
            "box_multiset": tuple(boxes[:12]),
            "actions": tuple(sorted(_valid(valid_actions))),
        }

    def _record(self, frame, valid_actions, role, raw, phase):
        effect = _effect(raw)
        self._cn_lineage_count += 1
        bucket = self._cn_ledger.setdefault(role, Counter())
        bucket[effect] += 1
        self._dt_append("CAUSAL_EPISODE", {
            "episode": self._cn_lineage_count,
            "level": int(frame.level),
            "role": role,
            "effect": effect,
            "phase": phase,
            "surface": self._surface_summary(frame, valid_actions),
        })
        return effect

    def _mouse_role_key(self, frame, role):
        comps = _components(frame.grid)
        if not comps:
            return None
        if role == "mouse:leftmost":
            c = min(comps, key=lambda z: (z["x0"], z["y0"], z["area"]))
        elif role == "mouse:rightmost":
            c = max(comps, key=lambda z: (z["x1"], -z["y0"], -z["area"]))
        elif role == "mouse:topmost":
            c = min(comps, key=lambda z: (z["y0"], z["x0"], z["area"]))
        elif role == "mouse:bottommost":
            c = max(comps, key=lambda z: (z["y1"], -z["x0"], -z["area"]))
        elif role == "mouse:smallest":
            c = min(comps, key=lambda z: (z["area"], z["x0"], z["y0"]))
        elif role == "mouse:largest":
            c = max(comps, key=lambda z: (z["area"], -z["x0"], -z["y0"]))
        else:
            return None
        row = (c["y0"] + c["y1"]) // 2
        col = (c["x0"] + c["x1"]) // 2
        return ("MOUSE", row, col)

    def _resolve_role(self, frame, role):
        if role.startswith("primitive:"):
            return (role.split(":", 1)[1],)
        if role.startswith("mouse:"):
            return self._mouse_role_key(frame, role)
        return None

    def _roles(self, frame, valid_actions):
        valid = _valid(valid_actions)
        roles = []
        for name in valid:
            if name != "MOUSE":
                roles.append("primitive:" + name)
        if "MOUSE" in valid:
            for role in (
                "mouse:leftmost", "mouse:rightmost", "mouse:topmost",
                "mouse:bottommost", "mouse:smallest", "mouse:largest",
            ):
                if self._resolve_role(frame, role) is not None:
                    roles.append(role)
        # Different symbolic roles may resolve to the same current coordinate.
        # Keep one representative now; the role can resolve differently later.
        seen_keys = set()
        out = []
        for role in roles:
            key = self._resolve_role(frame, role)
            if key is None or key in seen_keys:
                continue
            seen_keys.add(key)
            out.append(role)
        return out

    def _stage_or_promote(self, role, source_level):
        if role in self._cn_live:
            return
        staged = self._cn_staged.get(role)
        if staged is None:
            self._cn_staged[role] = int(source_level)
            self._dt_append("ATLAS_STAGE", {
                "role": role,
                "source_level": int(source_level),
                "claim": "candidate causal role progressed once",
            })
            return
        if int(staged) != int(source_level):
            self._cn_live[role] = {
                "first_level": int(staged),
                "verified_level": int(source_level),
            }
            self._dt_append("ATLAS_CAPABILITY", {
                "role": role,
                "first_level": int(staged),
                "verified_level": int(source_level),
                "guard": "role resolvable under current action interface",
                "memory": "causal role, not episode coordinates",
            })

    def _revoke(self, role, frame, reason):
        if role in self._cn_live:
            old = self._cn_live.pop(role)
            self._dt_append("ATLAS_REVOKE", {
                "role": role,
                "level": int(frame.level),
                "reason": reason,
                "previous_warrant": old,
            })
        self._dt_append("REPRESENTATION_RESIDUAL", {
            "role": role,
            "level": int(frame.level),
            "reason": reason,
            "instruction": "invent a new distinction only if consequence requires it",
        })

    def _execute_once(self, state_path, frame, valid_actions, role, step_env, phase):
        key = self._resolve_role(frame, role)
        if key is None:
            return None, None
        raw = step_env({"actions": [_action_dict(key)]})
        if not isinstance(raw, dict) or not raw.get("executed"):
            return None, None
        effect = self._record(frame, valid_actions, role, raw, phase)
        return raw, effect

    def _run_stable_role(self, state_path, frame, valid_actions, role, step_env, max_steps):
        used = 0
        last_effect = None
        while used < max_steps:
            current, _ = load_runtime_state(state_path)
            if current is None:
                break
            raw, effect = self._execute_once(
                state_path, current, valid_actions, role, step_env, "compiled"
            )
            if raw is None:
                break
            used += int(raw.get("executed_count") or 1)
            last_effect = effect
            if raw.get("level_completed") or raw.get("run_complete"):
                self._stage_or_promote(role, int(current.level))
                self._dt_append("FLASH_RECLOSE", {
                    "resolved_level": int(current.level),
                    "role": role,
                    "model_call": False,
                    "source": "consequential-nucleus",
                })
                break
            if raw.get("game_over"):
                self._revoke(role, current, "previously live causal role reached GAME_OVER")
                break
            if not raw.get("board_changed"):
                self._revoke(role, current, "causal role stopped changing protected observable state")
                break
        return used, last_effect

    def _probe_role(self, state_path, frame, valid_actions, role, step_env):
        raw1, effect1 = self._execute_once(
            state_path, frame, valid_actions, role, step_env, "separator-1"
        )
        if raw1 is None:
            return None
        if raw1.get("level_completed") or raw1.get("run_complete"):
            self._stage_or_promote(role, int(frame.level))
            return AnalyzerTurnResult(step_executed=True, reasoning="A causal role directly produced progress.")
        if raw1.get("game_over"):
            self._revoke(role, frame, "separator reached GAME_OVER")
            return AnalyzerTurnResult(step_executed=True, reasoning="Causal separator falsified this role.")
        if not raw1.get("board_changed"):
            return AnalyzerTurnResult(step_executed=True, reasoning="Causal separator produced no protected change.")

        frame2, _ = load_runtime_state(state_path)
        if frame2 is None:
            return AnalyzerTurnResult(step_executed=True, reasoning="One causal transition observed.")
        raw2, effect2 = self._execute_once(
            state_path, frame2, valid_actions, role, step_env, "separator-2"
        )
        if raw2 is None:
            return AnalyzerTurnResult(step_executed=True, reasoning="One causal transition observed.")
        if raw2.get("level_completed") or raw2.get("run_complete"):
            self._stage_or_promote(role, int(frame.level))
            self._dt_append("LOCAL_CAUSAL_LAW", {
                "role": role,
                "evidence": [effect1, effect2],
                "law": "repeat role while it continues to realize the same protected change",
            })
            return AnalyzerTurnResult(step_executed=True, reasoning="Repeated causal effect reached progress and was staged.")
        if raw2.get("game_over"):
            self._revoke(role, frame2, "second separator contradicted first transition")
            return AnalyzerTurnResult(step_executed=True, reasoning="Second causal separator falsified repetition.")

        if effect1 == effect2 and effect1[1] is True:
            self._dt_append("LOCAL_CAUSAL_LAW", {
                "role": role,
                "evidence": [effect1, effect2],
                "law": "repeat role while same protected consequence continues",
            })
            self._run_stable_role(state_path, frame2, valid_actions, role, step_env, max_steps=30)
            return AnalyzerTurnResult(step_executed=True, reasoning="Stable causal law was executed until its consequence changed.")

        self._dt_append("REPRESENTATION_RESIDUAL", {
            "role": role,
            "level": int(frame.level),
            "reason": "same symbolic intervention produced non-stable consequences",
        })
        return AnalyzerTurnResult(step_executed=True, reasoning="Transition changed; representation residual recorded.")

    def _projection(self):
        lines = [
            "",
            "Consequential Nucleus live state:",
            f"- lineage_events={self._cn_lineage_count}",
            f"- live_causal_capabilities={len(self._cn_live)}",
            f"- staged_roles={len(self._cn_staged)}",
            "- representations are hypotheses; consequences are authority",
            "- use history to invent a new distinction only when current distinctions collapse different consequences",
        ]
        for role, warrant in sorted(self._cn_live.items()):
            lines.append(f"- works now: {role} under resolvability guard; warrant={warrant}")
        for role, counts in sorted(self._cn_ledger.items()):
            compact = ", ".join(f"{k}:{v}" for k, v in counts.most_common(4))
            lines.append(f"- causal evidence {role}: {compact}")
        return "\n".join(lines)

    def _build_user_prompt(self, *args, **kwargs):
        return super()._build_user_prompt(*args, **kwargs) + self._projection()

    def analyze(
        self,
        state_path: Path,
        action_num: int,
        valid_actions=None,
        step_env=None,
        transcript_path=None,
        analysis_step=None,
        transcript_updated=None,
        request_timeout_seconds=None,
        should_stop=None,
    ):
        self._ensure_session(state_path)
        frame, _ = load_runtime_state(state_path)

        # Existing Metatron-qualified exact capability still has precedence.
        active = self._active_flash_capability(frame)
        if active is not None:
            return FlashToolAgent.analyze(
                self, state_path, action_num, valid_actions=valid_actions,
                step_env=step_env, transcript_path=transcript_path,
                analysis_step=analysis_step, transcript_updated=transcript_updated,
                request_timeout_seconds=request_timeout_seconds, should_stop=should_stop,
            )

        if frame is not None and step_env is not None:
            # What works: live causal roles are applied by symbolic role, not replayed coordinates.
            for role in list(self._cn_live):
                if self._resolve_role(frame, role) is not None:
                    used, _ = self._run_stable_role(
                        state_path, frame, valid_actions, role, step_env, max_steps=64
                    )
                    if used:
                        return AnalyzerTurnResult(
                            step_executed=True,
                            reasoning="Executed a currently warranted causal capability.",
                        )

            level = int(frame.level)
            tried = self._cn_tried.setdefault(level, set())

            # A once-successful role gets the first fresh test on a new surface.
            staged_roles = [
                r for r, source in self._cn_staged.items()
                if source != level and r not in tried and self._resolve_role(frame, r) is not None
            ]
            candidates = staged_roles + [
                r for r in self._roles(frame, valid_actions) if r not in tried and r not in staged_roles
            ]
            if candidates:
                role = candidates[0]
                tried.add(role)
                result = self._probe_role(state_path, frame, valid_actions, role, step_env)
                if result is not None:
                    return result

        # Current causal language is exhausted. Escalate to fluid cognition with
        # only the consequential summary retained as memory.
        self._dt_append("NEBULA_ESCALATE", {
            "level": int(frame.level) if frame is not None else None,
            "reason": "no current causal role resolves the residual",
            "request": "propose a new distinction or intervention; do not retrieve an old episode",
        })
        return FlashToolAgent.analyze(
            self, state_path, action_num, valid_actions=valid_actions,
            step_env=step_env, transcript_path=transcript_path,
            analysis_step=analysis_step, transcript_updated=transcript_updated,
            request_timeout_seconds=request_timeout_seconds, should_stop=should_stop,
        )
'''


def patch(root: Path) -> None:
    root = root.resolve()
    agent_dir = root / "inference" / "agent"
    solver = root / "inference" / "framework" / "solver.py"
    if not (agent_dir / "flash_agent.py").is_file():
        raise SystemExit("apply flash_ducktape_patch.py first")

    target = agent_dir / "consequence_nucleus.py"
    target.write_text(MODULE, encoding="utf-8")

    text = solver.read_text(encoding="utf-8")
    old_import = "from inference.agent.flash_agent import FlashToolAgent\n"
    new_import = "from inference.agent.consequence_nucleus import ConsequenceNucleusAgent\n"
    if old_import not in text and new_import not in text:
        raise SystemExit("Flash solver import anchor changed")
    text = text.replace(old_import, new_import, 1)

    old_ctor = "        return FlashToolAgent(\n"
    new_ctor = "        return ConsequenceNucleusAgent(\n"
    if old_ctor not in text and new_ctor not in text:
        raise SystemExit("Flash constructor anchor changed")
    text = text.replace(old_ctor, new_ctor, 1)
    solver.write_text(text, encoding="utf-8")

    compile(target.read_text(), str(target), "exec")
    compile(solver.read_text(), str(solver), "exec")
    print("CONSEQUENCE_NUCLEUS_PATCH=PASS")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, required=True)
    a = p.parse_args()
    patch(a.root)


if __name__ == "__main__":
    main()

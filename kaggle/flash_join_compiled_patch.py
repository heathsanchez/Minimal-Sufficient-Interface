from __future__ import annotations

import argparse
from pathlib import Path

MODULE = r'''from __future__ import annotations

from typing import Any

from inference.agent.flash_autonomous import AutonomousFlashToolAgent, _components


ADMITTED_JOIN_LAWS = (
    {
        "guard": {"valid_actions": ("MOUSE",), "bbox": (2, 2), "area": 3},
        "feature": "mask",
        "value": "11/10",
        "evidence": {
            "separator_run": 35686312976,
            "separator_job": 106613761328,
            "decision": "ADMIT_JOIN_HOOK",
            "passing_trials": 3,
            "evidence_label": "PROSPECTIVE_FROZEN",
        },
    },
)


def _mask(grid: tuple[tuple[int, ...], ...], x0: int, y0: int, x1: int, y1: int, color: int) -> str:
    rows = []
    for y in range(y0, y1 + 1):
        rows.append(
            "".join("1" if grid[y][x] == color else "0" for x in range(x0, x1 + 1))
        )
    return "/".join(rows)


class JoinCompiledFlashToolAgent(AutonomousFlashToolAgent):
    """Autonomous Flash plus one admitted JOIN law compiled downward.

    No model call is made for the law itself. The semantic model proposed the
    law during the external separator experiment; only the verified law is
    retained here, with a narrow guard. If the guard does not match, control
    falls back to the pre-existing Autonomous Flash policy unchanged.
    """

    def _probe_key(self, frame, valid_actions):
        valid = {str(x).strip().upper() for x in (valid_actions or [])}
        if valid == {"MOUSE"}:
            rejected = {
                tuple(dict(e["payload"]).get("action", ()))
                for e in self._dt_events("PROBE_REJECT")
                if int(dict(e["payload"]).get("level", -1)) == int(frame.level)
            }

            for law in ADMITTED_JOIN_LAWS:
                guard = law["guard"]
                if tuple(sorted(valid)) != tuple(sorted(guard["valid_actions"])):
                    continue

                for x0, y0, x1, y1, color, area in _components(frame.grid):
                    width = x1 - x0 + 1
                    height = y1 - y0 + 1
                    if (width, height) != tuple(guard["bbox"]):
                        continue
                    if int(area) != int(guard["area"]):
                        continue

                    observed = _mask(frame.grid, x0, y0, x1, y1, color)
                    if observed != law["value"]:
                        continue

                    key = ("MOUSE", (y0 + y1) // 2, (x0 + x1) // 2)
                    if key in rejected:
                        continue

                    self._dt_append(
                        "JOIN_COMPILED_MATCH",
                        {
                            "level": int(frame.level),
                            "law_feature": law["feature"],
                            "law_value": law["value"],
                            "observed": observed,
                            "action": key,
                            "separator_run": law["evidence"]["separator_run"],
                        },
                    )
                    return key

        return super()._probe_key(frame, valid_actions)
'''


def patch(root: Path) -> None:
    root = root.resolve()
    agent_dir = root / "inference" / "agent"
    solver = root / "inference" / "framework" / "solver.py"
    if not (agent_dir / "flash_autonomous.py").is_file():
        raise SystemExit("apply flash_autonomous_patch.py first")

    (agent_dir / "flash_join_compiled.py").write_text(MODULE, encoding="utf-8")

    text = solver.read_text(encoding="utf-8")
    old_import = "from inference.agent.flash_autonomous import AutonomousFlashToolAgent\n"
    new_import = "from inference.agent.flash_join_compiled import JoinCompiledFlashToolAgent\n"
    if old_import not in text and new_import not in text:
        raise SystemExit("Autonomous Flash solver import anchor changed")
    text = text.replace(old_import, new_import, 1)

    old_ctor = "        return AutonomousFlashToolAgent(\n"
    new_ctor = "        return JoinCompiledFlashToolAgent(\n"
    if old_ctor not in text and new_ctor not in text:
        raise SystemExit("Autonomous Flash constructor anchor changed")
    text = text.replace(old_ctor, new_ctor, 1)
    solver.write_text(text, encoding="utf-8")

    compile(
        (agent_dir / "flash_join_compiled.py").read_text(),
        str(agent_dir / "flash_join_compiled.py"),
        "exec",
    )
    compile(solver.read_text(), str(solver), "exec")
    print("FLASH_JOIN_COMPILED_PATCH=PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    patch(args.root)


if __name__ == "__main__":
    main()

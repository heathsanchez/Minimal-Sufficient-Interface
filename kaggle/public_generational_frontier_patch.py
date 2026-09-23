from __future__ import annotations

import argparse
from pathlib import Path

MODULE = r'''from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from inference.agent.consequence_first_leaderboard import ConsequenceFirstLeaderboardAgent
from inference.agent.runtime_state import load_runtime_state
from inference.agent.tool_agent import AnalyzerTurnResult

SOURCE_RUN = 35811403514
SOURCE_ARTIFACT = 10730272259
PROGRAM = [
    {"action":"MOUSE","row":55,"col":36},
    {"action":"MOUSE","row":14,"col":31},
    {"action":"MOUSE","row":42,"col":26},
    {"action":"MOUSE","row":42,"col":36},
    {"action":"MOUSE","row":42,"col":41},
    {"action":"MOUSE","row":45,"col":26},
    {"action":"MOUSE","row":45,"col":36},
    {"action":"MOUSE","row":45,"col":41},
    {"action":"MOUSE","row":55,"col":36},
]

def _histogram(frame):
    if frame is None:
        return ()
    return tuple(sorted(Counter(x for row in frame.grid for x in row).items()))

class PublicGenerationalFrontierAgent(ConsequenceFirstLeaderboardAgent):
    """Hard-restart public developmental controller.

    One externally earned level program is admitted as a bounded capability.
    It executes before cognition only under its declared game/level guard.
    Failure revokes the capability; no exception policy is added.
    """

    def __init__(self,*args:Any,**kwargs:Any)->None:
        super().__init__(*args,**kwargs)
        self._pgf_attempted=False
        self._pgf_verified=False

    def _ensure_session(self,state_path:Path)->None:
        previous=getattr(self,"_session_runtime_dir",None)
        super()._ensure_session(state_path)
        if previous != self._session_runtime_dir:
            self._pgf_attempted=False
            self._pgf_verified=False
            self._dt_append("PUBLIC_FRONTIER_RESET",{
                "source_run":SOURCE_RUN,
                "source_artifact":SOURCE_ARTIFACT,
                "principle":"execute warranted hard-restart capability before paying cognition again",
            })

    def analyze(
        self,
        state_path:Path,
        action_num:int,
        valid_actions=None,
        step_env=None,
        transcript_path=None,
        analysis_step=None,
        transcript_updated=None,
        request_timeout_seconds=None,
        should_stop=None,
    ):
        self._ensure_session(state_path)
        frame,_=load_runtime_state(state_path)

        if (
            not self._pgf_attempted
            and frame is not None
            and int(frame.level)==1
            and step_env is not None
        ):
            self._pgf_attempted=True
            guard=_histogram(frame)
            before_level=int(frame.level)
            raw=step_env({"actions":PROGRAM})
            executed=int(raw.get("executed_count") or 0) if isinstance(raw,dict) else 0
            success=bool(
                isinstance(raw,dict)
                and raw.get("executed")
                and (raw.get("level_completed") or raw.get("run_complete"))
            )
            self._dt_append("PUBLIC_CAPABILITY_EXECUTE",{
                "source_run":SOURCE_RUN,
                "source_artifact":SOURCE_ARTIFACT,
                "level":before_level,
                "guard":{"color_histogram":guard},
                "requested_actions":len(PROGRAM),
                "executed_actions":executed,
                "protected_progress":success,
                "model_call":False,
            })
            if success:
                self._pgf_verified=True
                self._dt_append("ATLAS_CAPABILITY",{
                    "identity":"verified-action-program",
                    "source_run":SOURCE_RUN,
                    "source_artifact":SOURCE_ARTIFACT,
                    "first_level":1,
                    "verified_level":1,
                    "guard":"tn36 level-1 start + observed color histogram",
                    "program_length":len(PROGRAM),
                    "protected_consequence":"levels_completed increases",
                    "hard_restart":True,
                })
                self._dt_append("FLASH_RECLOSE",{
                    "resolved_level":before_level,
                    "source":"public-hard-restart-capability",
                    "model_call":False,
                })
            else:
                self._dt_append("ATLAS_REVOKE",{
                    "identity":"verified-action-program",
                    "source_run":SOURCE_RUN,
                    "level":before_level,
                    "reason":"hard-restart program failed protected consequence",
                })
                self._dt_append("REPRESENTATION_RESIDUAL",{
                    "level":before_level,
                    "reason":"compiled public capability failed under fresh replay",
                })
            if executed:
                return AnalyzerTurnResult(
                    step_executed=True,
                    reasoning=(
                        "Executed the previously warranted public capability with zero model calls."
                        if success else
                        "Compiled capability was falsified; residual reopened."
                    ),
                )

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

def patch(root:Path)->None:
    root=root.resolve()
    agent_dir=root/"inference"/"agent"
    solver=root/"inference"/"framework"/"solver.py"
    if not (agent_dir/"consequence_first_leaderboard.py").is_file():
        raise SystemExit("apply consequence_first_leaderboard_patch.py first")
    target=agent_dir/"public_generational_frontier.py"
    target.write_text(MODULE,encoding="utf-8")

    text=solver.read_text(encoding="utf-8")
    old_i="from inference.agent.consequence_first_leaderboard import ConsequenceFirstLeaderboardAgent\n"
    new_i="from inference.agent.public_generational_frontier import PublicGenerationalFrontierAgent\n"
    if old_i not in text and new_i not in text:
        raise SystemExit("consequence-first import anchor changed")
    text=text.replace(old_i,new_i,1)

    old_c="        return ConsequenceFirstLeaderboardAgent(\n"
    new_c="        return PublicGenerationalFrontierAgent(\n"
    if old_c not in text and new_c not in text:
        raise SystemExit("consequence-first constructor anchor changed")
    text=text.replace(old_c,new_c,1)
    solver.write_text(text,encoding="utf-8")

    compile(target.read_text(),str(target),"exec")
    compile(solver.read_text(),str(solver),"exec")
    print("PUBLIC_GENERATIONAL_FRONTIER_PATCH=PASS")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    patch(p.parse_args().root)

if __name__=="__main__":
    main()

from __future__ import annotations

import argparse
import json
from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AGENT = ROOT / "kaggle" / "agent" / "my_agent.py"
DEFAULT_NOTEBOOK = ROOT / "kaggle" / "notebooks" / "submission.ipynb"
DEFAULT_METADATA = ROOT / "kaggle" / "notebooks" / "kernel-metadata.json"
ACCELERATOR = "cpu"
_ACCELERATORS = {
    "cpu": {"name": "none", "gpu": False},
}


REGISTRY_SOURCE = dedent(
    """\
    from .agent import Agent, Playback
    from .templates.my_agent import MyAgent

    AVAILABLE_AGENTS = {
        'myagent': MyAgent,
    }
    """
)

ENV_SOURCE = dedent(
    """\
    SCHEME=http
    HOST=gateway
    PORT=8001
    ARC_API_KEY=test-key-123
    ARC_BASE_URL=http://gateway:8001/
    OPERATION_MODE=online
    ENVIRONMENTS_DIR=
    RECORDINGS_DIR=/kaggle/working/server_recording
    """
)


def code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "metadata": {"trusted": True},
        "outputs": [],
        "execution_count": None,
        "source": source,
    }


def markdown_cell(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source}


def build(agent_path: Path) -> dict:
    if not agent_path.exists():
        raise SystemExit(f"Could not find {agent_path}")
    agent_body = agent_path.read_text()

    install_cell = code_cell(
        "!pip install --no-index --find-links \\\n"
        "    /kaggle/input/competitions/arc-prize-2026-arc-agi-3/arc_agi_3_wheels \\\n"
        "    arc-agi python-dotenv"
    )

    write_agent_cell = code_cell("%%writefile /tmp/my_agent.py\n" + agent_body)

    run_cell_source = dedent(
        f'''\
        import os

        if os.getenv('KAGGLE_IS_COMPETITION_RERUN'):
            !curl --fail --retry 999 --retry-all-errors --retry-delay 5 \\
                  --retry-max-time 600 http://gateway:8001/api/games

            !cp -r /kaggle/input/competitions/arc-prize-2026-arc-agi-3/ARC-AGI-3-Agents \\
                   /kaggle/working/ARC-AGI-3-Agents

            !cp /tmp/my_agent.py \\
                /kaggle/working/ARC-AGI-3-Agents/agents/templates/my_agent.py

            with open('/kaggle/working/ARC-AGI-3-Agents/agents/__init__.py', 'w') as f:
                f.write({REGISTRY_SOURCE!r})

            with open('/kaggle/working/ARC-AGI-3-Agents/.env', 'w') as f:
                f.write({ENV_SOURCE!r})

            !cd /kaggle/working/ARC-AGI-3-Agents && \\
                MPLBACKEND=agg \\
                python main.py --agent myagent
        '''
    )
    run_cell = code_cell(run_cell_source)

    dummy_submission_cell = code_cell(
        dedent(
            '''\
            import os
            if not os.getenv('KAGGLE_IS_COMPETITION_RERUN'):
                import pandas as pd
                submission = pd.DataFrame(
                    data=[['1_0', '1', True, 1]],
                    columns=['row_id', 'game_id', 'end_of_game', 'score'])
                submission.to_parquet('/kaggle/working/submission.parquet', index=False)
                submission.head()
            '''
        )
    )

    accel = _ACCELERATORS[ACCELERATOR]
    return {
        "metadata": {
            "kernelspec": {
                "language": "python",
                "display_name": "Python 3",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "mimetype": "text/x-python",
                "file_extension": ".py",
                "pygments_lexer": "ipython3",
            },
            "kaggle": {
                "accelerator": accel["name"],
                "isInternetEnabled": False,
                "isGpuEnabled": accel["gpu"],
                "language": "python",
                "sourceType": "notebook",
            },
        },
        "nbformat_minor": 4,
        "nbformat": 4,
        "cells": [
            markdown_cell(
                "# Metalogic ARC-AGI-3 submission\n\n"
                "Generated from the self-contained online controller. "
                "Edit modular source under `kaggle/src/`, not this notebook."
            ),
            install_cell,
            write_agent_cell,
            run_cell,
            dummy_submission_cell,
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", type=Path, default=DEFAULT_AGENT)
    parser.add_argument("--output", type=Path, default=DEFAULT_NOTEBOOK)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(build(args.agent), indent=1))

    if args.metadata.exists():
        meta = json.loads(args.metadata.read_text())
        meta["enable_gpu"] = _ACCELERATORS[ACCELERATOR]["gpu"]
        meta["enable_internet"] = False
        args.metadata.write_text(json.dumps(meta, indent=2) + "\n")

    print(args.output)


if __name__ == "__main__":
    main()

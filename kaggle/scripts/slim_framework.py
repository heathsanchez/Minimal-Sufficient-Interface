"""Slim the vendored ARC-AGI-3 package to the base Agent API only.

The generated submission imports ``agents.agent.Agent`` directly. Importing a
Python submodule still executes ``agents/__init__.py`` first, so the upstream
registry must not eagerly pull optional LLM/swarm/template dependencies into
our model-free runtime.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INIT = ROOT / "vendor" / "ARC-AGI-3-Agents" / "agents" / "__init__.py"

SLIM = '''\
"""Minimal registry for Metalogic ARC3 symbolic execution."""
from .agent import Agent, Playback

AVAILABLE_AGENTS = {}
'''


def main() -> None:
    if not INIT.exists():
        raise SystemExit(f"Framework not found at {INIT}. Run `make setup` first.")
    INIT.write_text(SLIM)
    print(f"[slim_framework] Slimmed {INIT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

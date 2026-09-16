from __future__ import annotations

from typing import Any

from arcengine import FrameData, GameAction, GameState
from agents.agent import Agent

from .runtime import OnlineController


class MyAgent(Agent):
    """Thin ARC-AGI-3 framework adapter around the online MSI controller."""

    MAX_ACTIONS = 400

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        action_ids = tuple(
            int(action.value)
            for action in GameAction
            if action is not GameAction.RESET
        )
        self.controller = OnlineController(action_ids)

    @property
    def name(self) -> str:
        return f"{super().name}.metalogic-online-v1"

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        return latest_frame.state is GameState.WIN

    def choose_action(
        self, frames: list[FrameData], latest_frame: FrameData
    ) -> GameAction:
        if latest_frame.full_reset:
            self.controller.reset_episode()
            return GameAction.RESET

        if latest_frame.state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            self.controller.reset_episode()
            return GameAction.RESET

        token = self.controller.observe_and_choose(latest_frame)
        if token is None:
            return GameAction.RESET

        action = GameAction.from_id(token.action_id)
        if action.is_complex():
            if token.x is None or token.y is None:
                raise ValueError("complex action requires coordinates")
            action.set_data({"x": int(token.x), "y": int(token.y)})
            action.reasoning = {
                "agent": "metalogic-online-v1",
                "source": token.source,
                "x": int(token.x),
                "y": int(token.y),
            }
        else:
            action.reasoning = {
                "agent": "metalogic-online-v1",
                "source": token.source,
            }
        return action

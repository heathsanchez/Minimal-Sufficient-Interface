from __future__ import annotations

from typing import Any

from arcengine import FrameData, GameAction, GameState
from agents.agent import Agent

from .consequence_controller import ConsequenceController


class MyAgent(Agent):
    """Thin ARC-AGI-3 adapter around consequence acquisition and .mg memory."""

    MAX_ACTIONS = 400

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        action_ids = tuple(
            int(action.value)
            for action in GameAction
            if action is not GameAction.RESET
        )
        self.controller = ConsequenceController(action_ids)

    @property
    def name(self) -> str:
        return f"{super().name}.metalogic-affordance-v1"

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        if latest_frame.state is GameState.WIN:
            # The final winning consequence must be learned without buying
            # another action. observe_terminal consumes pending feedback once.
            self.controller.observe_terminal(latest_frame)
            return True
        return False

    def choose_action(
        self, frames: list[FrameData], latest_frame: FrameData
    ) -> GameAction:
        # The local/offline wrapper performs RESET during arc.make(). Its
        # full_reset observation is already playable: clear episode state but
        # do not send RESET again or fabricate a pre-reset/post-reset edge.
        if latest_frame.full_reset:
            self.controller.reset_episode()

        if latest_frame.state is GameState.GAME_OVER:
            # Commit both the visual consequence and exact failed prefix before
            # clearing trajectory state. Neither is a universal failure rule.
            self.controller.observe_terminal(latest_frame)
            self.controller.record_terminal_failure("GAME_OVER")
            self.controller.reset_episode()
            return GameAction.RESET

        if latest_frame.state is GameState.NOT_PLAYED:
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
                "agent": "metalogic-affordance-v1",
                "source": token.source,
                "x": int(token.x),
                "y": int(token.y),
            }
        else:
            action.reasoning = {
                "agent": "metalogic-affordance-v1",
                "source": token.source,
            }
        return action

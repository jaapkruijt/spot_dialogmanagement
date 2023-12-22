from enum import Enum
from typing import Optional


class ConvState(Enum):
    GAME_START = 1
    INTRO = 2
    ROUND_START = 3
    DISAMBIGUATION = 4
    REPAIR = 5
    ACKNOWLEDGE = 6
    QUERY_NEXT = 7
    ROUND_FINISH = 8
    GAME_FINISH = 9

    def transitions(self):
        return self._allowed()[self]

    def _allowed(self):
        return {
            ConvState.GAME_START: [ConvState.INTRO],
            ConvState.INTRO: [ConvState.ROUND_START],
            ConvState.ROUND_START: [ConvState.QUERY_NEXT],
            ConvState.QUERY_NEXT: [ConvState.DISAMBIGUATION],
            ConvState.DISAMBIGUATION: [ConvState.REPAIR, ConvState.ACKNOWLEDGE],
            ConvState.REPAIR: [ConvState.DISAMBIGUATION],
            ConvState.ACKNOWLEDGE: [ConvState.QUERY_NEXT, ConvState.ROUND_FINISH],
            ConvState.ROUND_FINISH: [ConvState.ROUND_START, ConvState.GAME_FINISH]
        }


class State:
    conv_state: Optional[ConvState]

    def transition(self, conv_state: ConvState, **kwargs):
        if conv_state not in self.conv_state.transitions():
            raise ValueError(f"Cannot change state from {self.conv_state} to {conv_state}")

        return self._transition(conv_state, **kwargs)

    def stay(self, **kwargs):
        return self._transition(self.conv_state, **kwargs)

    def _transition(self, conv_state: ConvState, **kwargs):
        new_state = vars(State(None)) if conv_state == ConvState.GAME_START else vars(self)
        new_state.update(**kwargs)
        new_state["conv_state"] = conv_state

        return State(**new_state)


class DialogManager:
    def __init__(self, interaction, max_rounds):
        self._state = State(ConvState.GAME_START)
        self._round = 0
        self._interaction = interaction
        self._max_rounds = max_rounds
    






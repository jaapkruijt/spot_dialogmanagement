import dataclasses
import logging
from enum import Enum, auto
from typing import Optional, Any

from spot.dialog.intro import IntroStep, GameStartStep

logger = logging.getLogger(__name__)


# from spot.pragmatic_model.model_ambiguity import Disambiguator, DisambiguatorStatus
class DisambiguatorStatus(Enum):
    AWAIT_NEXT = 1
    SUCCESS = 2
    NO_MATCH = 3
    MATCH_MULTIPLE = 4
    MATCH_PREVIOUS = 5


class ConvState(Enum):
    GAME_START = auto()
    # Training round
    INTRO = auto()
    ROUND_START = auto()
    QUERY_NEXT = auto()
    DISAMBIGUATION = auto()
    REPAIR = auto()
    ACKNOWLEDGE = auto()
    ROUND_FINISH = auto()
    GAME_FINISH = auto()

    def transitions(self):
        return self._allowed()[self]

    def _allowed(self):
        return {
            ConvState.GAME_START: [ConvState.GAME_START, ConvState.INTRO],
            ConvState.INTRO: [ConvState.INTRO, ConvState.ROUND_START],
            ConvState.ROUND_START: [ConvState.QUERY_NEXT],
            ConvState.QUERY_NEXT: [ConvState.QUERY_NEXT, ConvState.DISAMBIGUATION],
            ConvState.DISAMBIGUATION: [ConvState.DISAMBIGUATION, ConvState.REPAIR, ConvState.ACKNOWLEDGE],
            ConvState.REPAIR: [ConvState.REPAIR, ConvState.DISAMBIGUATION],
            ConvState.ACKNOWLEDGE: [ConvState.QUERY_NEXT, ConvState.ROUND_FINISH],
            ConvState.ROUND_FINISH: [ConvState.ROUND_START, ConvState.GAME_FINISH],
            ConvState.GAME_FINISH: [ConvState.GAME_FINISH, ConvState.GAME_START]
        }


class ConfirmationState(Enum):
    CONFIRM = auto()
    REQUESTED = auto()
    ACCEPTED = auto()


@dataclasses.dataclass()
class State:
    conv_state: Optional[ConvState] = None
    game_start: Optional[GameStartStep] = None
    intro: Optional[IntroStep] = None
    round: int = 0
    position: int = 0
    utterance: Optional[str] = None
    mention: Optional[str] = None
    disambiguation_result: Optional[Any] = None
    confirmation: Optional[ConfirmationState] = None

    def transition(self, conv_state: ConvState, **kwargs):
        if conv_state not in self.conv_state.transitions():
            raise ValueError(f"Cannot change state from {self.conv_state} to {conv_state}")

        return self._transition(conv_state, False, **kwargs)

    def transition_and_clear(self, conv_state: ConvState, **kwargs):
        if conv_state not in self.conv_state.transitions():
            raise ValueError(f"Cannot change state from {self.conv_state} to {conv_state}")

        return self._transition(conv_state, True, **kwargs)

    def _transition(self, conv_state: ConvState, clear, **kwargs):
        new_state = vars(State()) if clear else vars(self).copy()
        new_state.update(**kwargs)
        new_state["conv_state"] = conv_state

        return State(**new_state)


@dataclasses.dataclass
class Action:
    reply: Optional[str] = None
    await_input: Optional[bool] = None


class DialogManager:
    def __init__(self, disambiguator, max_position=5, acceptance_threshold=0.6, success_threshold=0.3):
        self._disambiguator = disambiguator
        self._success_threshold = success_threshold
        self._acceptance_threshold = acceptance_threshold
        self._positions = max_position

        self._state = State(ConvState.GAME_START)
        self._round = 0
        self._replier = None

    def set_replier(self, replier):
        self._replier = replier

    def game_event(self, event):
        logger.debug("Input (Game): %s", event)
        self.run(None, event)

    def utterance(self, utterance: str):
        logger.debug("Input: (Text) %s", utterance)
        self.run(utterance, None)

    def run(self, utterance, game_transition):
        action = Action()
        while not action.await_input:
            action, next_state = self.act(utterance, game_transition, self._state)
            if action.reply:
                self._replier(action.reply)
            logger.debug("Transition from %s to %s",self._format_state(self._state), self._format_state(next_state))
            self._state = next_state

        # TODO Clear utterance and mention and anything else
        self._state = next_state.transition(self._state.conv_state, utterance=None, mention=None)

    def act(self, utterance, game_transition, state):
        if ConvState.GAME_START == state.conv_state:
            action, next_state = self.act_game_start(game_transition, state)
        elif ConvState.INTRO == state.conv_state:
            action, next_state = self._act_intro(game_transition, state)
        elif ConvState.ROUND_START == state.conv_state:
            action, next_state = self._act_round_start(state)
        elif ConvState.QUERY_NEXT == state.conv_state:
            action, next_state = self._act_query_next(state)
        elif ConvState.DISAMBIGUATION == state.conv_state:
            action, next_state = self._act_disambiguation(state, utterance)
        elif ConvState.ACKNOWLEDGE == state.conv_state:
            action, next_state = self._act_acknowledge(utterance, state)
        elif ConvState.REPAIR == state.conv_state:
            action, next_state = self._act_repair(state)
        elif ConvState.ROUND_FINISH == state.conv_state:
            action, next_state = self._act_round_finished(state)
        elif ConvState.GAME_FINISH == state.conv_state:
            action, next_state = self._act_game_finished(state)
        else:
            raise ValueError("Invalid conversational state " + str(state.conv_state))


        # Put selected, certainty, disambiguator status into EMISSOR: mention is whole utterance, annotation a custom value with those data values
        return action, next_state

    def act_game_start(self, game_transition, state):
        if state.game_start is None:
            action = Action()
            next_state = state.transition(ConvState.GAME_START, game_start=GameStartStep())
        elif not state.game_start.final:
            step = state.game_start.next()
            next_state = state.transition(ConvState.GAME_START, game_start=step)
            action = Action(step.statement, True)
        elif game_transition:
            action = Action()
            next_state = state.transition(ConvState.INTRO, game_start=None)
        else:
            action = Action(None, True)
            next_state = state
        return action, next_state

    def _act_intro(self, game_transition, state):
        if state.intro is None:
            action = Action()
            next_state = state.transition(ConvState.INTRO, intro=IntroStep())
        elif not state.intro.final:
            step = state.intro.next()
            next_state = state.transition(ConvState.INTRO, intro=step)
            action = Action(step.statement, True)
        elif game_transition:
            action = Action()
            next_state = state.transition(ConvState.ROUND_START, intro=None, round=0)
        else:
            action = Action(None, True)
            next_state = state

        return action, next_state

    def _act_round_start(self, state):
        game_round = state.round + 1
        self._disambiguator.advance_round(start=(game_round == 1))

        action = Action("Let's start!")
        next_state = state.transition(ConvState.QUERY_NEXT, round=game_round, position=1, utterance=None,
                                      mention=None, disambiguation_result=None, confirmation=None)

        return action, next_state

    def _act_query_next(self, state):
        # Eventually check the disambiguator state if there is already information available
        action = Action("What about position " + str(state.position) + " Who is there?", True)
        next_state = state.transition(ConvState.DISAMBIGUATION)

        return action, next_state

    def _act_disambiguation(self, state, utterance):
        if state.utterance is None and utterance:
            action = Action()
            next_state = state.transition(ConvState.DISAMBIGUATION, utterance=utterance)
        elif state.mention is None and state.utterance:
            mention = self.get_mention(state.utterance)
            action = Action()
            # TODO if no mention, go to repair (No match) or clear utterance and wait for the next one (to be decided)
            next_state = state.transition(ConvState.DISAMBIGUATION if mention else state.conv_state, mention=mention)
        elif state.mention:
            disambiguation_result = self._disambiguator.disambiguate(state.mention)
            selected, certainty, position, difference = disambiguation_result
            success = self._disambiguator.status() == DisambiguatorStatus.SUCCESS
            if success and certainty > self._success_threshold:
                action = Action()
                confirmation = ConfirmationState.ACCEPTED if certainty > self._acceptance_threshold else ConfirmationState.CONFIRM
                next_state = state.transition(ConvState.ACKNOWLEDGE, disambiguation_result=disambiguation_result, confirmation=confirmation)
            else:
                action = Action()
                next_state = state.transition(ConvState.REPAIR, disambiguation_result=disambiguation_result)
        else:
            action = Action(None, True)
            next_state = state

        return action, next_state

    def _act_acknowledge(self, utterance, state):
        if ConfirmationState.ACCEPTED == state.confirmation:
            reply = self._acknowledge(state, confirm=False)
            action = Action(reply)

            position = state.position + 1
            self._disambiguator.advance_position()

            next_state = state.transition(
                ConvState.QUERY_NEXT if position <= self._positions else ConvState.ROUND_FINISH,
                position=position, utterance=None, mention=None, disambiguation_result=None, confirmation=None)
        elif ConfirmationState.CONFIRM == state.confirmation:
            reply = self._acknowledge(state, confirm=True)
            action = Action(reply, True)
            next_state = state.transition(state.conv_state, confirmation=ConfirmationState.REQUESTED)
        elif ConfirmationState.REQUESTED == state.confirmation:
            if "yes" in utterance.lower():
                action = Action()
                next_state = state.transition(state.conv_state, confirmation=ConfirmationState.ACCEPTED)
            elif "no" in utterance.lower():
                action = Action("OK, let's try again..")
                # Restart, but stay in the same position
                next_state = state.transition(ConvState.QUERY_NEXT, utterance=None, mention=None, disambiguation_result=None, confirmation=None)
            else:
                action = Action("I didn't get it.. Yes or no?", True)
                next_state = state
        else:
            raise ValueError("Invalid confirmation status " + str(state.confirmation))

        return action, next_state

    def _act_repair(self, state):
        if DisambiguatorStatus.NO_MATCH == self._disambiguator.status():
            action = Action("Aha, not sure who you are referring to.. Can you be more clear?", True)
        elif DisambiguatorStatus.MATCH_PREVIOUS == self._disambiguator.status():
            action = Action(f"We already decided about him.", True)
        elif DisambiguatorStatus.MATCH_MULTIPLE == self._disambiguator.status():
            action = Action(f"Did you mean the one with the {' and '.join(state.disambiguation_result[3])}.", True)
        else:
            raise ValueError(f"Illegal state for disambiguator status: {self._disambiguator.status()}")

        next_state = state.transition(ConvState.DISAMBIGUATION, utterance=None, mention=None, disambiguation_result=None)

        return action, next_state

    def _act_round_finished(self, state):
        action = Action("Let's see how you performed..")
        next_state = state.transition(ConvState.ROUND_START if self.has_next_round(state) else ConvState.GAME_FINISH,
                                      round=state.round + 1)

        return action, next_state

    def _act_game_finished(self, state):
        next_state = state.transition(ConvState.GAME_FINISH)
        action = Action("Goodbye!", True)

        return action, next_state

    def get_mention(self, utterance):
        # Eventually add mention detection
        return utterance

    def _acknowledge(self, state, confirm):
        selected, certainty, position, difference = state.disambiguation_result
        # TODO Find the mention the human used for the character (see mention detection ;)
        # or unique attributes of the character
        # ref_string = f"{selected} in position {position}"
        ref_string = f"that one in position {position}"
        if confirm:
            return f"So {ref_string}, correct?"
        else:
            return f"I have {ref_string}."

    def has_next_round(self, state):
        return state.round < 3

    def _format_state(self, value):
        if isinstance(value, dict):
            return {k: self._format_state(v) for k, v in value.items() if v}
        elif isinstance(value, (bool, str, int, float, type(None))):
            return value
        elif dataclasses.is_dataclass(value):
            result = {k: self._format_state(v) for k, v in dataclasses.asdict(value).items() if v}
            if 'conv_state' in result:
                result['conv_state'] = result['conv_state'].name
            return result
        else:
            return value


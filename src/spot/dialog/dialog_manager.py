import dataclasses
import enum
import json
import logging
import os
import random
from enum import Enum, auto
from pathlib import Path
from typing import Optional, Any

from spot.pragmatic_model.model_ambiguity import DisambiguatorStatus

from spot.dialog.conversations import IntroStep, GameStartStep, OutroStep

logger = logging.getLogger(__name__)

# TODO is it possible to add string formatting to some phrases and not others?
NO_MATCH_PHRASES = ['Ik begrijp niet zo goed wie je bedoelt. Kan je het nog een keer omschrijven?',
                    'Ik snap niet zo goed wat je zei. Kan je het iets anders formuleren?']
# ACKNOWLEDGE_PHRASES = ['Oh, die staat bij mij op plek %s']
QUESTIONAIRE_PHRASES=["We hebben ze allemaal gehad. Druk maar op de knop Ga Door. Op het scherm zie je nu onze score voor deze ronde. Voordat we doorgaan naar de volgende ronde, wil ik je eerst vragen de vragenlijst in te vullen. Druk maar op de link op het scherm om naar de vragen te gaan. Ik ben stil terwijl jij de vragen invult. Daarna gaan we weer verder."]
ROUND_FINISH_PHRASES = [
'We hebben ze allemaal gehad. Druk maar op de knop Ga Door. Op het scherm zie je nu onze score voor deze ronde. We kunnen nu door naar de volgende ronde. Druk maar weer op de knop Ga Door.',
    'Dit was het voor deze ronde. Druk maar op de knop Ga Door. Op het scherm zie je nu onze score voor deze ronde. Laten we naar de volgende ronde gaan. Druk maar weer op de knop Ga Door.',
    'Oke. Druk maar op de knop Ga Door. Onze score voor deze ronde verschijnt nu in beeld. We gaan door naar de volgende ronde. Druk maar weer op de knop Ga Door.',
    'Oke, we hebben ze allemaal gehad. Druk maar op de knop Ga Door. Dit is onze score. Laten we doorgaan naar de volgende ronde. Druk maar weer op de knop Ga Door.',
    'Deze ronde is klaar. Druk maar op de knop Ga Door. Onze score komt nu in beeld. Druk op de knop Ga Door om naar de volgende ronde te gaan.'
]
QUERY_NEXT_PHRASES = ['En de volgende?', 'Oke, we gaan door met de volgende.', 'Oke, en de volgende?',
                      'En de figuur die daarnaast staat?', 'En die daarnaast staat?', 'Oké, en die daarnaast staat?']
ACKNOWLEDGE_SAME_POSITION_PHRASES = ['Oh ja, %s staat bij mij ook op plek {position}', '%s staat bij mij ook op die plek.',
                                     'He, %s staat bij mij ook op die plek.', 'Ja, %s staat bij mij op dezelfde plek.',
                                     'Oh ja, %s staat bij mij op dezelfde plek.']
ACKNOWLEDGE_DIFFERENT_POSITION_PHRASES = ['Bij mij staat %s op plek {position}.',
                                          '%s staat bij mij ergens anders, namelijk op plek {position}.',
                                          'Oh, %s staat bij mij op plek {position}.',
                                          'Even kijken, nee, bij mij staat %s op plek {position}.']
MATCH_PREVIOUS_PHRASES = ['Wacht even, volgens mij hebben we deze al gehad. Wil je het nog een keer omschrijven?',
                          'Even kijken hoor, ik dacht dat we deze al hadden gehad. Laten we even een stap terug.  Kan je iets noemen wat specifiek is voor die figuur?'
                          ]


class ConvState(Enum):
    GAME_INIT = auto()
    GAME_START = auto()
    # Training round
    INTRO = auto()
    ROUND_START = auto()
    QUERY_NEXT = auto()
    DISAMBIGUATION = auto()
    REPAIR = auto()
    ACKNOWLEDGE = auto()
    ROUND_FINISH = auto()
    OUTRO = auto()
    GAME_FINISH = auto()

    def transitions(self):
        return self._allowed()[self]

    def _allowed(self):
        return {
            ConvState.GAME_INIT: [ConvState.GAME_INIT, ConvState.GAME_START],
            ConvState.GAME_START: [ConvState.GAME_START, ConvState.INTRO],
            ConvState.INTRO: [ConvState.INTRO, ConvState.ROUND_START],
            ConvState.ROUND_START: [ConvState.QUERY_NEXT],
            ConvState.QUERY_NEXT: [ConvState.QUERY_NEXT, ConvState.DISAMBIGUATION],
            ConvState.DISAMBIGUATION: [ConvState.DISAMBIGUATION, ConvState.REPAIR, ConvState.ACKNOWLEDGE],
            ConvState.REPAIR: [ConvState.REPAIR, ConvState.DISAMBIGUATION],
            ConvState.ACKNOWLEDGE: [ConvState.ACKNOWLEDGE, ConvState.QUERY_NEXT, ConvState.ROUND_FINISH],
            ConvState.ROUND_FINISH: [ConvState.ROUND_START, ConvState.ROUND_FINISH, ConvState.OUTRO],
            ConvState.OUTRO: [ConvState.OUTRO, ConvState.GAME_FINISH],
            ConvState.GAME_FINISH: [ConvState.GAME_FINISH, ConvState.GAME_INIT]
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
    outro: Optional[OutroStep] = None
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
class Input(enum.Enum):
    GAME = auto()
    REPLY = auto()


@dataclasses.dataclass
class Action:
    reply: Optional[str] = None
    await_input: Optional[Input] = None


class DialogManager:
    def __init__(self, disambiguator, storage_path: str, rounds=6, max_position=5, questionnaires=[1, 6], success_threshold=0.3, high_engagement=True):
        self._disambiguator = disambiguator
        self._storage_path = storage_path
        self._success_threshold = success_threshold
        self._positions = max_position
        self._rounds = rounds
        self._questionaire_rounds = questionnaires
        self.high_engagement = high_engagement

        self._participant_id = None

        self._state = State(ConvState.GAME_INIT)
        self._round = 0

    @property
    def participant_id(self):
        return self._participant_id

    def game_event(self, event):
        logger.debug("Input (Game): %s", event)
        return self.run(None, event)

    def utterance(self, utterance: str):
        logger.debug("Input: (Text) %s", utterance)
        return self.run(utterance, None)

    def run(self, utterance, game_transition):
        action = Action()
        reply = ""
        while not action.await_input:
            action, next_state = self.act(utterance, game_transition, self._state)
            if action.reply:
                if reply:
                    reply += " \\pau=1000\\" + action.reply
                else:
                    reply = action.reply
            logger.debug("Transition from %s to %s", self._format_state(self._state), self._format_state(next_state))
            self._state = next_state

        # TODO Clear utterance and mention and anything else
        self._state = next_state.transition(self._state.conv_state, utterance=None, mention=None)

        return reply, self._state, action.await_input

    def act(self, utterance, game_transition, state):
        if ConvState.GAME_INIT == state.conv_state:
            action, next_state = self.act_game_init(game_transition, state)
        elif ConvState.GAME_START == state.conv_state:
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
            action, next_state = self._act_round_finished(game_transition, state)
        elif ConvState.OUTRO == state.conv_state:
            action, next_state = self._act_outro(utterance, state)
        elif ConvState.GAME_FINISH == state.conv_state:
            action, next_state = self._act_game_finished(state)
        else:
            raise ValueError("Invalid conversational state " + str(state.conv_state))

        # Put selected, certainty, disambiguator status into EMISSOR: mention is whole utterance, annotation a custom value with those data values
        return action, next_state

    def act_game_init(self, game_transition, state):
        if game_transition:
            self._participant_id = game_transition.participant_id
            logger.info("Start game for %s", self._participant_id)
            action = Action()
            next_state = state.transition(ConvState.GAME_START)
        else:
            action = Action(await_input=Input.GAME)
            next_state = state.transition(ConvState.GAME_INIT)

        return action, next_state

    def act_game_start(self, game_transition, state):
        if state.game_start is None:
            action = Action()
            next_state = state.transition(ConvState.GAME_START, game_start=GameStartStep())
        elif not state.game_start.final:
            step = state.game_start.next()
            next_state = state.transition(ConvState.GAME_START, game_start=step)
            action = Action(step.statement, await_input=Input.REPLY if not next_state.game_start.final else Input.GAME)
        elif game_transition:
            action = Action()
            next_state = state.transition(ConvState.INTRO, game_start=None)
        else:
            action = Action(await_input=Input.REPLY)
            next_state = state
        return action, next_state

    def _act_intro(self, game_transition, state):
        if state.intro is None:
            action = Action()
            next_state = state.transition(ConvState.INTRO, intro=IntroStep())
        elif not state.intro.final:
            step = state.intro.next()
            next_state = state.transition(ConvState.INTRO, intro=step)
            action = Action(step.statement, await_input=Input.REPLY if not next_state.intro.final else Input.GAME)
        elif game_transition:
            action = Action()
            next_state = state.transition(ConvState.ROUND_START, intro=None, round=0)
        else:
            action = Action(await_input=Input.REPLY)
            next_state = state

        return action, next_state

    def _act_round_start(self, state):
        game_round = state.round + 1
        self._disambiguator.advance_round(start=(game_round == 1))

        action = Action("Laten we beginnen!")
        next_state = state.transition(ConvState.QUERY_NEXT, round=game_round, position=1, utterance=None,
                                      mention=None, disambiguation_result=None, confirmation=None)

        return action, next_state

    def _act_query_next(self, state):
        # Eventually check the disambiguator state if there is already information available
        # if asking for next position
        if DisambiguatorStatus.AWAIT_NEXT.name == self._disambiguator.status():
            if 1 == state.position:
                action = Action("Wie staat er bij jou op plek 1?", await_input=Input.REPLY)
            else:
                action = Action(random.choice(QUERY_NEXT_PHRASES), Input.REPLY)
        # if coming from repair
        else:
            action = Action("Wie staat er bij jou op plek " + str(state.position) + "?", Input.REPLY)
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
            if DisambiguatorStatus.SUCCESS_HIGH.name == self._disambiguator.status():
                action = Action()
                next_state = state.transition(ConvState.ACKNOWLEDGE, disambiguation_result=disambiguation_result, confirmation=ConfirmationState.ACCEPTED)
            elif DisambiguatorStatus.SUCCESS_LOW.name == self._disambiguator.status():
                action = Action()
                next_state = state.transition(ConvState.ACKNOWLEDGE,  disambiguation_result=disambiguation_result, confirmation=ConfirmationState.CONFIRM)
            else:
                action = Action()
                next_state = state.transition(ConvState.REPAIR, disambiguation_result=disambiguation_result)
        else:
            action = Action(await_input=Input.REPLY)
            next_state = state

        return action, next_state

    def _act_acknowledge(self, utterance, state):
        if ConfirmationState.ACCEPTED == state.confirmation:
            reply = self._acknowledge(state, confirm=False)
            action = Action(reply)

            # selected, certainty, position, difference = state.disambiguation_result
            # self._disambiguator.confirm_character_position(selected, state.mention)
            # logging.debug("State mention: %s", state.mention)
            position = state.position + 1
            if position < 6:
                self._disambiguator.advance_position()

            next_state = state.transition(
                ConvState.QUERY_NEXT if position <= self._positions else ConvState.ROUND_FINISH,
                position=position, utterance=None, mention=None, disambiguation_result=None, confirmation=None)
        elif ConfirmationState.CONFIRM == state.confirmation:
            reply = self._acknowledge(state, confirm=True)
            action = Action(reply, await_input=Input.REPLY)
            next_state = state.transition(state.conv_state, confirmation=ConfirmationState.REQUESTED)
        elif ConfirmationState.REQUESTED == state.confirmation:
            if "ja" in utterance.lower():
                action = Action()
                next_state = state.transition(state.conv_state, confirmation=ConfirmationState.ACCEPTED)
            elif "nee" in utterance.lower():
                action = Action("Oke, we proberen het opnieuw")
                # Restart, but stay in the same position
                next_state = state.transition(ConvState.QUERY_NEXT, utterance=None, mention=None, disambiguation_result=None, confirmation=None)
            else:
                action = Action("Ik snap het niet, ja of nee?", await_input=Input.REPLY)
                next_state = state
        else:
            raise ValueError("Invalid confirmation status " + str(state.confirmation))

        return action, next_state

    def _act_repair(self, state):
        if DisambiguatorStatus.NO_MATCH.name == self._disambiguator.status():
            action = Action(random.choice(NO_MATCH_PHRASES), await_input=Input.REPLY)
        elif DisambiguatorStatus.NEG_RESPONSE.name == self._disambiguator.status():
            # TODO not sure if this is way to go
            action = Action("Oke, kun je het op een andere manier omschrijven?", await_input=Input.REPLY)
        elif DisambiguatorStatus.MATCH_PREVIOUS.name == self._disambiguator.status():
            action = Action(random.choice(MATCH_PREVIOUS_PHRASES), await_input=Input.REPLY)
        elif DisambiguatorStatus.MATCH_MULTIPLE.name == self._disambiguator.status():
            description = state.disambiguation_result[3]
            action = Action(f"{description}?", await_input=Input.REPLY)
        else:
            raise ValueError(f"Illegal state for disambiguator status: {self._disambiguator.status()}")

        next_state = state.transition(ConvState.DISAMBIGUATION, utterance=None, mention=None, disambiguation_result=None)

        return action, next_state

    def _act_round_finished(self, game_transition, state):
        if game_transition:
            action = Action()
            next_state = state.transition(ConvState.ROUND_START if self.has_next_round(state) else ConvState.OUTRO)
        elif state.round not in self._questionaire_rounds:
            reply = random.choice(ROUND_FINISH_PHRASES)
            action = Action(reply, await_input=Input.GAME if self.has_next_round(state) else None)
            next_state = state.transition(state.conv_state if self.has_next_round(state) else ConvState.OUTRO)
        else:
            reply = random.choice(QUESTIONAIRE_PHRASES)
            action = Action(reply, await_input=Input.GAME)
            next_state = state

        return action, next_state

    def _act_outro(self, utterance, state):
        if state.outro is None:
            action = Action()
            next_state = state.transition(ConvState.OUTRO, outro=OutroStep())
        elif state.outro.store_input and not state.utterance:
            if utterance:
                self.save_preferences(utterance)
                return Action(), state.transition(ConvState.OUTRO, utterance=utterance)
            else:
                # No response, wait..
                return Action(await_input=Input.REPLY), state
        elif state.outro.final:
            action = Action()
            next_state = state.transition(ConvState.GAME_FINISH, outro=None, utterance=None)
        else:
            step = state.outro.next()
            next_state = state.transition(ConvState.OUTRO, outro=step, utterance=None)
            action = Action(step.statement, await_input=Input.REPLY if not state.outro.final else None)

        return action, next_state

    def _act_game_finished(self, state):
        action = Action("Goodbye!", await_input=Input.GAME)

        self.save_interaction()

        return action, state

    def save_preferences(self, utterance):
        if not self._storage_path:
            return

        storage_dir = os.path.join(self._storage_path, "dialog")
        Path(storage_dir).mkdir(parents=True, exist_ok=True)
        data_path = os.path.join(storage_dir, f"pp_{self._participant_id}_int{1}_preferences.json")

        try:
            with open(data_path, 'r') as data_file:
                data = json.load(data_file)
        except:
            data = {}

        data["answer"] = utterance

        with open(data_path, 'w') as data_file:
            json.dump(data, data_file)

    def save_interaction(self):
        self._disambiguator.save_interaction(self._storage_path, self._participant_id, 1)

    def get_mention(self, utterance):
        # Eventually add mention detection
        return utterance

    def _acknowledge(self, state, confirm):
        selected, certainty, position, description = state.disambiguation_result
        # TODO Find the mention the human used for the character (see mention detection ;)
        # or unique attributes of the character
        # ref_string = f"{selected} in position {position}"
        # ref_string = f"that one in position {position}"
        if confirm:
            return f"{description}?"
        else:
            if self.high_engagement:
                if position == state.position:
                    # TODO is state.position already None here?
                    response = random.choice(ACKNOWLEDGE_SAME_POSITION_PHRASES).format_map({"position": position}) % description
                else:
                    response = random.choice(ACKNOWLEDGE_DIFFERENT_POSITION_PHRASES).format_map({"position": position}) % description
            else:
                if position == state.position:
                    response = random.choice(ACKNOWLEDGE_SAME_POSITION_PHRASES).format_map({"position": position}) % "die"
                else:
                    response = random.choice(ACKNOWLEDGE_DIFFERENT_POSITION_PHRASES).format_map({"position": position}) % "die"
            response = response + " Vul dat maar in op de thablet."
            return response

    def has_next_round(self, state):
        return state.round < self._rounds

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


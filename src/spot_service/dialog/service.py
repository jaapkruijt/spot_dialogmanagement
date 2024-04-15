import logging
from typing import List, Union

from cltl.combot.event.emissor import TextSignalEvent, AudioSignalStarted, SignalEvent
from cltl.combot.event.bdi import DesireEvent
from cltl.combot.infra.config import ConfigurationManager
from cltl.combot.infra.event import Event, EventBus
from cltl.combot.infra.resource import ResourceManager
from cltl.combot.infra.time_util import timestamp_now
from cltl.combot.infra.topic_worker import TopicWorker
from cltl_service.emissordata.client import EmissorDataClient
from emissor.representation.scenario import TextSignal, Modality, class_type

from spot.dialog.dialog_manager import DialogManager, State, ConvState, Input
from spot_service.dialog.api import GameSignal, GameEvent

logger = logging.getLogger(__name__)


CONTENT_TYPE_SEPARATOR = ';'


class SpotDialogService:
    @classmethod
    def from_config(cls, manager: DialogManager, emissor_client: EmissorDataClient,
                    event_bus: EventBus, resource_manager: ResourceManager,
                    config_manager: ConfigurationManager):
        config = config_manager.get_config("spot.dialog")

        mic_topic = config.get("topic_mic") if "topic_mic" in config else None
        text_input_topic = config.get("topic_text_input")
        game_input_topic = config.get("topic_game_input")
        game_state_topic = config.get("topic_game_state")
        output_topic = config.get("topic_text_output")

        intention_topic = config.get("topic_intention") if "topic_intention" in config else None
        desire_topic = config.get("topic_desire") if "topic_desire" in config else None
        intentions = config.get("intentions", multi=True) if "intentions" in config else []

        return cls(mic_topic, text_input_topic, game_input_topic, game_state_topic, output_topic,
                   intention_topic, desire_topic, intentions,
                   manager, emissor_client, event_bus, resource_manager)

    def __init__(self, mic_topic: str, text_input_topic: str, game_input_topic: str, game_state_topic: str,
                 output_topic: str, intention_topic: str, desire_topic: str, intentions: List[str],
                 manager: DialogManager, emissor_client: EmissorDataClient,
                 event_bus: EventBus, resource_manager: ResourceManager):
        self._manager = manager

        self._event_bus = event_bus
        self._resource_manager = resource_manager
        self._emissor_client = emissor_client

        self._mic_topic = mic_topic
        self._text_input_topic = text_input_topic
        self._game_input_topic = game_input_topic
        self._game_state_topic = game_state_topic
        self._output_topic = output_topic

        self._intention_topic = intention_topic
        self._desire_topic = desire_topic
        self._intentions = intentions

        self._topic_worker = None

        self._ignore_utterances = False if mic_topic else None

    @property
    def app(self):
        return None

    def start(self, timeout=30):
        input_topics = [self._text_input_topic, self._game_input_topic]
        if self._mic_topic:
            input_topics += [self._mic_topic]

        self._topic_worker = TopicWorker(input_topics, self._event_bus,
                                         provides=[self._output_topic, self._game_state_topic],
                                         intention_topic=self._intention_topic, intentions=self._intentions,
                                         resource_manager=self._resource_manager, processor=self._process,
                                         buffer_size=16, name=self.__class__.__name__)
        self._topic_worker.start().wait()

    def stop(self):
        if not self._topic_worker:
            pass

        self._topic_worker.stop()
        self._topic_worker.await_stop()
        self._topic_worker = None

    def _process(self, event: Event[Union[TextSignalEvent, AudioSignalStarted, SignalEvent[GameEvent]]]):
        if event.metadata.topic == self._game_input_topic:
            response, state, input = self._manager.game_event(event.payload.signal.value)
            self._send_reply(response, state, input)
            logger.info("Handled game event %s", event.payload.signal.value)
        elif event.metadata.topic == self._mic_topic:
            if event.payload.type == AudioSignalStarted.__name__:
                self._set_ignore_utterances(False)
        elif event.metadata.topic == self._text_input_topic and not event.payload.signal.text:
            # Ignore empty inputs
            pass
        elif event.metadata.topic == self._text_input_topic and not self._ignore_utterances:
            # Ignore events until utterance is handled
            self._set_ignore_utterances()
            response, state, input = self._manager.utterance(event.payload.signal.text)
            self._send_reply(response, state, input)
        else:
            logger.info("Ignored event %s (ignore utterances: %s)", event, self._ignore_utterances)

    def _send_reply(self, response: str, state: State, input: Input):
        if not response:
            return

        scenario_id = self._emissor_client.get_current_scenario_id()
        signal = TextSignal.for_scenario(scenario_id, timestamp_now(), timestamp_now(), None, response)
        signal_event = TextSignalEvent.for_agent(signal)
        self._event_bus.publish(self._output_topic, Event.for_payload(signal_event))

        event = GameEvent(participant_id=self._manager._participant_id, round=str(state.round),
                          state=state.conv_state.name, input=input.name)
        game_signal = GameSignal.for_scenario(scenario_id, timestamp_now(), event)
        game_signal_event = SignalEvent(class_type(GameSignal), Modality.VIDEO, game_signal)
        self._event_bus.publish(self._game_state_topic, Event.for_payload(game_signal_event))

        if ConvState.GAME_FINISH == state.conv_state:
            self._event_bus.publish(self._desire_topic, Event.for_payload(DesireEvent(['quit'])))

    def _set_ignore_utterances(self, ignore=True):
        if self._ignore_utterances is None:
            return

        self._ignore_utterances = ignore
        logger.debug("Set ignore utterances to %s", ignore)

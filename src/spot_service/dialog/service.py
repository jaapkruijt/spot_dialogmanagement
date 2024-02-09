import logging
from typing import List

from cltl.combot.infra.config import ConfigurationManager
from cltl.combot.infra.event import Event, EventBus
from cltl.combot.infra.resource import ResourceManager
from cltl.combot.infra.time_util import timestamp_now
from cltl.combot.infra.topic_worker import TopicWorker
from cltl.eliza.api import Eliza
from cltl.combot.event.emissor import TextSignalEvent
from cltl_service.emissordata.client import EmissorDataClient
from emissor.representation.scenario import TextSignal

from spot.dialog.dialog_manager import DialogManager

logger = logging.getLogger(__name__)


CONTENT_TYPE_SEPARATOR = ';'


class SpotDialogService:
    @classmethod
    def from_config(cls, manager: DialogManager, emissor_client: EmissorDataClient,
                    event_bus: EventBus, resource_manager: ResourceManager,
                    config_manager: ConfigurationManager):
        config = config_manager.get_config("spot.dialog")

        text_input_topic = config.get("topic_text_input")
        game_input_topic = config.get("topic_game_input")
        output_topic = config.get("topic_text_output")

        intention_topic = config.get("topic_intention") if "topic_intention" in config else None
        desire_topic = config.get("topic_desire") if "topic_desire" in config else None
        intentions = config.get("intentions", multi=True) if "intentions" in config else []

        return cls(text_input_topic, game_input_topic, output_topic,
                   intention_topic, desire_topic, intentions,
                   manager, emissor_client, event_bus, resource_manager)

    def __init__(self, text_input_topic: str, game_input_topic: str, output_topic: str,
                 intention_topic: str, desire_topic: str, intentions: List[str],
                 manager: DialogManager, emissor_client: EmissorDataClient,
                 event_bus: EventBus, resource_manager: ResourceManager):
        self._manager = manager

        self._event_bus = event_bus
        self._resource_manager = resource_manager
        self._emissor_client = emissor_client

        self._text_input_topic = text_input_topic
        self._game_input_topic = game_input_topic
        self._output_topic = output_topic

        self._intention_topic = intention_topic
        self._desire_topic = desire_topic
        self._intentions = intentions

        self._topic_worker = None

    @property
    def app(self):
        return None

    def start(self, timeout=30):
        self._topic_worker = TopicWorker([self._text_input_topic, self._game_input_topic], self._event_bus,
                                         provides=[self._output_topic],
                                         intention_topic=self._intention_topic, intentions=self._intentions,
                                         resource_manager=self._resource_manager, processor=self._process,
                                         name=self.__class__.__name__)
        self._topic_worker.start().wait()

    def stop(self):
        if not self._topic_worker:
            pass

        self._topic_worker.stop()
        self._topic_worker.await_stop()
        self._topic_worker = None

    def _process(self, event: Event[TextSignalEvent]):
        self._manager.set_replier(self._send_reply)
        if event.metadata.topic == self._text_input_topic:
            self._manager.utterance(event.payload.signal.text)
        elif event.metadata.topic == self._game_input_topic:
            self._manager.game_event(event.payload)

    def _send_reply(self, response):
        if not response:
            return

        scenario_id = self._emissor_client.get_current_scenario_id()
        signal = TextSignal.for_scenario(scenario_id, timestamp_now(), timestamp_now(), None, response)
        signal = TextSignalEvent.for_agent(signal)

        self._event_bus.publish(self._output_topic, Event.for_payload(signal))

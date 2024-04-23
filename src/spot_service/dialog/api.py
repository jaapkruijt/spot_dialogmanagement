import dataclasses
import uuid
from typing import Iterable, Any
from typing import Optional

from cltl.combot.event.emissor import AnnotationEvent
from emissor.representation.container import AtomicContainer, AtomicRuler, TemporalRuler
from emissor.representation.ldschema import emissor_dataclass
from emissor.representation.scenario import Signal, Mention, Modality
from emissor.representation.util import Identifier

from spot.dialog.dialog_manager import DisambigutionResult


@dataclasses.dataclass
class SpotterAnnotationEvent(AnnotationEvent):
    pass


@dataclasses.dataclass
class GameEvent:
    participant_id: Optional[str] = None
    participant_name: Optional[str] = None
    interaction: Optional[str] = "1"
    round: Optional[str] = None
    state: Optional[str] = None
    input: Optional[str] = None


@emissor_dataclass
class GameSignal(Signal[AtomicRuler, GameEvent], AtomicContainer[GameEvent]):
    @classmethod
    def for_scenario(cls: Any, scenario_id: Identifier, start: int, event: GameEvent = None,
                     mentions: Iterable[Mention] = None, signal_id: Optional[str] = None):
        signal_id = signal_id if signal_id else str(uuid.uuid4())

        return cls(signal_id, AtomicRuler(signal_id), event, Modality.VIDEO, TemporalRuler(scenario_id, start, start),
                   [], list(mentions) if mentions else [])
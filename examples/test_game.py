import random

from spot.dialog.dialog_manager import DisambiguatorStatus, DialogManager
from spot.dialog.conversations import GameStartStep
from spot_service.dialog.api import GameEvent


class TestDisambiguator:
    def __init__(self):
        self._status = DisambiguatorStatus.AWAIT_NEXT

    def status(self):
        return self._status.name

    def advance_round(self, round_number=None, start=False):
        pass

    def advance_position(self):
        pass

    def disambiguate(self, mention):
        # return disambiguator.disambiguate(mention)
        # and check status
        # returns selected (the referenced character), certainty, and status specific data (position, differences, etc.)
        choice = random.choice([0, 1, 2])
        if choice == 0:
            self._status = DisambiguatorStatus.NO_MATCH
            return None, None, None, None
        elif choice == 1:
            self._status = DisambiguatorStatus.SUCCESS_HIGH
            split_ = mention.split(" ")[-2:]
            return split_[0], 1.0, split_[1], None
        elif choice == 2:
            self._status = random.choice([DisambiguatorStatus.MATCH_PREVIOUS, DisambiguatorStatus.MATCH_MULTIPLE])
            return 1, 1, 1, ["differences"]
        raise  ValueError()


dialog_manager = DialogManager(TestDisambiguator(), storage_path=None, max_position=3)

reply = {"value": None, "position": 0}
def replier(reply_str, state):
    reply["value"] = reply_str
    print("Output:", reply_str, "state:", state)


dialog_manager.set_replier(replier)

for i in GameStartStep.STATEMENTS:
    print("Input:", "bla")
    dialog_manager.utterance(random.choice([None, "bla"]))
print("Input (Gane): submit")
dialog_manager.game_event(GameEvent(participant_id="1"))

for i in GameStartStep.STATEMENTS:
    print("Input:", "bla")
    dialog_manager.utterance(random.choice([None, "bla"]))
print("Input (Gane): submit")
dialog_manager.game_event(GameEvent(participant_id="1"))

position = 1
# TODO advance position, parse in test disambiguator
while position < 4:
    input = f"Number {position} {position}"
    print("Input:", input)
    dialog_manager.utterance(input)
    if "Goodbye" in reply["value"]:
        exit()
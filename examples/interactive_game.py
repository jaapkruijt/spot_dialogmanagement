import logging

from spot.pragmatic_model.model_ambiguity import Disambiguator
from spot.pragmatic_model.world_short_phrases_nl import ak_characters, ak_robot_scene

from spot.dialog.dialog_manager import DialogManager

logger = logging.getLogger(__name__)


def replier(reply):
    print("Robot > ", reply)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )

    disambiguator = Disambiguator(ak_characters, ak_robot_scene)
    dialog_manager = DialogManager(disambiguator, max_position=3)

    dialog_manager.set_replier(replier)

    human_input = None
    while human_input != "Tot ziens".lower():
        logger.debug("Await human input", )
        human_input = input("Human > ")
        logger.debug("Human input: %s", human_input)
        if human_input.lower().startswith("game:"):
            dialog_manager.game_event(human_input[5:])
        else:
            dialog_manager.utterance(human_input)
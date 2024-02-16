import dataclasses
from typing import Tuple, Iterator, Optional, Iterable, ClassVar


@dataclasses.dataclass(frozen=True)
class GameStartStep:
    step: int = -1
    statement: Optional[str] = None
    final: bool = False

    STATEMENTS: ClassVar[Tuple[str, ...]] = ("Hoi!", "Laten we een spelletje spelen.", "Leuk hoor!")

    def next(self):
        step = min(self.step + 1, len(self.STATEMENTS) - 1)
        statement = self.STATEMENTS[step]

        return GameStartStep(step, statement, step == len(self.STATEMENTS) - 1)


@dataclasses.dataclass(frozen=True)
class IntroStep:
    step: int = -1
    statement: Optional[str] = None
    final: bool = False

    STATEMENTS: ClassVar[Tuple[str, ...]] = ("Laten we het even proberen.", "Selecteer een figuur.", "Veel plezier!")

    def next(self):
        step = min(self.step + 1, len(self.STATEMENTS) - 1)
        statement = self.STATEMENTS[step]

        return IntroStep(step, statement, step == len(self.STATEMENTS) - 1)


if __name__ == '__main__':
    intro = IntroStep()
    for _ in range(5):
        print(intro)
        intro = intro.next()

    game = GameStartStep()
    for _ in range(5):
        print(game)
        game = game.next()

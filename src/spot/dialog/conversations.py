import dataclasses
from typing import Optional, List


@dataclasses.dataclass(frozen=True)
class GameStartStep:
    statements: List[str] = ()
    step: int = -1
    statement: Optional[str] = None
    final: bool = False

    def next(self):
        step = min(self.step + 1, len(self.statements) - 1)
        statement = self.statements[step]

        return GameStartStep(self.statements, step, statement, step == len(self.statements) - 1)


@dataclasses.dataclass(frozen=True)
class IntroStep:
    statements: List[str] = ()
    step: int = -1
    statement: Optional[str] = None
    final: bool = False

    def next(self):
        step = min(self.step + 1, len(self.statements) - 1)
        statement = self.statements[step]

        return IntroStep(self.statements, step, statement, step == len(self.statements) - 1)


@dataclasses.dataclass(frozen=True)
class OutroStep:
    statements: List[List] = ()
    step: int = -1
    statement: Optional[str] = None
    store_input: bool = False
    final: bool = False

    def next(self):
        step = min(self.step + 1, len(self.statements) - 1)
        statement, store_input = self.statements[step]

        return OutroStep(self.statements, step, statement, store_input, step == len(self.statements) - 1)


if __name__ == '__main__':
    intro = IntroStep()
    for _ in range(5):
        print(intro)
        intro = intro.next()

    game = GameStartStep()
    for _ in range(5):
        print(game)
        game = game.next()

import dataclasses
from typing import Tuple, Iterator, Optional, Iterable, ClassVar


@dataclasses.dataclass(frozen=True)
class GameStartStep:
    step: int = -1
    statement: Optional[str] = None
    final: bool = False

    STATEMENTS: ClassVar[Tuple[str, ...]] = ("Hoi, mijn naam is Robin. Hoe heet jij?!",
                                             "Oke, leuk dat je meedoet met dit spelletje! Het gaat over mijn drie vrienden. Ik zal ze aan je voorstellen. \pau=700\  Zie je, de theblet, op die standaard naast mij?",
                                             "Als je op de knop op het scherm drukt, dan zie je mijn vrienden. Kijk goed naar hun gezichten. Die moet je een beetje onthouden.",
                                             "Deze vrienden gaan overal naar toe, en maken dan een footo. Soms staan ze ook op de footo met anderen. Maar, op jouw footo staan mijn vrienden op een andere plek, dan bij mij. Daar maken we een leuk spelletje van. Wij gaan elke ronde samen uitzoeken, wie waar staat, goed?",
                                             "Het werkt als volgt. We gaan de vrienden 1 voor 1 langs. Jij vertelt wie je op \pau=100\ elke plek ziet, en dan vertel ik, of dat bij mij het zelfde is, of anders. Als we goed overleggen, vinden we samen de verschillen! Leuk toch?",
                                             "Laten we dit even oefenen. Druk maar op de knop om door te gaan naar de oefenronde.")

    def next(self):
        step = min(self.step + 1, len(self.STATEMENTS) - 1)
        statement = self.STATEMENTS[step]

        return GameStartStep(step, statement, step == len(self.STATEMENTS) - 1)


@dataclasses.dataclass(frozen=True)
class IntroStep:
    step: int = -1
    statement: Optional[str] = None
    final: bool = False

    STATEMENTS: ClassVar[Tuple[str, ...]] = ("Beschrijf nu maar aan mij, wie er bij jou, op de eerste plek staat, zodat ik begrijp wie je bedoelt. Je kunt bijvoorbeeld aan mij vertellen \pau=20\ hoe hun gezicht er \pau=20\ uit ziet, of iets anders \pau=25\ dat opvalt",
                                             "Oh ja, die staat bij mij op de tweede plek. Je kan nu op het cijfer 1 tikken. Er opent dan een menuutje. Daarin kan je het cijfer 2 invullen, om aan te geven dat die op de tweede plek staat bij mij. Als je dat gedaan hebt, verschijnt er een vinkje om aan te geven dat je het hebt ingevuld. Klopt dat?",
                                             "Mooi! In het echte spel moeten we samen de antwoorden vinden voor alle vrienden. Voor we doorgaan naar het echte spel \pau=20\ nog even een paar spelregels. Je krijgt het plaatje maar een paar seconden te zien. \pau=15\ Onthoud dus goed wie waar staat, en hoe die persoon er uit ziet. Daarna kun je vertellen wat je zag, en gaan wij overleggen wie \pau=10\ waar staat \pau=5\ op jouw plaatje, \pau=15\ en op de mijne. Is dat goed?",
                                             "Top. Als je bent vergeten wie je zag, kan je op het \pau=5\ scherm tikken \pau=10\ op de knop \pau=250\ Laat het plaatje zien. Maar, je moet ook goed naar mij kijken. Dat praat wat makkelijker, toch? Ben je klaar voor het echte spel?",
                                             "Oke. Het spel duurt in totaal 6 rondes. Je kunt elke keer naar beneden scrollen om het hele plaatje te zien. Klik maar op de knop Ga door op het scherm om te beginnen. Leuk hoor!"
                                             )

    def next(self):
        step = min(self.step + 1, len(self.STATEMENTS) - 1)
        statement = self.STATEMENTS[step]

        return IntroStep(step, statement, step == len(self.STATEMENTS) - 1)


@dataclasses.dataclass(frozen=True)
class OutroStep:
    step: int = -1
    statement: Optional[str] = None
    store_input: bool = False
    final: bool = False

    STATEMENTS: ClassVar[Tuple[str, ...]] = (("Dankjewel voor het invullen van de vragenlijst! Ik ben nog benieuwd naar iets: wat is eigenlijk jouw lievelings vakantiebestemming? Ga je liever naar de bergen? naar een stad? of naar het strand.", True),
                                             ("Leuk om te horen. Dat ga ik onthouden. Tot volgende week.", False))

    def next(self):
        step = min(self.step + 1, len(self.STATEMENTS) - 1)
        statement, store_input = self.STATEMENTS[step]

        return OutroStep(step, statement, store_input, step == len(self.STATEMENTS) - 1)


if __name__ == '__main__':
    intro = IntroStep()
    for _ in range(5):
        print(intro)
        intro = intro.next()

    game = GameStartStep()
    for _ in range(5):
        print(game)
        game = game.next()

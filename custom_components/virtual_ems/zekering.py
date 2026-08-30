"""De hoofdzekering, zodat te veel vragen ook echt gevolgen heeft.

Zonder dit bestand kan een cursist alles tegelijk aanzetten, de belastbaarheid
boven de honderd procent laten lopen, en gebeurt er niets. Dat is precies de
verkeerde les: in een echte woning smelt er dan iets en zit het hele huis in het
donker.

Het model is een warmtemodel en geen kopie van een smeltkarakteristiek. De
ijkpunten komen uit IEC 60269-1 voor een gG-smeltveiligheid met een nominale
stroom tot en met 63 A:

* bij 1,25 keer de nominale stroom smelt hij binnen de conventionele tijd niet,
* bij 1,6 keer de nominale stroom smelt hij binnen de conventionele tijd wel,
* en die conventionele tijd is één uur.

De warmte loopt op met het kwadraat van de stroom boven de niet-smeltstroom, en
zakt weer als de belasting eronder komt. De schaal is zo gekozen dat 1,6 keer de
nominale stroom precies in een uur bij de smeltgrens komt.

**Wat dit model niet is.** Bij een zware overbelasting is een echte zekering veel
sneller: bij vijf keer de nominale stroom smelt hij in de orde van seconden,
terwijl dit model er minuten over doet. Voor het practicum gaat het om het
principe, en de tijdversnelling van de simulatie maakt dat uur bovendien kort.
Wie een echte selectiviteitsberekening wil doen, heeft de curve van de
fabrikant nodig en niet dit bestand.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: Conventionele niet-smeltstroom van een gG-veiligheid, als factor van In.
NIET_SMELTSTROOM = 1.25

#: Conventionele smeltstroom van een gG-veiligheid, als factor van In.
SMELTSTROOM = 1.6

#: Conventionele tijd voor In tot en met 63 A, in seconden.
CONVENTIONELE_TIJD_S = 3600.0

#: De schaal volgt uit de twee ijkpunten hierboven: bij de smeltstroom moet de
#: warmte in de conventionele tijd van nul naar één lopen.
SCHAAL_S = (SMELTSTROOM**2 - NIET_SMELTSTROOM**2) * CONVENTIONELE_TIJD_S

#: Hoe snel de warmte weer wegzakt als de belasting onder de niet-smeltstroom
#: komt. Even snel als hij opliep, want het is hetzelfde stukje metaal.
AFKOELTIJD_S = CONVENTIONELE_TIJD_S


@dataclass
class Zekering:
    """De hoofdzekering van de aansluiting.

    De belasting wordt in vermogen aangeleverd en niet in stroom. Dat mag hier:
    de simulatie rekent met één spanning, dus vermogen en stroom lopen recht
    evenredig, en de verhouding tot de nominale waarde is wat telt.
    """

    #: Wat de aansluiting continu aankan, in W.
    nominaal_w: float
    #: Hoe warm de zekering is. Nul is koud, één is doorgesmolten.
    warmte: float = 0.0
    gesprongen: bool = False

    @property
    def warmte_pct(self) -> float:
        return max(0.0, min(100.0, self.warmte * 100.0))

    def stap(self, vermogen_w: float, seconden: float) -> bool:
        """Werk de warmte bij. Geeft True als de zekering nu net doorsmelt.

        Teruglevering belast de zekering net zo goed als afname, dus de absolute
        waarde telt.
        """
        if self.gesprongen or seconden <= 0 or self.nominaal_w <= 0:
            return False

        verhouding = abs(vermogen_w) / self.nominaal_w
        if verhouding > NIET_SMELTSTROOM:
            self.warmte += (verhouding**2 - NIET_SMELTSTROOM**2) * seconden / SCHAAL_S
        else:
            self.warmte = max(0.0, self.warmte - seconden / AFKOELTIJD_S)

        if self.warmte >= 1.0:
            self.warmte = 1.0
            self.gesprongen = True
            return True
        return False

    def resterende_tijd_s(self, vermogen_w: float) -> float | None:
        """Hoe lang de zekering deze belasting nog volhoudt, in seconden.

        Geeft None als hij het bij deze belasting oneindig volhoudt, en 0 als hij
        al doorgesmolten is. Dit is geen voorspelling van de toekomst maar een
        rechttoe rechtaan som op de huidige belasting; verandert er iets, dan
        verandert het antwoord mee.
        """
        if self.gesprongen:
            return 0.0
        if self.nominaal_w <= 0:
            return None
        verhouding = abs(vermogen_w) / self.nominaal_w
        boven = verhouding**2 - NIET_SMELTSTROOM**2
        if boven <= 0:
            return None
        return max(0.0, (1.0 - self.warmte) * SCHAAL_S / boven)

    def herstel(self) -> None:
        """Een nieuwe zekering erin. Dit is werk voor de docent, niet voor de kaart."""
        self.warmte = 0.0
        self.gesprongen = False

    def as_dict(self) -> dict[str, Any]:
        return {"warmte": self.warmte, "gesprongen": self.gesprongen}

    def restore(self, data: dict[str, Any]) -> None:
        if not isinstance(data, dict):
            return
        self.warmte = max(0.0, min(1.0, float(data.get("warmte", 0.0))))
        self.gesprongen = bool(data.get("gesprongen", False))

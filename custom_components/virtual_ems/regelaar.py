"""De regelaar: het stuk dat van een installatie een energiemanagementsysteem maakt.

Zonder dit bestand is er alleen een huis met knoppen. Hier staat wat een EMS
werkelijk doet: elke ronde opnieuw beslissen wat de batterij en de laadpaal
moeten doen, met een doel en met grenzen, en daarna verantwoorden waarom.

Er zijn drie modussen en een vangnet.

* **handmatig** doet niets aan het doel: de cursist bepaalt zelf wat de batterij
  doet. Dit is de stand waarin je ziet hoe lastig het met de hand is.
* **zelfconsumptie** stuurt de batterij zo dat er zo min mogelijk over de
  aansluiting gaat: overschot van de zon erin, tekort van het huis eruit.
* **piekscheren** houdt de afname onder een grens die de docent instelt, en
  laadt daarbuiten met het overschot.

Het vangnet, de aansluitbewaking, staat los van de modus en werkt altijd als het
aan staat: het houdt de installatie binnen wat de aansluiting aankan. Het regelt
in vaste volgorde terug, want niet alles is even makkelijk uit te zetten. Een
wasmachine kun je niet halverwege afknijpen, een laadpaal wel.

Dit bestand kent Home Assistant niet en is dus los door te rekenen tegen een
hele dag.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MODUS_HANDMATIG = "handmatig"
MODUS_ZELFCONSUMPTIE = "zelfconsumptie"
MODUS_PIEKSCHEREN = "piekscheren"

MODUSSEN: tuple[str, ...] = (MODUS_HANDMATIG, MODUS_ZELFCONSUMPTIE, MODUS_PIEKSCHEREN)

#: Onder dit vermogen noemen we iets nul. Anders staat er om de haverklap een
#: reden op het scherm over twee watt.
DREMPEL_W = 25.0


@dataclass(frozen=True)
class Situatie:
    """Wat de regelaar op dit moment aantreft."""

    #: Wat de panelen zouden leveren als er niets afgeregeld wordt.
    pv_w: float
    #: Wat het huis vraagt, basislast plus de apparaten die aan staan.
    household_w: float
    #: Wat de laadpaal zou vragen als niemand hem terugregelt.
    ev_request_w: float
    #: Wat de cursist zelf op de batterij heeft gezet.
    battery_request_w: float
    #: Wat er op dit moment in de batterij past en uit kan, in W.
    max_charge_w: float
    max_discharge_w: float
    #: Wat de aansluiting aankan, in W.
    connection_w: float


@dataclass
class Besluit:
    """Wat de regelaar besloten heeft, en waarom."""

    battery_w: float
    ev_w: float
    pv_w: float
    redenen: list[str] = field(default_factory=list)
    #: Heeft de regelaar iets anders gedaan dan de cursist vroeg?
    ingegrepen: bool = False
    #: Staat er meer op de aansluiting dan hij aankan, zonder dat de regelaar er
    #: nog iets aan kan doen?
    knelpunt: bool = False

    @property
    def reden(self) -> str:
        """De belangrijkste reden, of een lege tekst als er niets te melden is."""
        return self.redenen[0] if self.redenen else ""


def _kw(watt: float) -> str:
    """Een vermogen in kW met een komma, zoals het op het scherm komt."""
    return f"{watt / 1000:.2f}".replace(".", ",")


def bepaal(
    situatie: Situatie,
    *,
    modus: str = MODUS_HANDMATIG,
    bewaking: bool = True,
    piekgrens_w: float = 0.0,
) -> Besluit:
    """Beslis wat de batterij, de laadpaal en de omvormer moeten doen."""
    pv = max(0.0, situatie.pv_w)
    huis = max(0.0, situatie.household_w)
    ev = max(0.0, situatie.ev_request_w)

    besluit = Besluit(battery_w=situatie.battery_request_w, ev_w=ev, pv_w=pv)

    # --- 1. Het doel: wat wil de regelaar dat de batterij doet ---------------

    if modus == MODUS_ZELFCONSUMPTIE:
        # Het saldo zonder de batterij is precies wat de batterij moet opvangen.
        # Een tekort moet de batterij aanvullen (ontladen, dus negatief), een
        # overschot moet hij opnemen (laden, dus positief). Vandaar het minteken.
        saldo = huis + ev - pv
        besluit.battery_w = _begrens_batterij(-saldo, situatie)
        if besluit.battery_w > DREMPEL_W:
            besluit.redenen.append(
                f"De batterij laadt met {_kw(besluit.battery_w)} kW met het overschot van de zon."
            )
        elif besluit.battery_w < -DREMPEL_W:
            besluit.redenen.append(
                f"De batterij ontlaadt met {_kw(-besluit.battery_w)} kW om het huis te dekken."
            )
        elif saldo > DREMPEL_W:
            besluit.redenen.append("De batterij kan niet verder ontladen, dus het net vult aan.")
        besluit.ingegrepen = True

    elif modus == MODUS_PIEKSCHEREN:
        grens = max(0.0, piekgrens_w)
        saldo = huis + ev - pv
        if saldo > grens:
            # Boven de piekgrens: de batterij vult het verschil aan.
            besluit.battery_w = _begrens_batterij(-(saldo - grens), situatie)
            # Wat er overblijft nadat de batterij gedaan heeft wat hij kon. Dit
            # is het verschil tussen willen en kunnen, en dat hoort er eerlijk
            # te staan: melden dat de piek gehouden wordt terwijl hij dat niet
            # doet is erger dan niets melden.
            rest = saldo + besluit.battery_w
            if besluit.battery_w < -DREMPEL_W and rest <= grens + DREMPEL_W:
                besluit.redenen.append(
                    f"De batterij ontlaadt met {_kw(-besluit.battery_w)} kW om de afname "
                    f"onder {_kw(grens)} kW te houden."
                )
            elif besluit.battery_w < -DREMPEL_W:
                besluit.redenen.append(
                    f"De batterij ontlaadt met {_kw(-besluit.battery_w)} kW, maar de afname "
                    f"blijft met {_kw(rest)} kW boven de grens van {_kw(grens)} kW."
                )
            else:
                besluit.redenen.append(
                    f"De afname wil boven {_kw(grens)} kW, maar de batterij kan niet verder "
                    "ontladen."
                )
        elif saldo < -DREMPEL_W:
            # Overschot: opslaan in plaats van terugleveren.
            besluit.battery_w = _begrens_batterij(-saldo, situatie)
            if besluit.battery_w > DREMPEL_W:
                besluit.redenen.append(
                    f"De batterij laadt met {_kw(besluit.battery_w)} kW met het overschot."
                )
        else:
            besluit.battery_w = 0.0
            besluit.redenen.append(
                f"De afname blijft onder {_kw(grens)} kW, dus de batterij hoeft niets te doen."
            )
        besluit.ingegrepen = True

    else:
        besluit.battery_w = _begrens_batterij(situatie.battery_request_w, situatie)

    # --- 2. Het vangnet: binnen wat de aansluiting aankan --------------------

    if bewaking and situatie.connection_w > 0:
        besluit = _bewaak_aansluiting(besluit, situatie, huis)

    return besluit


def _begrens_batterij(gevraagd: float, situatie: Situatie) -> float:
    """Knijp een verzoek af op wat er nu werkelijk in of uit kan.

    De natuurkunde in simulation.py doet dit ook, maar de regelaar moet het zelf
    weten: anders zet hij een reden op het scherm over vermogen dat er niet is.
    """
    if gevraagd > 0:
        return min(gevraagd, max(0.0, situatie.max_charge_w))
    if gevraagd < 0:
        return -min(-gevraagd, max(0.0, situatie.max_discharge_w))
    return 0.0


def _bewaak_aansluiting(besluit: Besluit, situatie: Situatie, huis: float) -> Besluit:
    """Houd de installatie binnen wat de aansluiting aankan.

    De volgorde is niet willekeurig. Eerst gaat weg wat niemand mist, daarna wat
    uitgesteld kan worden, en pas als laatste wordt er bijgeschakeld. Wat een
    cursist zelf heeft aangezet, de wasmachine en de boiler, blijft staan: dat is
    precies de grens van wat een EMS kan.
    """
    grens = situatie.connection_w

    # De redenen van het vangnet komen in de volgorde waarin er is ingegrepen,
    # en ze gaan voor de reden van de modus: wat er zojuist is afgeknepen is
    # belangrijker dan wat de regelaar van plan was. Zouden ze omgekeerd staan,
    # dan komt een ingreep van twintig watt bovenaan het scherm terwijl er vijf
    # kilowatt is teruggeregeld. Dat is gemeten en het las verkeerd.
    vangnet: list[str] = []

    saldo = huis + besluit.ev_w + besluit.battery_w - besluit.pv_w

    # a. Te veel afname.
    if saldo > grens:
        if besluit.battery_w > DREMPEL_W:
            # Laden kan wachten.
            weg = min(besluit.battery_w, saldo - grens)
            besluit.battery_w -= weg
            saldo -= weg
            besluit.ingegrepen = True
            vangnet.append(
                f"Het laden van de batterij is {_kw(weg)} kW teruggeregeld voor de aansluiting."
            )

    if saldo > grens and besluit.ev_w > DREMPEL_W:
        gevraagd = besluit.ev_w
        besluit.ev_w = max(0.0, besluit.ev_w - (saldo - grens))
        saldo = huis + besluit.ev_w + besluit.battery_w - besluit.pv_w
        besluit.ingegrepen = True
        vangnet.append(
            f"De laadpaal is teruggeregeld van {_kw(gevraagd)} naar {_kw(besluit.ev_w)} kW "
            "om binnen de aansluiting te blijven."
        )

    if saldo > grens:
        extra = _begrens_batterij(besluit.battery_w - (saldo - grens), situatie)
        if extra < besluit.battery_w - DREMPEL_W:
            erbij = besluit.battery_w - extra
            besluit.battery_w = extra
            saldo = huis + besluit.ev_w + besluit.battery_w - besluit.pv_w
            besluit.ingegrepen = True
            vangnet.append(
                f"De batterij springt bij met {_kw(erbij)} kW om de aansluiting te ontlasten."
            )

    if saldo > grens:
        besluit.knelpunt = True
        # Een knelpunt gaat voorop: dat is het enige wat de cursist nu moet lezen.
        vangnet.insert(
            0,
            f"De aansluiting zit {_kw(saldo - grens)} kW over de grens en er valt niets meer "
            "terug te regelen. Zet zelf iets uit.",
        )
        besluit.redenen = vangnet + besluit.redenen
        return besluit

    # b. Te veel teruglevering. Dit kan alleen bij een grote installatie op een
    #    kleine aansluiting, maar dan wel meteen.
    if -saldo > grens:
        extra = _begrens_batterij(besluit.battery_w + (-saldo - grens), situatie)
        if extra > besluit.battery_w + DREMPEL_W:
            erbij = extra - besluit.battery_w
            besluit.battery_w = extra
            saldo = huis + besluit.ev_w + besluit.battery_w - besluit.pv_w
            besluit.ingegrepen = True
            vangnet.append(f"De batterij vangt {_kw(erbij)} kW van de teruglevering op.")

    if -saldo > grens:
        # Laatste redmiddel: de omvormer terugregelen. Dat kost opbrengst, en
        # daarom staat het achteraan.
        te_veel = -saldo - grens
        afgeregeld = min(besluit.pv_w, te_veel)
        besluit.pv_w -= afgeregeld
        besluit.ingegrepen = True
        vangnet.append(f"De omvormer is {_kw(afgeregeld)} kW teruggeregeld; die opbrengst is weg.")
        saldo = huis + besluit.ev_w + besluit.battery_w - besluit.pv_w
        if -saldo > grens:
            besluit.knelpunt = True

    besluit.redenen = vangnet + besluit.redenen
    return besluit

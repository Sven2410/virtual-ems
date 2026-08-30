"""Bewakers op de frontend.

Dit zijn fouten die al eens gemaakt zijn en die een script kan vangen. Ze hangen
daarom aan de proefronde (tests/kern/test_frontend.py) en aan CI, en niet aan of
iemand eraan denkt dit script te draaien.

Los te draaien:

    python scripts/bewaak_frontend.py
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
FRONTEND = REPO / "custom_components" / "virtual_ems" / "frontend"
REGISTRATIEBESTAND = "registratie.js"


@dataclass(frozen=True)
class Klacht:
    bestand: str
    regel: int
    uitleg: str

    def __str__(self) -> str:
        return f"{self.bestand}:{self.regel}: {self.uitleg}"


def js_bestanden() -> list[Path]:
    return sorted(FRONTEND.rglob("*.js"))


# --- 1. Een stijlblok dat middenin een commentaar ophoudt --------------------


def _template_literalen(bron: str) -> list[tuple[int, str]]:
    """Geef elk stukje tussen accent graves, met het regelnummer van de start.

    Dit is geen volledige javascriptontleder en hoeft dat ook niet te zijn: de
    stijlblokken in dit project staan altijd op zichzelf.
    """
    gevonden: list[tuple[int, str]] = []
    positie = 0
    while True:
        start = bron.find("`", positie)
        if start == -1:
            break
        einde = bron.find("`", start + 1)
        if einde == -1:
            break
        regel = bron.count("\n", 0, start) + 1
        gevonden.append((regel, bron[start + 1 : einde]))
        positie = einde + 1
    return gevonden


def controleer_stijlblokken() -> list[Klacht]:
    """Vang niet de accent grave zelf, maar het gevolg ervan.

    Alle stijlen staan in een template-literal, en een accent grave in een
    CSS-commentaar sluit die string af. Soms is dat een bouwfout binnen een
    minuut, maar niet altijd: het is ook al eens geldige javascript geworden die
    bouwde, laadde, en daarna de hele bundel omgooide. node --check gaf daar
    groen op. Het gevolg is wél te zien: een stijlblok dat ophoudt terwijl er nog
    een commentaar openstaat.
    """
    klachten: list[Klacht] = []
    for bestand in js_bestanden():
        bron = bestand.read_text(encoding="utf-8")
        for regel, inhoud in _template_literalen(bron):
            if "/*" not in inhoud:
                continue
            open_aantal = inhoud.count("/*")
            sluit_aantal = inhoud.count("*/")
            if open_aantal != sluit_aantal:
                klachten.append(
                    Klacht(
                        bestand.name,
                        regel,
                        "een stijlblok houdt op terwijl er nog een commentaar openstaat; "
                        "staat er een accent grave in dat commentaar?",
                    )
                )
    return klachten


# --- 2. Registratie op één plek ----------------------------------------------


def controleer_registratie() -> list[Klacht]:
    """customElements.define hoort op precies één plek te staan.

    Home Assistant draait scoped-custom-element-registry. Win je de race met
    zijn eigen import(), dan is je element daarna onzichtbaar, zonder fout en
    zonder logregel. Kennis in één bestand is geen bewaking, dus dit script
    kijkt na.
    """
    klachten: list[Klacht] = []
    for bestand in js_bestanden():
        if bestand.name == REGISTRATIEBESTAND:
            continue
        for nummer, regel in enumerate(bestand.read_text(encoding="utf-8").splitlines(), start=1):
            if "customElements.define" in regel:
                klachten.append(
                    Klacht(
                        bestand.name,
                        nummer,
                        f"registreer elementen alleen in {REGISTRATIEBESTAND}",
                    )
                )
    return klachten


# --- 3. Niets vasts aan het scherm zonder reden ------------------------------


def controleer_position_fixed() -> list[Klacht]:
    """position: fixed is niet vast aan het scherm zodra een voorouder een
    transform, filter of backdrop-filter heeft; dan wordt die het referentievlak.

    Er zweeft in deze frontend niets, dus fixed hoort er niet in te staan. Komt
    er ooit een menu of een dialoog bij, dan hangt die aan document.body en mag
    deze bewaker aangepast worden, met die uitleg erbij.
    """
    klachten: list[Klacht] = []
    patroon = re.compile(r"position\s*:\s*fixed")
    for bestand in js_bestanden():
        for nummer, regel in enumerate(bestand.read_text(encoding="utf-8").splitlines(), start=1):
            if patroon.search(regel):
                klachten.append(
                    Klacht(
                        bestand.name,
                        nummer,
                        "position: fixed hangt aan de dichtstbijzijnde voorouder met een "
                        "transform of filter; hang zwevende dingen aan document.body",
                    )
                )
    return klachten


# --- 4. Het attribuut hidden verliest van elke display -----------------------


def controleer_hidden() -> list[Klacht]:
    """Wie iets met het attribuut hidden verbergt heeft de bijbehorende
    CSS-regel nodig, anders staat het blok gewoon in beeld."""
    gebruikt = any(
        "hidden" in bestand.read_text(encoding="utf-8") and "setAttribute" in bestand.read_text(encoding="utf-8")
        for bestand in js_bestanden()
    )
    if not gebruikt:
        return []
    stijl = (FRONTEND / "stijl.js").read_text(encoding="utf-8")
    if "[hidden]" in stijl and "display: none" in stijl:
        return []
    return [Klacht("stijl.js", 0, "er wordt met hidden verborgen, maar [hidden] staat niet in de stijl")]


# --- 5. De entiteitenlijst aan beide kanten ----------------------------------


def _lijst_uit_js(bron: str, naam: str) -> list[str]:
    patroon = re.compile(r"export const " + naam + r"\s*=\s*\[(.*?)\]", re.S)
    treffer = patroon.search(bron)
    if not treffer:
        return []
    return re.findall(r'"([^"]+)"', treffer.group(1))


def frontend_entiteiten() -> dict[str, list[str]]:
    bron = (FRONTEND / "entiteiten.js").read_text(encoding="utf-8")
    return {
        "sensor": _lijst_uit_js(bron, "SENSOREN"),
        "number": _lijst_uit_js(bron, "NUMMERS"),
        "switch": _lijst_uit_js(bron, "SCHAKELAARS"),
    }


def controleer_entiteiten(catalogus: dict[str, tuple[str, ...]]) -> list[Klacht]:
    """De frontend en catalog.py moeten dezelfde entiteiten kennen.

    Een kaart die naar een entiteit wijst die niet bestaat geeft geen fout en
    geen logregel; hij blijft gewoon leeg.
    """
    klachten: list[Klacht] = []
    van_js = frontend_entiteiten()
    for platform, sleutels in catalogus.items():
        js = set(van_js.get(platform, []))
        py = set(sleutels)
        for ontbreekt in sorted(py - js):
            klachten.append(
                Klacht("entiteiten.js", 0, f"{platform}.{ontbreekt} staat wel in catalog.py maar niet hier")
            )
        for te_veel in sorted(js - py):
            klachten.append(
                Klacht("entiteiten.js", 0, f"{platform}.{te_veel} staat hier maar niet in catalog.py")
            )
    return klachten


# --- 6. Geen gedachtestreepjes in wat een cursist leest ----------------------


def controleer_streepjes() -> list[Klacht]:
    klachten: list[Klacht] = []
    for bestand in js_bestanden():
        for nummer, regel in enumerate(bestand.read_text(encoding="utf-8").splitlines(), start=1):
            if "—" in regel or "–" in regel:
                klachten.append(Klacht(bestand.name, nummer, "hier staat een gedachtestreepje"))
    return klachten


# --- Alles bij elkaar --------------------------------------------------------


def catalogus() -> dict[str, tuple[str, ...]]:
    """Lees catalog.py zonder het Home Assistant-pakket eromheen te laden.

    Zelfde reden als in tests/kern/kernlader.py: het importeren van
    custom_components.virtual_ems.catalog voert eerst __init__.py uit, en dat is
    het aanknopingspunt voor Home Assistant. Deze bewaker moet ook draaien op
    een machine waar Home Assistant niet staat.
    """
    import importlib
    import types

    pakket = "virtual_ems_bewaking"
    if pakket not in sys.modules:
        module = types.ModuleType(pakket)
        module.__path__ = [str(REPO / "custom_components" / "virtual_ems")]
        sys.modules[pakket] = module
    return importlib.import_module(f"{pakket}.catalog").ENTITY_KEYS


def alle_klachten() -> list[Klacht]:
    ENTITY_KEYS = catalogus()

    return (
        controleer_stijlblokken()
        + controleer_registratie()
        + controleer_position_fixed()
        + controleer_hidden()
        + controleer_entiteiten(ENTITY_KEYS)
        + controleer_streepjes()
    )


def main() -> int:
    klachten = alle_klachten()
    if not klachten:
        aantal = len(js_bestanden())
        print(f"De frontend is in orde: {aantal} bestanden nagekeken.")
        return 0
    for klacht in klachten:
        print(str(klacht))
    print()
    print(f"{len(klachten)} klachten over de frontend.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

"""De lijst van alle entiteiten die deze integratie aanmaakt.

Dit bestand is bewust vrij van Home Assistant-imports, zodat een controle op de
dashboards en op de vertalingen overal te draaien is: op een Pi, op een laptop
zonder Home Assistant, en in de bouwstap.

De lijst is niet vrijblijvend. tests/ha/test_entiteiten.py zet de integratie
echt op en vergelijkt de aangemaakte entiteiten één op één met deze lijst, dus
een entiteit die hier ontbreekt of te veel staat laat die proef vallen.
"""

from __future__ import annotations

import re
import unicodedata

from .const import APPLIANCES


def slugify_naam(naam: str) -> str:
    """Maak van een installatienaam de slug die in de entity_id komt.

    Home Assistant gebruikt hiervoor python-slugify met een liggend streepje als
    scheidingsteken. Deze functie doet hetzelfde voor gewone namen zonder dat er
    een pakket geinstalleerd hoeft te zijn; tests/ha/test_entiteiten.py legt de
    twee naast elkaar.
    """
    ontdaan = unicodedata.normalize("NFKD", naam)
    ontdaan = "".join(teken for teken in ontdaan if not unicodedata.combining(teken))
    ontdaan = re.sub(r"[^a-zA-Z0-9]+", "_", ontdaan).strip("_").lower()
    return re.sub(r"_+", "_", ontdaan)

SENSOR_KEYS: tuple[str, ...] = (
    "pv_vermogen",
    "pv_opbrengst",
    "batterij_soc",
    "batterij_vermogen_actueel",
    "batterij_inhoud",
    "batterij_geladen",
    "batterij_ontladen",
    "laadpaal_vermogen",
    "laadpaal_verbruik",
    "huishoudelijk_verbruik",
    "verbruik_totaal",
    "net_vermogen",
    "net_afname",
    "net_teruglevering",
    "aansluiting_belasting",
    "zelfbenutting",
    "zonnehoogte",
    "simulatietijd",
) + tuple(f"{key}_verbruik" for key in APPLIANCES)

NUMBER_KEYS: tuple[str, ...] = (
    "pv_bewolking",
    "batterij_vermogen",
    "batterij_min_soc",
    "batterij_max_soc",
    "laadpaal_vermogen",
    "tijdversnelling",
)

SWITCH_KEYS: tuple[str, ...] = ("laadpaal_actief",) + tuple(APPLIANCES)

ENTITY_KEYS: dict[str, tuple[str, ...]] = {
    "sensor": SENSOR_KEYS,
    "number": NUMBER_KEYS,
    "switch": SWITCH_KEYS,
}


def entity_ids(slug: str) -> set[str]:
    """Alle entity_id's die bij een installatie met deze naam-slug horen."""
    return {
        f"{platform}.{slug}_{key}"
        for platform, keys in ENTITY_KEYS.items()
        for key in keys
    }

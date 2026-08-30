"""Waar de frontendbundel staat en welke versie het is.

Dit bestand kent Home Assistant niet, zodat de versieberekening in een gewone
unittest te draaien is. Het aanmelden bij Home Assistant zelf staat in
bundel.py.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from .const import DOMAIN

URL_BASIS = f"/{DOMAIN}_frontend"
BUNDELNAAM = "virtual-ems.js"
MAPNAAM = "frontend"

#: Lengte van de versieaanduiding. Twaalf hexadecimale tekens is genoeg om
#: twee uitgaven uit elkaar te houden en kort genoeg om in beeld te passen.
VERSIELENGTE = 12


def frontend_map() -> Path:
    return Path(__file__).parent / MAPNAAM


def bereken_versie(map_pad: Path | None = None) -> str:
    """Hash over alle frontendbestanden samen.

    Er wordt over de inhoud van alle bestanden gehasht en niet alleen over de
    ingang: die verandert niet als een kaart wijzigt. De bestandsnaam gaat mee,
    zodat een hernoemd bestand ook een andere hash geeft.
    """
    pad = map_pad or frontend_map()
    if not pad.is_dir():
        return "onbekend"
    digest = hashlib.sha256()
    for bestand in sorted(pad.rglob("*.js")):
        digest.update(bestand.name.encode("utf-8"))
        digest.update(bestand.read_bytes())
    return digest.hexdigest()[:VERSIELENGTE]


def bundel_url(versie: str) -> str:
    """De URL waarmee de frontend geladen wordt, met de versie erachter.

    Een gehashte URL overleeft geen service worker als hij in een pagina staat;
    hier geeft de integratie hem zelf af, dus dat speelt niet. De hash zorgt dat
    een nieuwe uitgave ook echt een ander adres is.
    """
    return f"{URL_BASIS}/{BUNDELNAAM}?v={versie}"

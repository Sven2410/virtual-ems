"""Zet de meegeleverde dashboards om naar een andere installatienaam.

De dashboards in dashboards/ gaan uit van de naam "Virtueel EMS", en dus van
entiteiten die met virtueel_ems_ beginnen. Heet jouw installatie anders, draai
dan bijvoorbeeld:

    python scripts/dashboard_naam.py "Lokaal A"

Dan komen de omgezette bestanden in dashboards/uit/ te staan. Met --toon worden
ze in plaats daarvan op het scherm gezet, zodat je ze meteen kunt plakken in de
ruwe configuratie-editor van Home Assistant.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from custom_components.virtual_ems.catalog import slugify_naam  # noqa: E402

BRON_SLUG = "virtueel_ems"
BESTANDEN = ("cursist-dashboard.yaml", "docent-dashboard.yaml")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("naam", help='De naam van de installatie, bijvoorbeeld "Lokaal A"')
    parser.add_argument("--toon", action="store_true", help="Zet het resultaat op het scherm")
    parser.add_argument(
        "--map",
        default=str(REPO / "dashboards" / "uit"),
        help="Map waar de omgezette bestanden komen te staan",
    )
    argumenten = parser.parse_args()

    slug = slugify_naam(argumenten.naam)
    if not slug:
        print("Die naam levert geen bruikbare entity_id op.", file=sys.stderr)
        return 1

    doelmap = Path(argumenten.map)
    if not argumenten.toon:
        doelmap.mkdir(parents=True, exist_ok=True)

    for bestandsnaam in BESTANDEN:
        bron = REPO / "dashboards" / bestandsnaam
        inhoud = bron.read_text(encoding="utf-8").replace(BRON_SLUG, slug)
        if argumenten.toon:
            print(f"# ---------- {bestandsnaam} ----------")
            print(inhoud)
        else:
            doel = doelmap / bestandsnaam
            doel.write_text(inhoud, encoding="utf-8")
            print(f"Geschreven: {doel}")

    if not argumenten.toon:
        print(f'Entiteiten heten nu {slug}_... (installatienaam "{argumenten.naam}").')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

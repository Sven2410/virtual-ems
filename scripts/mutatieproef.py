"""Bewijs dat de proeven onderscheidend zijn.

Een proef die altijd groen is bewijst niets. Dit script breekt telkens één ding
in de code of in de dashboards, draait de proef die dat hoort te vangen, en
verwacht dat hij rood wordt. Daarna wordt het bestand teruggezet.

Draaien:

    python scripts/mutatieproef.py                    # op Linux of macOS
    python scripts/mutatieproef.py --pytest-arg -p --pytest-arg windows_shim

Elke regel in de uitvoer zegt of de proef inderdaad viel. Blijft een proef
groen terwijl zijn onderwerp kapot is, dan bewaakt hij niets.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


REGELEINDE = "\n"


def lees(pad: Path) -> str:
    """Lees met de regeleindes vertaald, zodat de zoekteksten matchen."""
    with pad.open(encoding="utf-8") as bestand:
        return bestand.read()


def schrijf(pad: Path, tekst: str) -> None:
    """Schrijf met een enkel regeleinde, ook op Windows.

    Zou Python hier zijn eigen regeleinde gebruiken, dan zet het terugzetten van
    een bestand elke regel om naar CRLF en staat de hele repository na afloop als
    gewijzigd te boek, terwijl er inhoudelijk niets veranderd is.
    """
    with pad.open("w", encoding="utf-8", newline=REGELEINDE) as bestand:
        bestand.write(tekst)


REPO = Path(__file__).resolve().parents[1]
COMPONENT = REPO / "custom_components" / "virtual_ems"


@dataclass(frozen=True)
class Mutatie:
    naam: str
    bestand: Path
    zoek: str
    vervang: str
    proeven: tuple[str, ...]
    toelichting: str = ""
    extra: tuple[tuple[Path, str, str], ...] = field(default_factory=tuple)


MUTATIES: tuple[Mutatie, ...] = (
    Mutatie(
        naam="azimut via een enkele acos (de fout die op 21 juni de zon in het noorden zette)",
        bestand=COMPONENT / "simulation.py",
        zoek="""    east = -math.cos(decl) * math.sin(ha_rad)
    north = math.sin(decl) * math.cos(lat_rad) - math.cos(decl) * math.sin(lat_rad) * math.cos(ha_rad)
    azimuth = math.degrees(math.atan2(east, north)) % 360.0""",
        vervang="""    sin_zenith = math.sin(zenith)
    if abs(sin_zenith) < 1e-9:
        azimuth = 180.0
    else:
        cos_az = (math.sin(lat_rad) * cos_zenith - math.sin(decl)) / (math.cos(lat_rad) * sin_zenith)
        azimuth = math.degrees(math.acos(max(-1.0, min(1.0, cos_az))))""",
        proeven=(
            "tests/kern/test_simulation.py::test_zon_staat_op_zijn_hoogst_pal_in_het_zuiden",
            "tests/kern/test_simulation.py::test_zon_staat_s_ochtends_in_het_oosten_en_s_avonds_in_het_westen",
        ),
        toelichting="De zonnehoogte blijft kloppen, dus een schermafdruk verraadt dit niet.",
    ),
    Mutatie(
        naam="batterij laadt zonder te kijken hoeveel er nog in past",
        bestand=COMPONENT / "simulation.py",
        zoek="            power = min(request, max(0.0, allowed_w))",
        vervang="            power = request",
        proeven=(
            "tests/kern/test_simulation.py::test_soc_blijft_altijd_tussen_nul_en_honderd",
            "tests/kern/test_simulation.py::test_batterij_laadt_niet_boven_de_ingestelde_bovengrens",
        ),
    ),
    Mutatie(
        naam="batterij ontlaadt zonder ondergrens",
        bestand=COMPONENT / "simulation.py",
        zoek="            power = -min(-request, max(0.0, allowed_w))",
        vervang="            power = request",
        proeven=(
            "tests/kern/test_simulation.py::test_batterij_ontlaadt_niet_onder_de_ingestelde_ondergrens",
        ),
    ),
    Mutatie(
        naam="netvermogen telt de zon erbij op in plaats van eraf",
        bestand=COMPONENT / "simulation.py",
        zoek="        grid_w = household_w + ev_w + battery_w - pv_w",
        vervang="        grid_w = household_w + ev_w + battery_w + pv_w",
        proeven=(
            "tests/kern/test_simulation.py::test_net_vermogen_is_de_optelsom_van_alle_stromen",
            "tests/kern/test_simulation.py::test_energiebalans_over_een_hele_dag_klopt",
            "tests/kern/test_simulation.py::test_teruglevering_krijgt_een_negatief_netvermogen",
        ),
    ),
    Mutatie(
        naam="terugzetten laat de tellers staan",
        bestand=COMPONENT / "simulation.py",
        zoek="""        self.totals = Totals()
        for name, _power in self.config.appliances:
            self.totals.appliance_kwh[name] = 0.0

        self.set_soc_pct(start_soc_pct)""",
        vervang="        self.set_soc_pct(start_soc_pct)",
        proeven=(
            "tests/kern/test_simulation.py::test_reset_zet_de_tellers_en_de_soc_terug",
            "tests/kern/test_simulation.py::test_reset_met_alleen_tellers_laat_de_bediening_staan",
        ),
    ),
    Mutatie(
        naam="laadpaal springt in één stap naar zijn eindvermogen",
        bestand=COMPONENT / "simulation.py",
        zoek="""        rate = self.config.ev_max_power_w / EV_RAMP_SECONDS  # W per seconde
        step = rate * elapsed_s""",
        vervang="        step = self.config.ev_max_power_w",
        proeven=(
            "tests/kern/test_simulation.py::test_laadpaal_loopt_op_in_plaats_van_te_springen",
        ),
    ),
    Mutatie(
        naam="bewolking werkt niet meer door in de opbrengst",
        bestand=COMPONENT / "simulation.py",
        zoek="        power *= 1.0 - cloud / 100.0",
        vervang="        power *= 1.0",
        proeven=(
            "tests/kern/test_simulation.py::test_bewolking_verlaagt_de_opbrengst_evenredig",
            "tests/kern/test_scenarios.py::test_bewolkte_dag_levert_veel_minder_dan_een_zonnige_dag",
        ),
    ),
    Mutatie(
        naam="een tikfout in een entity_id op het cursist-dashboard",
        bestand=REPO / "dashboards" / "cursist-dashboard.yaml",
        zoek="            entity: sensor.virtueel_ems_net_afname",
        vervang="            entity: sensor.virtueel_ems_net_afnamen",
        proeven=(
            "tests/kern/test_dashboards.py::test_elke_entiteit_op_het_dashboard_bestaat_ook_echt",
        ),
        toelichting="Home Assistant meldt zoiets niet; de kaart wordt gewoon grijs.",
    ),
    Mutatie(
        naam="een scenarioknop die naar een niet-bestaand scenario wijst",
        bestand=REPO / "dashboards" / "docent-dashboard.yaml",
        zoek="                    scenario: lege_batterij",
        vervang="                    scenario: lege_accu",
        proeven=(
            "tests/kern/test_dashboards.py::test_dashboards_roepen_alleen_bestaande_services_aan",
            "tests/kern/test_dashboards.py::test_alle_scenarios_staan_op_het_docentdashboard",
        ),
    ),
    Mutatie(
        naam="een accent grave in een CSS-commentaar in de frontend",
        bestand=REPO / "custom_components" / "virtual_ems" / "frontend" / "stijl.js",
        zoek="  /* Een klasse die display zet wint van het attribuut hidden",
        vervang="  /* Een klasse die `display` zet wint van het attribuut hidden",
        proeven=("tests/kern/test_frontend.py::test_de_frontend_doorstaat_alle_bewakers",),
        toelichting="node --check gaf hier ooit groen op; de bundel viel pas in de browser om.",
    ),
    Mutatie(
        naam="een element dat buiten registratie.js geregistreerd wordt",
        bestand=REPO / "custom_components" / "virtual_ems" / "frontend" / "pagina.js",
        zoek="export class PaginaKaart extends Kaart {",
        vervang=(
            "customElements.define('virtual-ems-los', class extends HTMLElement {});\n\n"
            "export class PaginaKaart extends Kaart {"
        ),
        proeven=(
            "tests/kern/test_frontend.py::test_de_frontend_doorstaat_alle_bewakers",
            "tests/kern/test_frontend.py::test_elementen_worden_op_precies_een_plek_geregistreerd",
        ),
        toelichting="Zonder bewaking wint dit soms de race met de eigen import van HA.",
    ),
    Mutatie(
        naam="een entiteit die de frontend kent maar de integratie niet",
        bestand=REPO / "custom_components" / "virtual_ems" / "frontend" / "entiteiten.js",
        zoek='  "zelfbenutting",\n',
        vervang='  "zelfbenutting",\n  "zelfvoorziening",\n',
        proeven=(
            "tests/kern/test_frontend.py::test_de_entiteitenlijst_is_aan_beide_kanten_gelijk",
        ),
    ),
    Mutatie(
        naam="een stroomkleur die net iets anders is",
        bestand=REPO / "custom_components" / "virtual_ems" / "frontend" / "stijl.js",
        zoek="--dt-solar: #dc7300;",
        vervang="--dt-solar: #dc7400;",
        proeven=("tests/kern/test_frontend.py::test_de_zes_stroomkleuren_staan_er_letterlijk_in",),
        toelichting="Die kleuren zijn gezocht op OKLCH-scheiding; ongeveer bestaat niet.",
    ),
    Mutatie(
        naam="een webfont in de frontend",
        bestand=REPO / "custom_components" / "virtual_ems" / "frontend" / "stijl.js",
        zoek="export const baseCss = `",
        vervang=(
            "export const baseCss = `\n"
            '  @import url("https://fonts.googleapis.com/css2?family=Inter");'
        ),
        proeven=("tests/kern/test_frontend.py::test_er_wordt_geen_webfont_geladen",),
    ),
    Mutatie(
        naam="een ontbrekende Nederlandse naam voor een entiteit",
        bestand=COMPONENT / "translations" / "nl.json",
        zoek='      "net_teruglevering": {\n        "name": "Net teruglevering"\n      },\n',
        vervang="",
        proeven=(
            "tests/kern/test_repo.py::test_elke_entiteit_heeft_een_naam_in_beide_talen",
            "tests/kern/test_repo.py::test_beide_talen_hebben_dezelfde_sleutels",
        ),
    ),
    Mutatie(
        naam="een entiteit die wel bestaat maar niet in de catalogus staat",
        bestand=COMPONENT / "catalog.py",
        zoek='    "net_teruglevering",\n',
        vervang="",
        proeven=(
            "tests/ha/test_entiteiten.py::test_alle_entiteiten_uit_de_catalogus_bestaan_ook_echt",
        ),
        toelichting="Deze proef heeft Home Assistant nodig.",
    ),
)


def draai(proeven: tuple[str, ...], extra_argumenten: list[str]) -> tuple[bool, str]:
    opdracht = [sys.executable, "-m", "pytest", "-q", "--no-header", *extra_argumenten, *proeven]
    klaar = subprocess.run(opdracht, cwd=REPO, capture_output=True, text=True)
    laatste = [regel for regel in klaar.stdout.splitlines() if regel.strip()]
    samenvatting = laatste[-1] if laatste else "(geen uitvoer)"
    return klaar.returncode == 0, samenvatting


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pytest-arg",
        action="append",
        default=[],
        help="Extra argument voor pytest, bijvoorbeeld -p windows_shim",
    )
    argumenten = parser.parse_args()

    mislukt = 0
    for mutatie in MUTATIES:
        origineel = lees(mutatie.bestand)
        if mutatie.zoek not in origineel:
            print(f"OVERGESLAGEN  {mutatie.naam}")
            print(f"              de te vervangen tekst staat niet in {mutatie.bestand.name}")
            mislukt += 1
            continue

        schrijf(mutatie.bestand, origineel.replace(mutatie.zoek, mutatie.vervang, 1))
        try:
            groen, samenvatting = draai(mutatie.proeven, argumenten.pytest_arg)
        finally:
            schrijf(mutatie.bestand, origineel)

        if groen:
            print(f"BEWAAKT NIET  {mutatie.naam}")
            print(f"              proeven bleven groen: {samenvatting}")
            mislukt += 1
        else:
            print(f"GEVANGEN      {mutatie.naam}")
            print(f"              {samenvatting}")
        if mutatie.toelichting:
            print(f"              {mutatie.toelichting}")

    print()
    if mislukt:
        print(f"{mislukt} van de {len(MUTATIES)} mutaties werd niet gevangen.")
        return 1
    print(f"Alle {len(MUTATIES)} mutaties werden gevangen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Bewaker: klopt de verpakking van de integratie?

Manifest, HACS-bestand, vertalingen en services.yaml horen bij elkaar te passen.
Een ontbrekende vertaling levert in Home Assistant geen fout op, maar wel een
entiteit die "Pv Vermogen" heet in plaats van "PV vermogen", en dat merk je pas
op het scherm van een cursist.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

from kernlader import (  # noqa: E402
    APPLIANCES,
    DOMAIN,
    ENTITY_KEYS,
    KERNBESTANDEN,
    SCENARIOS,
    SERVICE_RESET,
    SERVICE_SET_SCENARIO,
    UPDATE_INTERVAL_SECONDS,
)

REPO = Path(__file__).resolve().parents[2]
COMPONENT = REPO / "custom_components" / DOMAIN
TALEN = ("nl", "en")


def lees_json(pad: Path) -> dict:
    return json.loads(pad.read_text(encoding="utf-8"))


def vertaling(taal: str) -> dict:
    return lees_json(COMPONENT / "translations" / f"{taal}.json")


# --- Verpakking --------------------------------------------------------------


def test_manifest_heeft_alles_wat_een_custom_integratie_nodig_heeft():
    manifest = lees_json(COMPONENT / "manifest.json")
    assert manifest["domain"] == DOMAIN
    assert manifest["config_flow"] is True
    assert manifest["version"], "HACS weigert een integratie zonder version"
    assert manifest["requirements"] == [], "de simulatie draait zonder externe pakketten"
    assert manifest["documentation"].startswith("http")


def test_hacs_bestand_is_geldig():
    hacs = lees_json(REPO / "hacs.json")
    assert hacs["name"]
    assert hacs["content_in_root"] is False
    assert hacs["homeassistant"]


def test_de_map_heet_precies_zoals_het_domein():
    assert COMPONENT.is_dir()
    assert COMPONENT.name == DOMAIN


def test_update_interval_valt_binnen_de_gevraagde_vijf_tot_tien_seconden():
    assert 5 <= UPDATE_INTERVAL_SECONDS <= 10


# --- Vertalingen -------------------------------------------------------------


@pytest.mark.parametrize("taal", TALEN)
def test_elke_entiteit_heeft_een_naam_in_beide_talen(taal: str):
    entiteiten = vertaling(taal)["entity"]
    for platform, sleutels in ENTITY_KEYS.items():
        aanwezig = set(entiteiten.get(platform, {}))
        ontbreekt = sorted(set(sleutels) - aanwezig)
        assert not ontbreekt, f"{taal}.json mist namen voor {platform}: {ontbreekt}"
        te_veel = sorted(aanwezig - set(sleutels))
        assert not te_veel, f"{taal}.json beschrijft niet-bestaande entiteiten: {te_veel}"


def test_beide_talen_hebben_dezelfde_sleutels():
    def sleutels(knoop, pad: str = "") -> set[str]:
        gevonden: set[str] = set()
        if isinstance(knoop, dict):
            for sleutel, waarde in knoop.items():
                gevonden.add(f"{pad}/{sleutel}")
                gevonden |= sleutels(waarde, f"{pad}/{sleutel}")
        return gevonden

    nl = sleutels(vertaling("nl"))
    en = sleutels(vertaling("en"))
    assert nl == en, f"verschil: {sorted(nl ^ en)}"


def test_strings_json_is_gelijk_aan_de_engelse_vertaling():
    assert lees_json(COMPONENT / "strings.json") == vertaling("en")


@pytest.mark.parametrize("taal", TALEN)
def test_elk_scenario_heeft_een_leesbare_naam(taal: str):
    opties = vertaling(taal)["selector"]["scenario"]["options"]
    assert set(opties) == set(SCENARIOS)
    for sleutel, tekst in opties.items():
        assert tekst.strip(), sleutel


@pytest.mark.parametrize("taal", TALEN)
def test_beide_services_zijn_vertaald(taal: str):
    services = vertaling(taal)["services"]
    assert set(services) == {SERVICE_SET_SCENARIO, SERVICE_RESET}
    for naam, blok in services.items():
        assert blok["name"] and blok["description"], naam


NEDERLANDSE_TEKSTEN = (
    COMPONENT / "translations" / "nl.json",
    COMPONENT / "services.yaml",
    REPO / "README.md",
    REPO / "dashboards" / "cursist-dashboard.yaml",
    REPO / "dashboards" / "docent-dashboard.yaml",
    REPO / "themes" / "domotitech.yaml",
)


@pytest.mark.parametrize("pad", NEDERLANDSE_TEKSTEN, ids=lambda pad: pad.name)
def test_nederlandse_teksten_bevatten_geen_gedachtestreepjes(pad: Path):
    """Huisstijl: geen gedachtestreepjes in tekst die een ander leest."""
    tekst = pad.read_text(encoding="utf-8")
    for teken in ("—", "–"):
        regels = [
            nummer
            for nummer, regel in enumerate(tekst.splitlines(), start=1)
            if teken in regel
        ]
        assert not regels, f"{pad.name} heeft een gedachtestreepje op regel {regels}"


# --- Services ----------------------------------------------------------------


def test_services_yaml_beschrijft_precies_de_bestaande_services():
    services = yaml.safe_load((COMPONENT / "services.yaml").read_text(encoding="utf-8"))
    assert set(services) == {SERVICE_SET_SCENARIO, SERVICE_RESET}
    for naam, blok in services.items():
        assert blok["name"], naam
        assert blok["description"], naam


def test_de_scenariokeuze_in_services_yaml_klopt_met_de_code():
    services = yaml.safe_load((COMPONENT / "services.yaml").read_text(encoding="utf-8"))
    opties = services[SERVICE_SET_SCENARIO]["fields"]["scenario"]["selector"]["select"]["options"]
    assert set(opties) == set(SCENARIOS)


# --- Apparaten ---------------------------------------------------------------


def test_de_drie_gevraagde_apparaten_staan_erin_met_hun_vermogen():
    assert set(APPLIANCES) == {"wasmachine", "boiler", "airco"}
    assert APPLIANCES["wasmachine"]["power_w"] == 2000.0
    assert APPLIANCES["boiler"]["power_w"] == 2500.0
    assert APPLIANCES["airco"]["power_w"] == 1200.0


def test_elk_apparaat_heeft_een_schakelaar_en_een_teller():
    for sleutel in APPLIANCES:
        assert sleutel in ENTITY_KEYS["switch"]
        assert f"{sleutel}_verbruik" in ENTITY_KEYS["sensor"]


# --- Naam naar entity_id -----------------------------------------------------


@pytest.mark.parametrize(
    ("naam", "verwacht"),
    [
        ("Virtueel EMS", "virtueel_ems"),
        ("Lokaal A", "lokaal_a"),
        ("Lokaal  A2", "lokaal_a2"),
        ("Praktijklokaal 3", "praktijklokaal_3"),
        ("EMS", "ems"),
        ("  Lokaal A  ", "lokaal_a"),
    ],
)
def test_de_naam_wordt_dezelfde_slug_als_in_de_entity_id(naam: str, verwacht: str):
    """De dashboards leunen hierop; tests/ha legt dit naast de slugify van HA."""
    from kernlader import slugify_naam

    assert slugify_naam(naam) == verwacht


def test_de_meegeleverde_dashboards_gebruiken_de_standaardnaam():
    from kernlader import DEFAULT_NAME, slugify_naam

    assert slugify_naam(DEFAULT_NAME) == "virtueel_ems"


# --- De rekenkern staat los van Home Assistant -------------------------------


@pytest.mark.parametrize("bestand", KERNBESTANDEN)
def test_de_rekenkern_noemt_home_assistant_nergens(bestand: str):
    """Anders is de kern niet meer los te draaien tegen een hele dag gegevens.

    De structurele bewaking zit in kernlader.py: die laadt deze bestanden zonder
    het Home Assistant-pakket eromheen, dus een import die er niet hoort laat
    alle kernproeven vallen op een machine zonder Home Assistant. Deze proef zegt
    er alleen nog bij wélk woord er dan te veel staat.
    """
    tekst = (COMPONENT / bestand).read_text(encoding="utf-8")
    regels = [
        f"{nummer}: {regel.strip()}"
        for nummer, regel in enumerate(tekst.splitlines(), start=1)
        if regel.lstrip().startswith(("import ", "from "))
        and ("homeassistant" in regel or "voluptuous" in regel)
    ]
    assert not regels, f"{bestand} hangt aan Home Assistant: {regels}"

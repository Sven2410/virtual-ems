"""Bewaker: verwijzen de dashboards naar entiteiten die echt bestaan?

Een dashboard dat naar een niet-bestaande entiteit wijst geeft geen foutmelding
en geen logregel. Het toont een grijze kaart met "Entity not available", en dat
merkt de docent pas midden in de les. Deze proef vangt dat af, en hij hangt aan
de proefronde en aan de bouwstap in CI, niet aan iemands geheugen.
"""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

from kernlader import (  # noqa: E402
    DOMAIN,
    SCENARIOS,
    SERVICE_HERSTEL_ZEKERING,
    SERVICE_RESET,
    SERVICE_SET_SCENARIO,
    entity_ids,
)

REPO = Path(__file__).resolve().parents[2]
DASHBOARDS = REPO / "dashboards"

#: De naam waar de meegeleverde dashboards van uitgaan.
SLUG = "virtueel_ems"

PLATFORMS = ("sensor.", "number.", "switch.")


def laad(naam: str) -> dict:
    with (DASHBOARDS / naam).open(encoding="utf-8") as bestand:
        return yaml.safe_load(bestand)


def verzamel_entiteiten(knoop, gevonden: set[str]) -> set[str]:
    """Haal elke entity_id uit een dashboardconfiguratie."""
    if isinstance(knoop, dict):
        for sleutel, waarde in knoop.items():
            if sleutel == "entity" and isinstance(waarde, str):
                gevonden.add(waarde)
            elif sleutel == "entities" and isinstance(waarde, list):
                for item in waarde:
                    if isinstance(item, str):
                        gevonden.add(item)
                    else:
                        verzamel_entiteiten(item, gevonden)
            else:
                verzamel_entiteiten(waarde, gevonden)
    elif isinstance(knoop, list):
        for item in knoop:
            verzamel_entiteiten(item, gevonden)
    return gevonden


def verzamel_acties(knoop, gevonden: list[dict]) -> list[dict]:
    """Haal elke serviceaanroep uit een dashboardconfiguratie."""
    if isinstance(knoop, dict):
        if "perform_action" in knoop:
            gevonden.append(knoop)
        if "service" in knoop and isinstance(knoop.get("service"), str):
            gevonden.append({"perform_action": knoop["service"], "data": knoop.get("data", {})})
        for waarde in knoop.values():
            verzamel_acties(waarde, gevonden)
    elif isinstance(knoop, list):
        for item in knoop:
            verzamel_acties(item, gevonden)
    return gevonden


@pytest.mark.parametrize("bestand", ["cursist-dashboard.yaml", "docent-dashboard.yaml"])
def test_dashboard_is_geldige_yaml_met_views(bestand: str):
    config = laad(bestand)
    assert isinstance(config, dict)
    assert config.get("views"), bestand


@pytest.mark.parametrize("bestand", ["cursist-dashboard.yaml", "docent-dashboard.yaml"])
def test_elke_entiteit_op_het_dashboard_bestaat_ook_echt(bestand: str):
    bekend = entity_ids(SLUG)
    gebruikt = verzamel_entiteiten(laad(bestand), set())
    van_ons = {e for e in gebruikt if e.startswith(PLATFORMS)}

    assert van_ons, f"{bestand} verwijst naar geen enkele entiteit van {DOMAIN}"
    onbekend = sorted(van_ons - bekend)
    assert not onbekend, f"{bestand} verwijst naar niet-bestaande entiteiten: {onbekend}"


@pytest.mark.parametrize("bestand", ["cursist-dashboard.yaml", "docent-dashboard.yaml"])
def test_dashboards_roepen_alleen_bestaande_services_aan(bestand: str):
    toegestaan = {
        f"{DOMAIN}.{SERVICE_SET_SCENARIO}",
        f"{DOMAIN}.{SERVICE_RESET}",
        f"{DOMAIN}.{SERVICE_HERSTEL_ZEKERING}",
    }
    for actie in verzamel_acties(laad(bestand), []):
        naam = actie["perform_action"]
        if not naam.startswith(f"{DOMAIN}."):
            continue
        assert naam in toegestaan, f"{bestand} roept onbekende service {naam} aan"
        if naam.endswith(SERVICE_SET_SCENARIO):
            scenario = (actie.get("data") or {}).get("scenario")
            assert scenario in SCENARIOS, f"{bestand} kent scenario {scenario} niet"


def test_alle_scenarios_staan_op_het_docentdashboard():
    """Een scenario dat nergens op een knop staat, gebruikt niemand."""
    acties = verzamel_acties(laad("docent-dashboard.yaml"), [])
    op_knoppen = {
        (actie.get("data") or {}).get("scenario")
        for actie in acties
        if actie["perform_action"] == f"{DOMAIN}.{SERVICE_SET_SCENARIO}"
    }
    assert set(SCENARIOS) <= op_knoppen


def test_cursistdashboard_staat_in_kiosk_mode():
    config = laad("cursist-dashboard.yaml")
    kiosk = config.get("kiosk_mode")
    assert kiosk, "zonder kiosk_mode-blok ziet een cursist de zijbalk"
    assert kiosk["non_admin_settings"]["kiosk"] is True


def test_docentdashboard_staat_juist_niet_in_kiosk_mode():
    assert "kiosk_mode" not in laad("docent-dashboard.yaml")


def test_cursistdashboard_toont_geen_diagnose_entiteiten():
    """De cursist bedient het systeem; de tijdversnelling is voor de docent."""
    gebruikt = verzamel_entiteiten(laad("cursist-dashboard.yaml"), set())
    assert f"number.{SLUG}_tijdversnelling" not in gebruikt
    assert f"sensor.{SLUG}_simulatietijd" not in gebruikt

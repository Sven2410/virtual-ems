"""Proeven op de bedrading: entiteiten, bediening en services in echte HA."""

from __future__ import annotations

import pytest

from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.virtual_ems.catalog import entity_ids
from custom_components.virtual_ems.const import (
    ATTR_ONLY_COUNTERS,
    ATTR_SCENARIO,
    CONF_BATTERY_KWH,
    CONF_EV_MAX_KW,
    CONF_NAME,
    CONF_PV_PEAK_KWP,
    DOMAIN,
    SERVICE_RESET,
    SERVICE_SET_SCENARIO,
)
from custom_components.virtual_ems.scenarios import SCENARIOS

SLUG = "lokaal_a"
INVOER = {
    CONF_NAME: "Lokaal A",
    CONF_PV_PEAK_KWP: 4.0,
    CONF_BATTERY_KWH: 10.0,
    CONF_EV_MAX_KW: 11.0,
}


@pytest.fixture
async def opgezet(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, data=INVOER, unique_id=SLUG)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_alle_entiteiten_uit_de_catalogus_bestaan_ook_echt(
    hass: HomeAssistant, opgezet: MockConfigEntry
):
    """De catalogus is de bron voor de dashboardbewaker; hij moet dus kloppen."""
    verwacht = entity_ids(SLUG)
    aanwezig = {
        entity_id
        for entity_id in hass.states.async_entity_ids()
        if entity_id.split(".", 1)[1].startswith(f"{SLUG}_")
    }
    assert aanwezig == verwacht


async def test_alles_hangt_onder_een_apparaat(
    hass: HomeAssistant, opgezet: MockConfigEntry
):
    from homeassistant.helpers import device_registry as dr, entity_registry as er

    apparaten = dr.async_get(hass)
    entiteiten = er.async_get(hass)

    van_ons = er.async_entries_for_config_entry(entiteiten, opgezet.entry_id)
    assert van_ons

    # Alles hoort onder één apparaat te hangen, zodat de installatie in Home
    # Assistant als één geheel te vinden is.
    apparaat_ids = {vermelding.device_id for vermelding in van_ons}
    assert len(apparaat_ids) == 1

    apparaat = apparaten.async_get(apparaat_ids.pop())
    assert apparaat is not None
    assert apparaat.name == "Lokaal A"
    assert (DOMAIN, opgezet.entry_id) in apparaat.identifiers

    for vermelding in van_ons:
        assert vermelding.unique_id.startswith(opgezet.entry_id)


async def test_de_netsensor_is_de_optelsom_van_de_andere_sensoren(
    hass: HomeAssistant, opgezet: MockConfigEntry
):
    def waarde(sleutel: str) -> float:
        return float(hass.states.get(f"sensor.{SLUG}_{sleutel}").state)

    verwacht = (
        waarde("huishoudelijk_verbruik")
        + waarde("laadpaal_vermogen")
        + waarde("batterij_vermogen_actueel")
        - waarde("pv_vermogen")
    )
    assert waarde("net_vermogen") == pytest.approx(verwacht, abs=1e-6)


async def test_een_apparaat_aanzetten_verhoogt_het_verbruik_meteen(
    hass: HomeAssistant, opgezet: MockConfigEntry
):
    voor = float(hass.states.get(f"sensor.{SLUG}_huishoudelijk_verbruik").state)

    await hass.services.async_call(
        "switch",
        "turn_on",
        {ATTR_ENTITY_ID: f"switch.{SLUG}_boiler"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert hass.states.get(f"switch.{SLUG}_boiler").state == STATE_ON
    na = float(hass.states.get(f"sensor.{SLUG}_huishoudelijk_verbruik").state)
    assert na - voor == pytest.approx(2500.0, abs=50.0)


async def test_de_schuif_voor_het_batterijvermogen_kent_de_c_rate(
    hass: HomeAssistant, opgezet: MockConfigEntry
):
    toestand = hass.states.get(f"number.{SLUG}_batterij_vermogen")
    # 10 kWh bij 0,5 C geeft 5000 W in beide richtingen.
    assert float(toestand.attributes["min"]) == -5000.0
    assert float(toestand.attributes["max"]) == 5000.0


async def test_de_laadpaalschuif_is_begrensd_op_de_ingestelde_maximum(
    hass: HomeAssistant, opgezet: MockConfigEntry
):
    toestand = hass.states.get(f"number.{SLUG}_laadpaal_vermogen")
    assert float(toestand.attributes["max"]) == 11000.0


async def test_bewolking_verzetten_verlaagt_de_pv_direct(
    hass: HomeAssistant, opgezet: MockConfigEntry
):
    coordinator = opgezet.runtime_data
    # Zet de simulatieklok op klaarlichte dag, anders is er niets te verlagen.
    await coordinator.async_apply_scenario("zonnige_dag")
    await hass.async_block_till_done()

    voor = float(hass.states.get(f"sensor.{SLUG}_pv_vermogen").state)
    assert voor > 0

    await hass.services.async_call(
        "number",
        "set_value",
        {ATTR_ENTITY_ID: f"number.{SLUG}_pv_bewolking", "value": 100},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert float(hass.states.get(f"sensor.{SLUG}_pv_vermogen").state) == 0.0


async def test_de_laadpaal_loopt_op_in_plaats_van_te_springen(
    hass: HomeAssistant, opgezet: MockConfigEntry
):
    await hass.services.async_call(
        "switch",
        "turn_on",
        {ATTR_ENTITY_ID: f"switch.{SLUG}_laadpaal_actief"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert hass.states.get(f"switch.{SLUG}_laadpaal_actief").state == STATE_ON
    # Direct na het inschakelen is er nauwelijks tijd verstreken, dus het
    # vermogen staat nog ver onder de instelling.
    direct = float(hass.states.get(f"sensor.{SLUG}_laadpaal_vermogen").state)
    assert direct < 3700.0


async def test_de_service_zet_een_scenario_klaar(
    hass: HomeAssistant, opgezet: MockConfigEntry
):
    await hass.services.async_call(
        DOMAIN,
        SERVICE_SET_SCENARIO,
        {ATTR_SCENARIO: "piekbelasting_avond"},
        blocking=True,
    )
    await hass.async_block_till_done()

    scenario = SCENARIOS["piekbelasting_avond"]
    assert hass.states.get(f"switch.{SLUG}_wasmachine").state == STATE_ON
    assert hass.states.get(f"switch.{SLUG}_boiler").state == STATE_ON
    assert hass.states.get(f"switch.{SLUG}_airco").state == STATE_OFF
    assert hass.states.get(f"switch.{SLUG}_laadpaal_actief").state == STATE_ON
    assert float(hass.states.get(f"sensor.{SLUG}_batterij_soc").state) == pytest.approx(
        scenario.soc_pct, abs=0.5
    )


async def test_een_onbekend_scenario_wordt_geweigerd(
    hass: HomeAssistant, opgezet: MockConfigEntry
):
    import voluptuous as vol

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN, SERVICE_SET_SCENARIO, {ATTR_SCENARIO: "onzin"}, blocking=True
        )


async def test_de_service_zet_de_tellers_terug(
    hass: HomeAssistant, opgezet: MockConfigEntry
):
    coordinator = opgezet.runtime_data
    coordinator.simulation.totals.pv_kwh = 12.5
    coordinator.simulation.totals.grid_import_kwh = 3.25
    coordinator.simulation.setpoints.cloud_pct = 80.0
    coordinator.simulation.set_soc_pct(12.0)

    await hass.services.async_call(DOMAIN, SERVICE_RESET, {}, blocking=True)
    await hass.async_block_till_done()

    # Na het terugzetten rekent de simulatie meteen een stap door, dus staat er
    # al een fractie van een wattuur op de teller. Precies nul zou betekenen dat
    # de simulatie stilstaat.
    assert float(hass.states.get(f"sensor.{SLUG}_pv_opbrengst").state) < 0.001
    assert float(hass.states.get(f"sensor.{SLUG}_net_afname").state) < 0.001
    assert float(hass.states.get(f"sensor.{SLUG}_batterij_soc").state) == pytest.approx(
        50.0, abs=0.5
    )
    assert float(hass.states.get(f"number.{SLUG}_pv_bewolking").state) == 0.0


async def test_terugzetten_met_alleen_tellers_laat_de_bediening_staan(
    hass: HomeAssistant, opgezet: MockConfigEntry
):
    await hass.services.async_call(
        "number",
        "set_value",
        {ATTR_ENTITY_ID: f"number.{SLUG}_pv_bewolking", "value": 60},
        blocking=True,
    )
    await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN, SERVICE_RESET, {ATTR_ONLY_COUNTERS: True}, blocking=True
    )
    await hass.async_block_till_done()

    assert float(hass.states.get(f"number.{SLUG}_pv_bewolking").state) == 60.0
    assert float(hass.states.get(f"sensor.{SLUG}_pv_opbrengst").state) < 0.001


async def test_de_energiesensoren_hebben_de_klassen_die_het_energiedashboard_eist(
    hass: HomeAssistant, opgezet: MockConfigEntry
):
    verplicht = (
        "pv_opbrengst",
        "batterij_geladen",
        "batterij_ontladen",
        "laadpaal_verbruik",
        "verbruik_totaal",
        "net_afname",
        "net_teruglevering",
        "wasmachine_verbruik",
        "boiler_verbruik",
        "airco_verbruik",
    )
    for sleutel in verplicht:
        toestand = hass.states.get(f"sensor.{SLUG}_{sleutel}")
        assert toestand is not None, sleutel
        assert toestand.attributes["device_class"] == "energy", sleutel
        assert toestand.attributes["state_class"] == "total_increasing", sleutel
        assert toestand.attributes["unit_of_measurement"] == "kWh", sleutel


async def test_de_tellers_overleven_een_herstart(
    hass: HomeAssistant, opgezet: MockConfigEntry
):
    coordinator = opgezet.runtime_data
    coordinator.simulation.totals.pv_kwh = 7.5
    coordinator.simulation.set_soc_pct(83.0)
    await coordinator.async_save()

    await hass.config_entries.async_reload(opgezet.entry_id)
    await hass.async_block_till_done()

    assert float(hass.states.get(f"sensor.{SLUG}_pv_opbrengst").state) == pytest.approx(
        7.5, abs=0.01
    )
    assert float(hass.states.get(f"sensor.{SLUG}_batterij_soc").state) == pytest.approx(
        83.0, abs=0.5
    )


async def test_de_services_verdwijnen_als_de_laatste_installatie_weggaat(
    hass: HomeAssistant, opgezet: MockConfigEntry
):
    assert hass.services.has_service(DOMAIN, SERVICE_SET_SCENARIO)

    assert await hass.config_entries.async_unload(opgezet.entry_id)
    await hass.async_block_till_done()

    assert not hass.services.has_service(DOMAIN, SERVICE_SET_SCENARIO)
    assert not hass.services.has_service(DOMAIN, SERVICE_RESET)


async def test_onze_slug_is_dezelfde_als_die_van_home_assistant(hass: HomeAssistant):
    """catalog.slugify_naam wordt gebruikt door de dashboardbewaker en het
    omzetscript. Wijkt hij af van Home Assistant, dan wijzen de dashboards naar
    entiteiten die niet bestaan."""
    from homeassistant.util import slugify

    from custom_components.virtual_ems.catalog import slugify_naam

    for naam in ("Virtueel EMS", "Lokaal A", "Lokaal  A2", "Praktijklokaal 3", "EMS"):
        assert slugify_naam(naam) == slugify(naam), naam

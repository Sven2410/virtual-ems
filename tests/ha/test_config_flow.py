"""Proeven op de config flow, met een echte Home Assistant in het geheugen."""

from __future__ import annotations

import pytest

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.virtual_ems.const import (
    CONF_ANNUAL_KWH,
    CONF_BATTERY_KWH,
    CONF_CONNECTION_A,
    CONF_EV_MAX_KW,
    CONF_NAME,
    CONF_PHASES,
    CONF_PV_PEAK_KWP,
    CONF_START_HOUR,
    DOMAIN,
)

#: Wat de optiesdialoog minimaal terugkrijgt.
OPTIES = {
    CONF_PV_PEAK_KWP: 4.0,
    CONF_BATTERY_KWH: 10.0,
    CONF_EV_MAX_KW: 11.0,
    CONF_ANNUAL_KWH: 2900.0,
    CONF_CONNECTION_A: 25.0,
    CONF_PHASES: "3",
}

INVOER = {
    CONF_NAME: "Lokaal A",
    CONF_PV_PEAK_KWP: 4.0,
    CONF_BATTERY_KWH: 10.0,
    CONF_EV_MAX_KW: 11.0,
}


async def test_installeren_via_de_gebruikersdialoog(hass: HomeAssistant):
    resultaat = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert resultaat["type"] is FlowResultType.FORM
    assert resultaat["step_id"] == "user"

    resultaat = await hass.config_entries.flow.async_configure(
        resultaat["flow_id"], INVOER
    )
    await hass.async_block_till_done()

    assert resultaat["type"] is FlowResultType.CREATE_ENTRY
    assert resultaat["title"] == "Lokaal A"
    assert resultaat["data"] == {
        CONF_NAME: "Lokaal A",
        CONF_PV_PEAK_KWP: 4.0,
        CONF_BATTERY_KWH: 10.0,
        CONF_EV_MAX_KW: 11.0,
    }


async def test_een_naam_zonder_letters_wordt_geweigerd(hass: HomeAssistant):
    resultaat = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    resultaat = await hass.config_entries.flow.async_configure(
        resultaat["flow_id"], {**INVOER, CONF_NAME: "   "}
    )

    assert resultaat["type"] is FlowResultType.FORM
    assert resultaat["errors"] == {CONF_NAME: "ongeldige_naam"}


async def test_dezelfde_naam_twee_keer_kan_niet(hass: HomeAssistant):
    """Twee installaties met dezelfde naam zouden dezelfde entity_id's krijgen."""
    entry = MockConfigEntry(domain=DOMAIN, data=INVOER, unique_id="lokaal_a")
    entry.add_to_hass(hass)

    resultaat = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    resultaat = await hass.config_entries.flow.async_configure(resultaat["flow_id"], INVOER)

    assert resultaat["type"] is FlowResultType.ABORT
    assert resultaat["reason"] == "already_configured"


async def test_opties_aanpassen_zonder_opnieuw_te_installeren(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, data=INVOER, unique_id="lokaal_a")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    resultaat = await hass.config_entries.options.async_init(entry.entry_id)
    assert resultaat["type"] is FlowResultType.FORM
    assert resultaat["step_id"] == "init"

    resultaat = await hass.config_entries.options.async_configure(
        resultaat["flow_id"],
        {
            **OPTIES,
            CONF_PV_PEAK_KWP: 8.0,
            CONF_BATTERY_KWH: 20.0,
            CONF_EV_MAX_KW: 22.0,
            CONF_ANNUAL_KWH: 3500.0,
            CONF_CONNECTION_A: 35.0,
            CONF_PHASES: "1",
            CONF_START_HOUR: 11.0,
        },
    )
    await hass.async_block_till_done()

    assert resultaat["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_PV_PEAK_KWP] == 8.0
    assert entry.options[CONF_START_HOUR] == 11.0

    # De integratie hoort zichzelf herladen te hebben met de nieuwe grootte.
    coordinator = entry.runtime_data
    assert coordinator.simulation.config.pv_peak_kwp == 8.0
    assert coordinator.simulation.config.battery_capacity_kwh == 20.0
    assert coordinator.simulation.config.ev_max_power_w == 22000.0
    # Eén fase van 35 A bij 230 V is 8050 W.
    assert coordinator.simulation.config.connection_power_w == pytest.approx(8050.0)


async def test_starttijd_mag_leeg_blijven(hass: HomeAssistant):
    entry = MockConfigEntry(domain=DOMAIN, data=INVOER, unique_id="lokaal_a")
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    resultaat = await hass.config_entries.options.async_init(entry.entry_id)
    resultaat = await hass.config_entries.options.async_configure(
        resultaat["flow_id"],
        OPTIES,
    )
    await hass.async_block_till_done()

    assert CONF_START_HOUR not in entry.options

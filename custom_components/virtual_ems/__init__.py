"""De virtual_ems integratie: een compleet gesimuleerd thuisenergiesysteem."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import (
    ATTR_ONLY_COUNTERS,
    ATTR_SCENARIO,
    DOMAIN,
    PLATFORMS,
    SERVICE_RESET,
    SERVICE_SET_SCENARIO,
)
from .coordinator import VirtualEmsCoordinator
from .scenarios import SCENARIOS

_LOGGER = logging.getLogger(__name__)

SET_SCENARIO_SCHEMA = vol.Schema(
    {vol.Required(ATTR_SCENARIO): vol.In(sorted(SCENARIOS))}
)

RESET_SCHEMA = vol.Schema(
    {vol.Optional(ATTR_ONLY_COUNTERS, default=False): cv.boolean}
)


def _loaded_coordinators(hass: HomeAssistant) -> list[VirtualEmsCoordinator]:
    """Alle draaiende installaties. In een klaslokaal is dat er meestal één."""
    coordinators: list[VirtualEmsCoordinator] = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is ConfigEntryState.LOADED and hasattr(entry, "runtime_data"):
            coordinators.append(entry.runtime_data)
    return coordinators


def _register_services(hass: HomeAssistant) -> None:
    """Registreer de services één keer voor het hele domein."""

    async def handle_set_scenario(call: ServiceCall) -> None:
        scenario = call.data[ATTR_SCENARIO]
        for coordinator in _loaded_coordinators(hass):
            await coordinator.async_apply_scenario(scenario)

    async def handle_reset(call: ServiceCall) -> None:
        only_counters = bool(call.data.get(ATTR_ONLY_COUNTERS, False))
        for coordinator in _loaded_coordinators(hass):
            await coordinator.async_reset(only_counters=only_counters)

    if not hass.services.has_service(DOMAIN, SERVICE_SET_SCENARIO):
        hass.services.async_register(
            DOMAIN, SERVICE_SET_SCENARIO, handle_set_scenario, schema=SET_SCENARIO_SCHEMA
        )
    if not hass.services.has_service(DOMAIN, SERVICE_RESET):
        hass.services.async_register(DOMAIN, SERVICE_RESET, handle_reset, schema=RESET_SCHEMA)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Start één gesimuleerde installatie."""
    coordinator = VirtualEmsCoordinator(hass, entry)
    await coordinator.async_prepare()
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _register_services(hass)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Herlaad zodra de docent de capaciteiten in de opties aanpast."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Stop een installatie en bewaar de tellerstanden."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        coordinator: VirtualEmsCoordinator = entry.runtime_data
        await coordinator.async_shutdown()

        # De services blijven bestaan zolang er nog een installatie draait.
        if not [
            other
            for other in hass.config_entries.async_entries(DOMAIN)
            if other.entry_id != entry.entry_id and other.state is ConfigEntryState.LOADED
        ]:
            hass.services.async_remove(DOMAIN, SERVICE_SET_SCENARIO)
            hass.services.async_remove(DOMAIN, SERVICE_RESET)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Ruim de opgeslagen tellerstanden op als de integratie verwijderd wordt."""
    from homeassistant.helpers.storage import Store

    from .const import STORAGE_KEY_TEMPLATE, STORAGE_VERSION

    store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY_TEMPLATE.format(entry_id=entry.entry_id))
    await store.async_remove()

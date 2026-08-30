"""De bedrading tussen de rekenkern en Home Assistant.

Hier zit alles wat Home Assistant kent: de klok, de opslag, de update-lus. De
som zelf staat in simulation.py en weet van dit bestand niets af.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    APPLIANCES,
    CONF_ANNUAL_KWH,
    CONF_BATTERY_KWH,
    CONF_EV_MAX_KW,
    CONF_NAME,
    CONF_PV_PEAK_KWP,
    CONF_START_HOUR,
    DEFAULT_ANNUAL_KWH,
    DEFAULT_BATTERY_KWH,
    DEFAULT_EV_MAX_KW,
    DEFAULT_NAME,
    DEFAULT_PV_PEAK_KWP,
    DOMAIN,
    HOUSEHOLD_PROFILE,
    MANUFACTURER,
    MODEL,
    STORAGE_KEY_TEMPLATE,
    STORAGE_VERSION,
    UPDATE_INTERVAL_SECONDS,
)
from .scenarios import SCENARIOS, apply_scenario
from .simulation import PlantConfig, Simulation, Snapshot

_LOGGER = logging.getLogger(__name__)

#: Hoeveel updates er tussen twee schrijfacties naar de opslag zitten. Bij vijf
#: seconden per update is dat ongeveer één minuut.
SAVE_EVERY_N_UPDATES = 12


def plant_config_from_entry(hass: HomeAssistant, entry: ConfigEntry) -> PlantConfig:
    """Bouw de rekenkernconfiguratie uit de config entry en de opties."""
    merged: dict[str, Any] = {**entry.data, **entry.options}
    return PlantConfig(
        pv_peak_kwp=float(merged.get(CONF_PV_PEAK_KWP, DEFAULT_PV_PEAK_KWP)),
        battery_capacity_kwh=float(merged.get(CONF_BATTERY_KWH, DEFAULT_BATTERY_KWH)),
        ev_max_power_w=float(merged.get(CONF_EV_MAX_KW, DEFAULT_EV_MAX_KW)) * 1000.0,
        annual_consumption_kwh=float(merged.get(CONF_ANNUAL_KWH, DEFAULT_ANNUAL_KWH)),
        latitude=float(hass.config.latitude),
        longitude=float(hass.config.longitude),
        household_profile=HOUSEHOLD_PROFILE,
        appliances=tuple((key, float(spec["power_w"])) for key, spec in APPLIANCES.items()),
    )


class VirtualEmsCoordinator(DataUpdateCoordinator[Snapshot]):
    """Draait de simulatie en deelt het resultaat met alle entiteiten."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            # De config entry hoort er expliciet bij: Home Assistant leidt hem
            # niet meer af uit een ContextVar en gooit anders bij het opzetten.
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self.entry = entry
        self.installation_name: str = str(entry.data.get(CONF_NAME, DEFAULT_NAME))
        self.simulation = Simulation(plant_config_from_entry(hass, entry))
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, STORAGE_KEY_TEMPLATE.format(entry_id=entry.entry_id)
        )
        self._last_monotonic: float | None = None
        self._sim_now: datetime = dt_util.now()
        self._updates_since_save = 0
        self._unsub_stop = None

    # -- opstarten en opruimen ----------------------------------------------

    async def async_prepare(self) -> None:
        """Lees de opgeslagen toestand terug en zet de simulatieklok."""
        stored = await self._store.async_load()
        if stored:
            self.simulation.restore(stored.get("simulation", {}))
            saved_clock = stored.get("sim_now")
            if saved_clock:
                parsed = dt_util.parse_datetime(saved_clock)
                if parsed is not None:
                    self._sim_now = dt_util.as_local(parsed)

        start_hour = {**self.entry.data, **self.entry.options}.get(CONF_START_HOUR)
        if start_hour is not None and not stored:
            self._sim_now = self._today_at(float(start_hour))

        self._unsub_stop = self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, self._async_handle_stop
        )

    @callback
    def _today_at(self, hour: float) -> datetime:
        """Vandaag op het opgegeven uur, in de tijdzone van deze installatie."""
        now = dt_util.now()
        whole = int(hour) % 24
        minutes = int(round((hour - int(hour)) * 60)) % 60
        return now.replace(hour=whole, minute=minutes, second=0, microsecond=0)

    async def _async_handle_stop(self, _event: Any) -> None:
        await self.async_save()

    async def async_shutdown(self) -> None:
        if self._unsub_stop is not None:
            self._unsub_stop()
            self._unsub_stop = None
        await self.async_save()
        await super().async_shutdown()

    async def async_save(self) -> None:
        """Schrijf de toestand weg zodat een herstart de tellers niet wist."""
        await self._store.async_save(
            {
                "simulation": self.simulation.as_dict(),
                "sim_now": self._sim_now.isoformat(),
            }
        )
        self._updates_since_save = 0

    async def async_remove_storage(self) -> None:
        await self._store.async_remove()

    # -- de update-lus -------------------------------------------------------

    async def _async_update_data(self) -> Snapshot:
        now = time.monotonic()
        if self._last_monotonic is None:
            elapsed_real = 0.0
        else:
            elapsed_real = max(0.0, now - self._last_monotonic)
        self._last_monotonic = now

        factor = max(1.0, float(self.simulation.setpoints.time_factor))
        elapsed_sim = elapsed_real * factor
        self._sim_now = self._sim_now + timedelta(seconds=elapsed_sim)

        snapshot = self.simulation.step(self._sim_now, elapsed_sim)

        self._updates_since_save += 1
        if self._updates_since_save >= SAVE_EVERY_N_UPDATES:
            await self.async_save()

        return snapshot

    async def async_apply_and_refresh(self) -> None:
        """Reken meteen door, zodat het dashboard direct reageert."""
        await self.async_refresh()

    # -- bediening -----------------------------------------------------------

    async def async_set_cloud(self, value: float) -> None:
        self.simulation.setpoints.cloud_pct = max(0.0, min(100.0, value))
        await self.async_apply_and_refresh()

    async def async_set_battery_setpoint(self, value: float) -> None:
        limit = self.simulation.config.battery_max_power_w
        self.simulation.setpoints.battery_setpoint_w = max(-limit, min(limit, value))
        await self.async_apply_and_refresh()

    async def async_set_soc_min(self, value: float) -> None:
        self.simulation.setpoints.soc_min_pct = max(0.0, min(100.0, value))
        await self.async_apply_and_refresh()

    async def async_set_soc_max(self, value: float) -> None:
        self.simulation.setpoints.soc_max_pct = max(0.0, min(100.0, value))
        await self.async_apply_and_refresh()

    async def async_set_ev_power(self, value: float) -> None:
        limit = self.simulation.config.ev_max_power_w
        self.simulation.setpoints.ev_setpoint_w = max(0.0, min(limit, value))
        await self.async_apply_and_refresh()

    async def async_set_ev_enabled(self, enabled: bool) -> None:
        self.simulation.setpoints.ev_enabled = enabled
        await self.async_apply_and_refresh()

    async def async_set_time_factor(self, value: float) -> None:
        self.simulation.setpoints.time_factor = max(1.0, value)
        await self.async_apply_and_refresh()

    async def async_set_appliance(self, key: str, enabled: bool) -> None:
        self.simulation.setpoints.appliances[key] = enabled
        await self.async_apply_and_refresh()

    # -- services ------------------------------------------------------------

    async def async_apply_scenario(self, scenario_key: str) -> None:
        scenario = SCENARIOS[scenario_key]
        apply_scenario(self.simulation, scenario)
        if scenario.start_hour is not None:
            self._sim_now = self._today_at(scenario.start_hour)
        await self.async_save()
        await self.async_apply_and_refresh()

    async def async_reset(self, *, only_counters: bool = False) -> None:
        self.simulation.reset(only_counters=only_counters)
        start_hour = {**self.entry.data, **self.entry.options}.get(CONF_START_HOUR)
        if start_hour is not None:
            self._sim_now = self._today_at(float(start_hour))
        else:
            self._sim_now = dt_util.now()
        await self.async_save()
        await self.async_apply_and_refresh()

    # -- apparaat ------------------------------------------------------------

    @property
    def device_info(self) -> DeviceInfo:
        cfg = self.simulation.config
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name=self.installation_name,
            manufacturer=MANUFACTURER,
            model=MODEL,
            configuration_url=None,
            sw_version=None,
            hw_version=(
                f"{cfg.pv_peak_kwp:.1f} kWp PV, "
                f"{cfg.battery_capacity_kwh:.1f} kWh batterij, "
                f"{cfg.ev_max_power_w / 1000:.1f} kW laadpaal"
            ),
        )

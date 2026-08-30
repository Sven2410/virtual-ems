"""Sensoren van het virtuele EMS."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    ENTITY_ID_FORMAT,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    EntityCategory,
    UnitOfEnergy,
    UnitOfPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import APPLIANCES
from .coordinator import VirtualEmsCoordinator
from .entity import VirtualEmsEntity
from .simulation import Snapshot


@dataclass(frozen=True, kw_only=True)
class VirtualEmsSensorDescription(SensorEntityDescription):
    """Sensorbeschrijving met de som die de waarde levert."""

    value_fn: Callable[[Snapshot], float | datetime | None]


def _power(key: str, icon: str, value_fn: Callable[[Snapshot], float]) -> VirtualEmsSensorDescription:
    return VirtualEmsSensorDescription(
        key=key,
        icon=icon,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=0,
        value_fn=value_fn,
    )


def _energy(key: str, icon: str, value_fn: Callable[[Snapshot], float]) -> VirtualEmsSensorDescription:
    return VirtualEmsSensorDescription(
        key=key,
        icon=icon,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=3,
        value_fn=value_fn,
    )


SENSORS: tuple[VirtualEmsSensorDescription, ...] = (
    # PV
    _power("pv_vermogen", "mdi:solar-power", lambda s: s.pv_power_w),
    _energy("pv_opbrengst", "mdi:solar-power-variant", lambda s: s.totals.pv_kwh),
    # Batterij
    VirtualEmsSensorDescription(
        key="batterij_soc",
        icon="mdi:battery-charging-60",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
        value_fn=lambda s: s.battery_soc_pct,
    ),
    _power("batterij_vermogen_actueel", "mdi:home-battery", lambda s: s.battery_power_w),
    VirtualEmsSensorDescription(
        key="batterij_inhoud",
        icon="mdi:battery",
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        suggested_display_precision=2,
        value_fn=lambda s: s.battery_energy_kwh,
    ),
    _energy("batterij_geladen", "mdi:battery-plus", lambda s: s.totals.battery_charged_kwh),
    _energy("batterij_ontladen", "mdi:battery-minus", lambda s: s.totals.battery_discharged_kwh),
    # Laadpaal
    _power("laadpaal_vermogen", "mdi:ev-station", lambda s: s.ev_power_w),
    _energy("laadpaal_verbruik", "mdi:ev-plug-type2", lambda s: s.totals.ev_kwh),
    # Huishouden
    _power("huishoudelijk_verbruik", "mdi:home-lightning-bolt", lambda s: s.household_power_w),
    _energy("verbruik_totaal", "mdi:counter", lambda s: s.totals.household_kwh),
    # Netaansluiting
    _power("net_vermogen", "mdi:transmission-tower", lambda s: s.grid_power_w),
    _energy("net_afname", "mdi:transmission-tower-export", lambda s: s.totals.grid_import_kwh),
    _energy("net_teruglevering", "mdi:transmission-tower-import", lambda s: s.totals.grid_export_kwh),
    # Diagnose
    VirtualEmsSensorDescription(
        key="zonnehoogte",
        icon="mdi:weather-sunny",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=DEGREE,
        suggested_display_precision=1,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.solar_elevation_deg,
    ),
    VirtualEmsSensorDescription(
        key="simulatietijd",
        icon="mdi:clock-fast",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda s: s.moment,
    ),
)


def _appliance_sensors() -> tuple[VirtualEmsSensorDescription, ...]:
    """Een kWh-teller per virtueel apparaat, voor de sectie Apparaten."""

    def make(key: str, icon: str) -> VirtualEmsSensorDescription:
        return _energy(f"{key}_verbruik", icon, lambda s, k=key: s.totals.appliance_kwh.get(k, 0.0))

    return tuple(make(key, str(spec["icon"])) for key, spec in APPLIANCES.items())


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Zet de sensoren klaar."""
    coordinator: VirtualEmsCoordinator = entry.runtime_data
    descriptions = SENSORS + _appliance_sensors()
    async_add_entities(VirtualEmsSensor(coordinator, description) for description in descriptions)


class VirtualEmsSensor(VirtualEmsEntity, SensorEntity):
    """Eén afgelezen waarde uit de simulatie."""

    entity_description: VirtualEmsSensorDescription

    def __init__(
        self,
        coordinator: VirtualEmsCoordinator,
        description: VirtualEmsSensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key, ENTITY_ID_FORMAT)
        self.entity_description = description

    @property
    def native_value(self) -> float | datetime | None:
        snapshot = self.coordinator.data
        if snapshot is None:
            return None
        return self.entity_description.value_fn(snapshot)

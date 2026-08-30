"""Instelbare waarden: dit is wat een cursist zelf verzet."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.number import (
    ENTITY_ID_FORMAT,
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import VirtualEmsCoordinator
from .entity import VirtualEmsEntity
from .simulation import Setpoints


@dataclass(frozen=True, kw_only=True)
class VirtualEmsNumberDescription(NumberEntityDescription):
    """Beschrijving van een instelbare waarde."""

    value_fn: Callable[[Setpoints], float]
    set_fn: Callable[[VirtualEmsCoordinator, float], Awaitable[None]]
    #: Grenzen die van de installatiegrootte afhangen worden hiermee bepaald.
    limits_fn: Callable[[VirtualEmsCoordinator], tuple[float, float]] | None = None


NUMBERS: tuple[VirtualEmsNumberDescription, ...] = (
    VirtualEmsNumberDescription(
        key="pv_bewolking",
        icon="mdi:weather-cloudy",
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.SLIDER,
        value_fn=lambda s: s.cloud_pct,
        set_fn=lambda c, v: c.async_set_cloud(v),
    ),
    VirtualEmsNumberDescription(
        key="batterij_vermogen",
        icon="mdi:home-battery-outline",
        device_class=NumberDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        native_step=100,
        mode=NumberMode.SLIDER,
        native_min_value=-5000,
        native_max_value=5000,
        value_fn=lambda s: s.battery_setpoint_w,
        set_fn=lambda c, v: c.async_set_battery_setpoint(v),
        limits_fn=lambda c: (
            -c.simulation.config.battery_max_power_w,
            c.simulation.config.battery_max_power_w,
        ),
    ),
    VirtualEmsNumberDescription(
        key="batterij_min_soc",
        icon="mdi:battery-alert-variant-outline",
        native_min_value=0,
        native_max_value=100,
        native_step=5,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.SLIDER,
        value_fn=lambda s: s.soc_min_pct,
        set_fn=lambda c, v: c.async_set_soc_min(v),
    ),
    VirtualEmsNumberDescription(
        key="batterij_max_soc",
        icon="mdi:battery-charging-high",
        native_min_value=0,
        native_max_value=100,
        native_step=5,
        native_unit_of_measurement=PERCENTAGE,
        mode=NumberMode.SLIDER,
        value_fn=lambda s: s.soc_max_pct,
        set_fn=lambda c, v: c.async_set_soc_max(v),
    ),
    VirtualEmsNumberDescription(
        key="laadpaal_vermogen",
        icon="mdi:ev-station",
        device_class=NumberDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        native_min_value=0,
        native_max_value=11000,
        native_step=100,
        mode=NumberMode.SLIDER,
        value_fn=lambda s: s.ev_setpoint_w,
        set_fn=lambda c, v: c.async_set_ev_power(v),
        limits_fn=lambda c: (0.0, c.simulation.config.ev_max_power_w),
    ),
    VirtualEmsNumberDescription(
        key="piekgrens",
        icon="mdi:chart-timeline-variant",
        device_class=NumberDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        native_min_value=0,
        native_max_value=17250,
        native_step=250,
        mode=NumberMode.SLIDER,
        value_fn=lambda s: s.peak_limit_w,
        set_fn=lambda c, v: c.async_set_peak_limit(v),
        limits_fn=lambda c: (0.0, c.simulation.config.connection_power_w),
    ),
    VirtualEmsNumberDescription(
        key="tijdversnelling",
        icon="mdi:clock-fast",
        native_min_value=1,
        native_max_value=60,
        native_step=1,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
        value_fn=lambda s: s.time_factor,
        set_fn=lambda c, v: c.async_set_time_factor(v),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Zet de instelbare waarden klaar."""
    coordinator: VirtualEmsCoordinator = entry.runtime_data
    async_add_entities(VirtualEmsNumber(coordinator, description) for description in NUMBERS)


class VirtualEmsNumber(VirtualEmsEntity, NumberEntity):
    """Eén schuif die de cursist verzet."""

    entity_description: VirtualEmsNumberDescription

    def __init__(
        self,
        coordinator: VirtualEmsCoordinator,
        description: VirtualEmsNumberDescription,
    ) -> None:
        super().__init__(coordinator, description.key, ENTITY_ID_FORMAT)
        self.entity_description = description
        if description.limits_fn is not None:
            minimum, maximum = description.limits_fn(coordinator)
            self._attr_native_min_value = minimum
            self._attr_native_max_value = maximum

    @property
    def native_value(self) -> float:
        return self.entity_description.value_fn(self.coordinator.simulation.setpoints)

    async def async_set_native_value(self, value: float) -> None:
        await self.entity_description.set_fn(self.coordinator, value)

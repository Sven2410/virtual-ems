"""Schakelaars: de laadpaal en de virtuele apparaten."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import (
    ENTITY_ID_FORMAT,
    SwitchDeviceClass,
    SwitchEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import APPLIANCES
from .coordinator import VirtualEmsCoordinator
from .entity import VirtualEmsEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Zet de schakelaars klaar."""
    coordinator: VirtualEmsCoordinator = entry.runtime_data
    entities: list[SwitchEntity] = [VirtualEmsChargerSwitch(coordinator)]
    entities.extend(
        VirtualEmsApplianceSwitch(coordinator, key, str(spec["icon"]), float(spec["power_w"]))
        for key, spec in APPLIANCES.items()
    )
    async_add_entities(entities)


class VirtualEmsChargerSwitch(VirtualEmsEntity, SwitchEntity):
    """Aan of uit zetten van de laadpaal."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_icon = "mdi:ev-station"

    def __init__(self, coordinator: VirtualEmsCoordinator) -> None:
        super().__init__(coordinator, "laadpaal_actief", ENTITY_ID_FORMAT)

    @property
    def is_on(self) -> bool:
        return self.coordinator.simulation.setpoints.ev_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_ev_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_ev_enabled(False)


class VirtualEmsApplianceSwitch(VirtualEmsEntity, SwitchEntity):
    """Eén virtueel apparaat met een vast vermogen zolang het aan staat."""

    _attr_device_class = SwitchDeviceClass.OUTLET

    def __init__(
        self,
        coordinator: VirtualEmsCoordinator,
        key: str,
        icon: str,
        power_w: float,
    ) -> None:
        super().__init__(coordinator, key, ENTITY_ID_FORMAT)
        self._attr_icon = icon
        self._power_w = power_w

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.simulation.setpoints.appliances.get(self._key))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        # Het vermogen staat er bij, zodat een cursist op het dashboard kan
        # zien waarom de netafname met precies dit bedrag omhoog gaat.
        return {"vermogen_w": self._power_w}

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_appliance(self._key, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_appliance(self._key, False)

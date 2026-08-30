"""De hoofdzekering als eigen entiteit, want dit is een toestand met gevolgen."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    ENTITY_ID_FORMAT,
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import VirtualEmsCoordinator
from .entity import VirtualEmsEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: VirtualEmsCoordinator = entry.runtime_data
    async_add_entities([VirtualEmsHoofdzekering(coordinator)])


class VirtualEmsHoofdzekering(VirtualEmsEntity, BinarySensorEntity):
    """Aan betekent hier: er is een probleem, de zekering is doorgesmolten."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:fuse"

    def __init__(self, coordinator: VirtualEmsCoordinator) -> None:
        super().__init__(coordinator, "hoofdzekering", ENTITY_ID_FORMAT)

    @property
    def is_on(self) -> bool:
        return self.coordinator.simulation.zekering.gesprongen

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        zekering = self.coordinator.simulation.zekering
        snapshot = self.coordinator.data
        belasting = snapshot.grid_power_w if snapshot is not None else 0.0
        resterend = zekering.resterende_tijd_s(belasting)
        return {
            "warmte_pct": round(zekering.warmte_pct, 1),
            "nominaal_w": round(zekering.nominaal_w),
            # Hoe lang hij deze belasting nog volhoudt. None betekent: bij deze
            # belasting oneindig lang.
            "smelt_over_s": None if resterend is None else round(resterend),
        }

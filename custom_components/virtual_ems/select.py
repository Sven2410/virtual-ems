"""De regelmodus: wat het energiemanagementsysteem probeert te bereiken."""

from __future__ import annotations

from homeassistant.components.select import ENTITY_ID_FORMAT, SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import VirtualEmsCoordinator
from .entity import VirtualEmsEntity
from .regelaar import MODUS_HANDMATIG, MODUSSEN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: VirtualEmsCoordinator = entry.runtime_data
    async_add_entities([VirtualEmsModus(coordinator)])


class VirtualEmsModus(VirtualEmsEntity, SelectEntity):
    """De stand van de regelaar.

    Dit is de entiteit die van de installatie een systeem maakt: hier kiest de
    cursist of hij het zelf doet of dat de regelaar het overneemt.
    """

    _attr_icon = "mdi:robot-industrial"
    _attr_options = list(MODUSSEN)

    def __init__(self, coordinator: VirtualEmsCoordinator) -> None:
        super().__init__(coordinator, "regelmodus", ENTITY_ID_FORMAT)

    @property
    def current_option(self) -> str:
        modus = self.coordinator.simulation.setpoints.modus
        return modus if modus in MODUSSEN else MODUS_HANDMATIG

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_modus(option)

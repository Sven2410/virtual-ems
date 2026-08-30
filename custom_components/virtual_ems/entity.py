"""Gedeelde basisklasse voor alle entiteiten van virtual_ems."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .coordinator import VirtualEmsCoordinator


class VirtualEmsEntity(CoordinatorEntity[VirtualEmsCoordinator]):
    """Basis voor elke entiteit: één apparaat, vaste entity_id, vertaalde naam."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VirtualEmsCoordinator,
        key: str,
        entity_id_format: str,
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{key}"
        self._attr_translation_key = key

        # De entity_id wordt hier bewust vastgelegd op <naam>_<sleutel>. Zou we
        # dat aan Home Assistant overlaten, dan zou hij hem afleiden uit de
        # vertaalde naam en zouden de dashboards op een Engelstalige installatie
        # naar niet-bestaande entiteiten wijzen.
        self.entity_id = async_generate_entity_id(
            entity_id_format,
            f"{slugify(coordinator.installation_name)}_{key}",
            hass=coordinator.hass,
        )

    @property
    def device_info(self) -> DeviceInfo:
        return self.coordinator.device_info

"""Shared base entity — one device, consistent naming and availability."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TeamsRandomiserCoordinator


class TeamsRandomiserEntity(CoordinatorEntity[TeamsRandomiserCoordinator]):
    """Base for every entity, so they group under one device card."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: TeamsRandomiserCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Chris971991",
            model="Teams Status Randomiser",
            sw_version=self._data.get("version"),
            configuration_url=f"http://{entry.data['host']}:{entry.data['port']}/status",
        )

    @property
    def _data(self) -> dict[str, Any]:
        return self.coordinator.data or {}

    @property
    def available(self) -> bool:
        # The app answering is what "available" means here. Note the app can be
        # reachable while Teams itself is closed — that is NOT unavailable, it
        # is a real, reportable state, so it is exposed as its own sensor
        # rather than blanking every entity.
        return super().available and bool(self.coordinator.data)

"""Binary sensors — the app's own view of what is happening."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TeamsRandomiserConfigEntry
from .coordinator import TeamsRandomiserCoordinator
from .entity import TeamsRandomiserEntity


@dataclass(frozen=True, kw_only=True)
class TeamsBinaryDescription(BinarySensorEntityDescription):
    """Maps a /status field onto a binary sensor."""

    value: Callable[[dict[str, Any]], bool | None]


BINARY_SENSORS: tuple[TeamsBinaryDescription, ...] = (
    # The single most useful thing to automate on. The app's historical failure
    # mode is going SILENT: it keeps ticking while presence is frozen. Alerting
    # when this is off during work hours is the difference between noticing at
    # 9:15am and never noticing.
    TeamsBinaryDescription(
        key="connected",
        translation_key="connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda d: d.get("cdpConnected"),
    ),
    TeamsBinaryDescription(
        key="teams_running",
        translation_key="teams_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:microsoft-teams",
        value=lambda d: d.get("teamsRunning"),
    ),
    TeamsBinaryDescription(
        key="in_work_hours",
        translation_key="in_work_hours",
        icon="mdi:briefcase-clock-outline",
        value=lambda d: d.get("inActiveHours"),
    ),
    TeamsBinaryDescription(
        key="day_off",
        translation_key="day_off",
        icon="mdi:calendar-remove-outline",
        value=lambda d: d.get("dayOff"),
    ),
    TeamsBinaryDescription(
        key="on_break",
        translation_key="on_break",
        icon="mdi:coffee",
        value=lambda d: d.get("onBreak"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TeamsRandomiserConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        TeamsRandomiserBinarySensor(entry.runtime_data, description)
        for description in BINARY_SENSORS
    )


class TeamsRandomiserBinarySensor(TeamsRandomiserEntity, BinarySensorEntity):
    """One boolean field of /status."""

    entity_description: TeamsBinaryDescription

    def __init__(
        self,
        coordinator: TeamsRandomiserCoordinator,
        description: TeamsBinaryDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        value = self.entity_description.value(self._data)
        return None if value is None else bool(value)

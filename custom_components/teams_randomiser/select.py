"""Select entities: pick a Teams status or a work location directly."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TeamsRandomiserConfigEntry
from .const import STATUSES, WORK_LOCATIONS
from .entity import TeamsRandomiserEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TeamsRandomiserConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        [
            TeamsStatusSelect(entry.runtime_data),
            TeamsWorkLocationSelect(entry.runtime_data),
        ]
    )


class TeamsStatusSelect(TeamsRandomiserEntity, SelectEntity):
    """The Teams status, as a dropdown.

    Choosing one is a MANUAL set: it overrides the randomiser's schedule and
    ends any simulated break or lunch early. The randomiser resumes at its next
    scheduled change — use the switch to pause it, or the reset button to hand
    presence back to Teams entirely.
    """

    _attr_translation_key = "status"
    _attr_icon = "mdi:microsoft-teams"
    _attr_options = STATUSES

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "status")

    @property
    def current_option(self) -> str | None:
        status = self._data.get("status")
        # Only report a value the dropdown actually offers. The app reports
        # null before its first change of the day, and Teams' own automatic
        # presence can be something not in this list (e.g. "In a meeting").
        return status if status in STATUSES else None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_send(f"set {option}")


class TeamsWorkLocationSelect(TeamsRandomiserEntity, SelectEntity):
    """Work location shown on the Teams profile.

    Licence-gated: on a tenant without Microsoft Places the control does not
    exist in Teams at all and the command will fail. There is no way to read
    the current value back, so this is write-only and stays unknown.
    """

    _attr_translation_key = "work_location"
    _attr_icon = "mdi:office-building-marker-outline"
    _attr_options = WORK_LOCATIONS
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "work_location")

    @property
    def current_option(self) -> str | None:
        return None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_send(f"location {option.lower()}")

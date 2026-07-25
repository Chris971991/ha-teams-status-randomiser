"""Switch: run or pause the randomiser."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TeamsRandomiserConfigEntry
from .entity import TeamsRandomiserEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TeamsRandomiserConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([TeamsRandomiserSwitch(entry.runtime_data)])


class TeamsRandomiserSwitch(TeamsRandomiserEntity, SwitchEntity):
    """Whether the randomiser is actively changing the status.

    Off leaves whatever status is currently showing in place — it stops future
    changes, it does not revert. Use the "Reset to automatic" button to hand
    presence back to Teams.
    """

    _attr_translation_key = "randomiser"
    _attr_icon = "mdi:shuffle-variant"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "randomiser")

    @property
    def is_on(self) -> bool | None:
        # The app has two independent notions: a master enable, and a timed
        # pause. Either one stops changes, so the switch reflects both — it is
        # "is the randomiser actually going to do anything", not one flag.
        enabled = self._data.get("enabled")
        if enabled is None:
            return None
        return bool(enabled) and not bool(self._data.get("paused"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "enabled": self._data.get("enabled"),
            "paused": self._data.get("paused"),
            "paused_until": self._data.get("pausedUntil"),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_send("resume")

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_send("pause")

"""Text: read and write the Teams status message."""

from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TeamsRandomiserConfigEntry
from .entity import TeamsRandomiserEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TeamsRandomiserConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([TeamsMessageText(entry.runtime_data)])


class TeamsMessageText(TeamsRandomiserEntity, TextEntity):
    """The status message shown under your name in Teams.

    Note the app may rotate this on its own if message rotation is enabled in
    its settings, so a value set here is not necessarily permanent.
    """

    _attr_translation_key = "message"
    _attr_icon = "mdi:message-text-outline"
    # Teams' own compose box is the real limit; this is a sane guard that still
    # allows the kind of note people actually write.
    _attr_native_max = 255
    _attr_native_min = 0

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "message")

    @property
    def native_value(self) -> str | None:
        message = self._data.get("message")
        # Empty string rather than None: a text entity with no value shows as
        # unknown, which reads as "we cannot tell" when in fact we know the
        # message is cleared.
        return "" if message is None else str(message)[:255]

    async def async_set_value(self, value: str) -> None:
        text = value.strip()
        await self.coordinator.async_send("msg clear" if not text else f"msg {text}")

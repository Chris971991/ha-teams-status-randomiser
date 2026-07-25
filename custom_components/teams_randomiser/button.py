"""Buttons: one-shot actions with no state of their own."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable, Coroutine
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TeamsRandomiserConfigEntry
from .coordinator import TeamsRandomiserCoordinator
from .entity import TeamsRandomiserEntity


@dataclass(frozen=True, kw_only=True)
class TeamsButtonDescription(ButtonEntityDescription):
    """A button and the command line it sends."""

    command: str


BUTTONS: tuple[TeamsButtonDescription, ...] = (
    TeamsButtonDescription(
        key="change_now",
        translation_key="change_now",
        icon="mdi:dice-multiple-outline",
        command="change",
    ),
    TeamsButtonDescription(
        key="reroll",
        translation_key="reroll",
        icon="mdi:reload",
        command="reroll",
    ),
    TeamsButtonDescription(
        key="reset",
        translation_key="reset",
        icon="mdi:backup-restore",
        command="reset",
    ),
    TeamsButtonDescription(
        key="clear_message",
        translation_key="clear_message",
        icon="mdi:message-off-outline",
        command="msg clear",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TeamsRandomiserConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        TeamsRandomiserButton(entry.runtime_data, description)
        for description in BUTTONS
    )


class TeamsRandomiserButton(TeamsRandomiserEntity, ButtonEntity):
    """Sends one command line when pressed."""

    entity_description: TeamsButtonDescription

    def __init__(
        self,
        coordinator: TeamsRandomiserCoordinator,
        description: TeamsButtonDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    async def async_press(self) -> None:
        await self.coordinator.async_send(self.entity_description.command)

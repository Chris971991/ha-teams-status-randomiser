"""The Teams Status Randomiser integration.

Talks to the tray app's local HTTP bridge on a Windows PC. The app drives the
Microsoft Teams desktop client directly through its own debug port, so this
needs no Microsoft Graph access, no Entra app registration and no admin
consent — which matters on tenants that block app registrations outright.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .coordinator import TeamsRandomiserClient, TeamsRandomiserCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TEXT,
]

type TeamsRandomiserConfigEntry = ConfigEntry[TeamsRandomiserCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: TeamsRandomiserConfigEntry
) -> bool:
    """Set up from a config entry."""
    client = TeamsRandomiserClient(
        async_get_clientsession(hass),
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data.get(CONF_TOKEN),
    )
    coordinator = TeamsRandomiserCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: TeamsRandomiserConfigEntry
) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)

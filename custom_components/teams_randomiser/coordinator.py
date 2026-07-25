"""Client and update coordinator for the Teams Status Randomiser bridge."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import COMMAND_TIMEOUT, DOMAIN, STATUS_TIMEOUT, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class InvalidAuth(HomeAssistantError):
    """The bridge rejected the access token."""


class CannotConnect(HomeAssistantError):
    """The bridge could not be reached."""


class CommandRefused(HomeAssistantError):
    """The command reached the app and the app refused it."""


def _tidy(reply: str) -> str:
    """Collapse the app's nested error prefixes into one readable sentence.

    The app wraps an engine error inside its own, so a refused command arrives
    as "ERR CDP could not set work location 'Office': ERR location did not
    change ...". Home Assistant shows this verbatim in a toast, where the
    repeated ERR reads like a stutter and buries the part that matters.
    """
    text = (reply or "").strip()
    while text.upper().startswith("ERR "):
        text = text[4:].lstrip()
    # ...and the inner one, wherever the app spliced it in.
    text = text.replace(": ERR ", ": ")
    return text


class TeamsRandomiserClient:
    """Thin wrapper over the app's local HTTP bridge.

    Two endpoints only: GET /status returns the whole state as JSON, and
    POST /cmd takes ONE COMMAND LINE AS PLAIN TEXT — not JSON. The app replies
    {"reply": "..."} and uses HTTP 200 only when the reply starts with "OK", so
    a refused command is a real HTTP error rather than a silent success.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        host: str,
        port: int,
        token: str | None,
    ) -> None:
        self._session = session
        self._base = f"http://{host}:{port}"
        self._headers: dict[str, str] = {}
        if token:
            # Accept either form, so a user who pastes "Bearer xyz" straight
            # out of the app's settings window still works.
            value = token if token.lower().startswith("bearer ") else f"Bearer {token}"
            self._headers["Authorization"] = value

    async def async_get_status(self) -> dict[str, Any]:
        """Fetch the full state."""
        try:
            async with self._session.get(
                f"{self._base}/status",
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=STATUS_TIMEOUT),
            ) as resp:
                if resp.status in (401, 403):
                    raise InvalidAuth
                resp.raise_for_status()
                return await resp.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise CannotConnect(str(err)) from err

    async def async_command(self, command: str) -> str:
        """Send one command line and return the app's reply."""
        try:
            async with self._session.post(
                f"{self._base}/cmd",
                headers={**self._headers, "Content-Type": "text/plain"},
                data=command.encode("utf-8"),
                timeout=aiohttp.ClientTimeout(total=COMMAND_TIMEOUT),
            ) as resp:
                if resp.status in (401, 403):
                    raise InvalidAuth
                try:
                    payload = await resp.json()
                    reply = str(payload.get("reply", ""))
                except (aiohttp.ContentTypeError, ValueError):
                    reply = await resp.text()
                if resp.status != 200:
                    # Surface the app's own wording — it is written for humans
                    # and says WHY (Teams not running, work location not
                    # licensed, a status not in the pool).
                    raise CommandRefused(_tidy(reply) or f"HTTP {resp.status}")
                return reply
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise CannotConnect(str(err)) from err


class TeamsRandomiserCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Polls /status and lets entities push commands."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: TeamsRandomiserClient
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
            config_entry=entry,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.client.async_get_status()
        except InvalidAuth as err:
            raise UpdateFailed("The bridge rejected the access token") from err
        except CannotConnect as err:
            raise UpdateFailed(f"Cannot reach the app: {err}") from err

    async def async_send(self, command: str) -> str:
        """Run a command, then refresh so entities reflect it immediately.

        The refresh matters: a status write takes seconds, and without it every
        control would snap back to its old value until the next poll and look
        like the command had been ignored.
        """
        reply = await self.client.async_command(command)
        await self.async_request_refresh()
        return reply

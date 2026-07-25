"""Config flow for the Teams Status Randomiser integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_NAME, DEFAULT_PORT, DOMAIN
from .coordinator import CannotConnect, InvalidAuth, TeamsRandomiserClient


async def _validate(hass, data: dict[str, Any]) -> dict[str, Any]:
    """Prove we can actually reach the bridge before creating the entry.

    Validating here rather than at first refresh means a wrong port, a missing
    firewall rule or a bad token is reported in the dialog the user is looking
    at — instead of as an entry that silently never produces entities.
    """
    client = TeamsRandomiserClient(
        async_get_clientsession(hass),
        data[CONF_HOST],
        data[CONF_PORT],
        data.get(CONF_TOKEN),
    )
    return await client.async_get_status()


class TeamsRandomiserConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for host, port and token; verify before finishing."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            # One entry per bridge address.
            await self.async_set_unique_id(
                f"{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
            )
            self._abort_if_unique_id_configured()
            try:
                status = await _validate(self.hass, user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 - surfaced to the user as "unknown"
                errors["base"] = "unknown"
            else:
                version = status.get("version", "")
                return self.async_create_entry(
                    title=f"{DEFAULT_NAME}" + (f" {version}" if version else ""),
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=user_input.get(CONF_HOST) if user_input else vol.UNDEFINED): str,
                    vol.Required(CONF_PORT, default=(user_input or {}).get(CONF_PORT, DEFAULT_PORT)): int,
                    vol.Optional(CONF_TOKEN, default=(user_input or {}).get(CONF_TOKEN, "")): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the address or token be corrected without deleting the entry.

        The token is regenerated in the app's settings window, and the PC's IP
        can move on DHCP — both would otherwise mean removing and re-adding,
        losing entity IDs and history.
        """
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await _validate(self.hass, user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(entry, data=user_input)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST, default=entry.data[CONF_HOST]): str,
                    vol.Required(CONF_PORT, default=entry.data[CONF_PORT]): int,
                    vol.Optional(CONF_TOKEN, default=entry.data.get(CONF_TOKEN, "")): str,
                }
            ),
            errors=errors,
        )

"""Read-only sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import TeamsRandomiserConfigEntry
from .coordinator import TeamsRandomiserCoordinator
from .entity import TeamsRandomiserEntity


def _timestamp(raw: Any) -> datetime | None:
    """Parse one of the app's timestamps.

    The app emits a full offset (e.g. +10:00). Home Assistant used to read
    these as UTC when it did not, so the offset is load-bearing — do not
    "simplify" this to a naive parse.
    """
    if not raw:
        return None
    return dt_util.parse_datetime(str(raw))


def _not_scheduled(data: dict[str, Any]) -> str:
    """Why there is nothing scheduled, in words a person can act on."""
    if data.get("dayOff"):
        return "Day off"
    if data.get("inActiveHours") is False:
        return "Outside work hours"
    if data.get("paused"):
        return "Paused"
    return "Not scheduled"


def _time_or_reason(data: dict[str, Any], key: str, enabled: Any) -> str:
    """The scheduled time as a local clock time, or why there isn't one."""
    when = _timestamp(data.get(key))
    if when is not None:
        # Local time, no date: these are always today, and "11:47 AM" is what
        # someone glancing at a dashboard wants. Built without %-I / %#I, which
        # are platform-specific and would differ between a dev box and HAOS.
        local = dt_util.as_local(when)
        hour = local.hour % 12 or 12
        return f"{hour}:{local.minute:02d} {'AM' if local.hour < 12 else 'PM'}"
    if enabled is False:
        return "Turned off in settings"
    return _not_scheduled(data)


@dataclass(frozen=True, kw_only=True)
class TeamsSensorDescription(SensorEntityDescription):
    """Maps a /status field onto a sensor."""

    value: Callable[[dict[str, Any]], Any]
    extra: Callable[[dict[str, Any]], dict[str, Any]] | None = None


SENSORS: tuple[TeamsSensorDescription, ...] = (
    # What Teams is showing. This is the one people mean by "my status".
    TeamsSensorDescription(
        key="teams_presence",
        translation_key="teams_presence",
        icon="mdi:microsoft-teams",
        value=lambda d: d.get("teamsPresence") or d.get("status"),
    ),
    # What the APP last set, which is deliberately different: null after a
    # reset, before the day's first change, and all day on a day off. Useful
    # for telling "the randomiser did this" from "Teams decided this".
    TeamsSensorDescription(
        key="status",
        translation_key="status",
        icon="mdi:shuffle-variant",
        value=lambda d: d.get("status"),
    ),
    TeamsSensorDescription(
        key="message",
        translation_key="message",
        icon="mdi:message-text-outline",
        value=lambda d: d.get("message"),
    ),
    # A plain sensor, so it can say WHY rather than "Unknown": nothing is drawn
    # outside working hours, which is correct rather than a fault.
    TeamsSensorDescription(
        key="upcoming",
        translation_key="upcoming",
        icon="mdi:skip-next-outline",
        value=lambda d: d.get("upcoming") or _not_scheduled(d),
    ),
    # Falls back to when the window next OPENS, so an evening or a weekend
    # reads "Monday 5:30 am" instead of Unknown. Needs app 2.17.0+; older
    # versions simply have no fallback and behave as before.
    TeamsSensorDescription(
        key="next_change",
        translation_key="next_change",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-outline",
        value=lambda d: _timestamp(d.get("nextChange") or d.get("nextWindowStart")),
    ),
    # NOT timestamp sensors, deliberately. A timestamp sensor can only ever be
    # a time or "Unknown", and these two are usually not scheduled — off in
    # settings, or a day off — so the card was a column of Unknowns that gave
    # the reader nothing. They show the time when there is one and say WHY when
    # there is not; the raw ISO value stays in the `timestamp` attribute so
    # automations lose nothing.
    TeamsSensorDescription(
        key="lunch_at",
        translation_key="lunch_at",
        icon="mdi:silverware-fork-knife",
        value=lambda d: _time_or_reason(d, "lunchAt", d.get("lunchEnabled")),
        extra=lambda d: {"timestamp": d.get("lunchAt")},
    ),
    TeamsSensorDescription(
        key="next_break",
        translation_key="next_break",
        icon="mdi:coffee-outline",
        value=lambda d: _time_or_reason(d, "nextBreakAt", d.get("breaksEnabled")),
        extra=lambda d: {"timestamp": d.get("nextBreakAt")},
    ),
    TeamsSensorDescription(
        key="changes_today",
        translation_key="changes_today",
        icon="mdi:counter",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value=lambda d: d.get("changesToday"),
    ),
    TeamsSensorDescription(
        key="engine",
        translation_key="engine",
        icon="mdi:cog-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        # "cdp" = invisible, "uia" = the visible fallback, "none" = idle.
        value=lambda d: d.get("engine"),
    ),
    TeamsSensorDescription(
        key="last_error",
        translation_key="last_error",
        icon="mdi:alert-circle-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        # HA rejects states over 255 chars outright, and the app's errors can
        # carry a whole CDP payload — truncate rather than lose the entity.
        value=lambda d: (str(d["lastError"])[:250] if d.get("lastError") else "none"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TeamsRandomiserConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities(
        TeamsRandomiserSensor(entry.runtime_data, description)
        for description in SENSORS
    )


class TeamsRandomiserSensor(TeamsRandomiserEntity, SensorEntity):
    """One field of /status."""

    entity_description: TeamsSensorDescription

    def __init__(
        self,
        coordinator: TeamsRandomiserCoordinator,
        description: TeamsSensorDescription,
    ) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value(self._data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        extra = self.entity_description.extra
        return extra(self._data) if extra else None

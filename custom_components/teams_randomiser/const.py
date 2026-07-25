"""Constants for the Teams Status Randomiser integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "teams_randomiser"

DEFAULT_PORT = 8757
DEFAULT_NAME = "Teams Status Randomiser"

# The app's own scheduler ticks every 15 s, so polling faster than that only
# adds load without telling us anything new.
UPDATE_INTERVAL = timedelta(seconds=30)

# A status write drives the real Teams client and can take minutes against a
# degraded one — the app's own in-page script budgets run to ~100 s and its
# engine gate waits up to 240 s. Anything less and we would report failure for
# writes that are still in flight and about to succeed.
COMMAND_TIMEOUT = 180
STATUS_TIMEOUT = 15

# The exact names the Teams menu uses. The app matches these verbatim, so they
# are not free text — a typo silently matches the wrong option.
STATUSES = [
    "Available",
    "Busy",
    "Do not disturb",
    "Be right back",
    "Appear away",
    "Appear offline",
]

WORK_LOCATIONS = ["Office", "Remote", "Clear"]

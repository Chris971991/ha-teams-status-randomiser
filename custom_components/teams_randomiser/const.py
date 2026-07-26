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

# "Not set" is both the empty state AND the way to clear it — a select must
# report one of its own options, so a separate "Clear" verb left the control
# showing Unknown whenever no location was set, which is the normal case.
WORK_LOCATION_NONE = "Not set"
WORK_LOCATIONS = [WORK_LOCATION_NONE, "Office", "Remote"]

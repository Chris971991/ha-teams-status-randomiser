# CLAUDE.md — Teams Status Randomiser (Home Assistant integration)

Guidance for Claude Code working on this repository.

## What this is

A HACS custom integration that puts [Teams Status
Randomiser](https://github.com/Chris971991/TeamsStatusRandomiser-Releases) into
Home Assistant as one device with real entities.

**Public repo:** `Chris971991/ha-teams-status-randomiser`
**The app it talks to:** source lives at `C:\Users\Chris\Documents\TeamsStatusRandomiser`
(private repo `Chris971991/TeamsStatusRandomiser`) — read its `CLAUDE.md` before
changing anything about the protocol.

Chris's install: HA **2026.7.3** at `192.168.50.45`, config reachable at
`\\192.168.50.45\config\`. The app runs on `192.168.50.6:8757`.

## Why it is not a Graph integration

There is no Microsoft Graph, Entra app registration or admin consent anywhere in
this path, and that is forced rather than chosen. On Chris's tenant
`setUserPreferredPresence` returns **401** because the org blocks the Entra admin
portal outright, so a normal user cannot create a registration at all. The app
drives the Teams desktop client through its own debug port instead.

**If anyone (including another assistant) suggests the MS365-Teams HACS
integration, that is a dead end here** — it needs exactly the app registration
that cannot be created.

## The protocol

Two endpoints on the app's local HTTP bridge, both needing
`Authorization: Bearer <token>`.

- `GET /status` → the whole state as JSON.
- `POST /cmd` → **ONE COMMAND LINE AS PLAIN TEXT, NOT JSON.** Replies
  `{"reply": "..."}` and uses HTTP 200 **only** when the reply starts with `OK`,
  so a refused command is a real HTTP error rather than a silent success.

Commands are the app's CLI verbs: `status`, `change`, `reroll`, `reset`,
`pause [min]`, `resume`, `set <status> [min]`, `msg <text>`, `msg clear`,
`location office|remote|clear`.

### `status` vs `teamsPresence` — do not conflate these

| Field | Means |
|---|---|
| `status` | what the APP last set. Null after a reset, before the day's first change, and all day on a day off |
| `teamsPresence` | what Teams is ACTUALLY showing (needs app **2.16.1+**) |

Keying the status `select` off `status` alone made it read **unknown** while
Teams plainly displayed Available. It prefers `teamsPresence` now and falls back.

The select deliberately returns `None` when Teams shows something it cannot set
("In a meeting", "Presenting") — those are Teams' own automatic presence, and
offering them as a *selected* option would imply we could set them back.

## Non-obvious things — read before debugging

**1. HA caches `__pycache__`, and over an SMB share it wins.** Editing a `.py`
in `\\192.168.50.45\config\custom_components\teams_randomiser\` and restarting
is NOT enough — HA kept running the old bytecode across a full restart. Delete
`__pycache__` as well. This cost two extra restarts to work out.

**2. `has_entity_name` derives entity_ids from the DEVICE name**, which comes
from the config entry title. Putting the app version in the title baked
`_2_16_0_` into all 20 entity_ids, where it would have gone stale on the next app
update and been uncorrectable without renaming everything. The version belongs on
the device as `sw_version`, which updates itself.

**3. The command timeout is 180 s deliberately.** A status write drives the real
Teams client; the app's own in-page script budgets run to ~100 s and its engine
gate waits up to 240 s. Anything shorter reports failure for writes that are
still in flight and about to succeed.

**4. `async_send` refreshes the coordinator after every command.** Without it
each control snaps back to its old value until the next poll and looks ignored.
Note the app has a matching hazard on its side — see its `teamsPresence` cache
rules; a write there must update the cache or the same snap-back reappears one
layer down (it did, and shipped as 2.16.2).

**5. Work location reads AND writes** (app 2.16.4+). It was neither for a while,
and the reason is worth keeping: the Teams menu options ignore a synthetic
`.click()` and ignore a full pointer sequence too — they commit only on a
**keyboard press** (focus, then Enter). I told Chris this was a Microsoft Places
licence gap without testing it. He pushed back, three activation methods were
tried, and the licence story was simply wrong. Do not repeat that: an untested
cause stated confidently is worse than "I don't know yet".

The select's options are `Not set` / `Office` / `Remote`. A `select` can only
report one of its own options, so an unset location needs a real option to sit
on — that is what `Not set` is for, and choosing it sends `location clear`.

**6. An entity that says `Unknown` most of the time is a design fault, not a
state.** Four sensors read Unknown on any evening, weekend or day off. Two causes:
the app sent `null` for anything not currently scheduled without distinguishing
*turned off* from *not right now* (fixed app-side in 2.17.0 with
`nextWindowStart`, `breaksEnabled`, `lunchEnabled`), and `device_class:
timestamp` **cannot** hold an explanation — it is a time or it is Unknown. Where
the useful answer is often a reason rather than a moment, use a plain sensor and
keep the machine-readable value in a `timestamp` attribute.

Format times with `hour % 12 or 12` — `%-I` (glibc) and `%#I` (Windows) are both
platform-specific and one of them throws on the other platform.

**7. Availability means "the app answered".** The app being reachable while Teams
itself is closed is NOT unavailable — it is a real, reportable state, exposed as
its own `teams_running` sensor rather than blanking every entity.

## Layout

```
custom_components/teams_randomiser/
  __init__.py        setup/unload, PLATFORMS, runtime_data
  coordinator.py     the HTTP client + DataUpdateCoordinator
  entity.py          shared base: one device, availability
  config_flow.py     host/port/token, validated against a live /status
  const.py           statuses, timeouts, poll interval
  select.py switch.py button.py text.py sensor.py binary_sensor.py
  strings.json + translations/en.json
hacs.json            HACS metadata
```

`STATUSES` in `const.py` are the exact Teams menu labels. The app matches them
verbatim — a typo silently matches the wrong option rather than failing.

## Releasing

1. Bump `version` in `custom_components/teams_randomiser/manifest.json`.
2. Commit, push.
3. `gh release create vX.Y.Z --title vX.Y.Z --notes "..."` — HACS reads releases.
4. If it needs a newer app, say so in the README and the notes.

## Testing

There is no test suite yet. Verify against Chris's live HA:

- `ha_eval_template` with `integration_entities('teams_randomiser')` to list
  entities and states.
- Drive a control (`select.select_option`, `button.press`) and then read
  `%APPDATA%\TeamsStatusRandomiser\debug.log` on the PC — it logs
  `POST /cmd from <HA ip>` and the engine result, which proves the whole chain
  rather than just that HA ran something.
- **Put presence back afterwards** (`button.press` on *Reset to automatic*).
  This is Chris's real work account.

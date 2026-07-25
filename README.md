# Teams Status Randomiser — Home Assistant integration

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Chris971991&repository=ha-teams-status-randomiser&category=integration)
[![Add integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=teams_randomiser)

Control and monitor [Teams Status Randomiser](https://github.com/Chris971991/TeamsStatusRandomiser-Releases)
from Home Assistant.

The app drives the Microsoft Teams **desktop client** directly, through its own
debug port. That means this integration needs:

- **no Microsoft Graph access**
- **no Entra app registration**
- **no admin consent**
- **no Premium connector or licence**

which matters, because on a locked-down tenant the Graph route is simply not
available — `setUserPreferredPresence` returns 401 when the organisation blocks
app registrations, and there is no way for a normal user to create one. Driving
the client is what works.

Everything is local: Home Assistant talks HTTP to the PC on your own network.

## What you get

One device with the following entities.

### Controls

| Entity | Type | What it does |
|---|---|---|
| Status | `select` | Set the Teams status directly — Available, Busy, Do not disturb, Be right back, Appear away, Appear offline |
| Status message | `text` | Read and write the note under your name; blank clears it |
| Randomiser | `switch` | Run or pause the randomiser without changing what is showing |
| Change status now | `button` | Pick a new status immediately from the weighted pool |
| Reset to automatic | `button` | Hand presence back to Teams and clear the app's message |
| Clear status message | `button` | Remove the note |
| Reroll next status | `button` | Re-draw the *upcoming* status without changing the current one |
| Work location | `select` | Office / Remote / Clear — needs Microsoft Places on your tenant (see Notes) |

### State

| Entity | Type | Notes |
|---|---|---|
| **Teams presence** | `sensor` | What Teams is actually showing |
| Status set by the app, Status message, Next status | `sensor` | What the *randomiser* set — null after a reset or on a day off |
| Next change, Lunch at, Next break | `sensor` (timestamp) | Carry a real timezone offset |
| Changes today | `sensor` | Resets daily |
| Engine, Last error | `sensor` (diagnostic) | `cdp` = invisible, `uia` = visible fallback |
| **Connected to Teams** | `binary_sensor` (connectivity) | **The one worth automating on — see below** |
| Teams running, In work hours, Day off, On break | `binary_sensor` | |

## Install

### HACS

Click the badge at the top, or by hand:

1. HACS → three-dot menu → **Custom repositories**
2. Add `https://github.com/Chris971991/ha-teams-status-randomiser`, type **Integration**
3. Install, then restart Home Assistant
4. Settings → Devices & Services → **Add integration** → *Teams Status Randomiser*

Needs the app itself: **[Teams Status Randomiser](https://github.com/Chris971991/TeamsStatusRandomiser-Releases/releases/latest)**
(2.16.2 or newer for live presence).

### Manual

Copy `custom_components/teams_randomiser` into your `config/custom_components/`
directory and restart.

## Setup

In the app on your PC: **Settings → Behaviour → System**

1. Turn the **HTTP bridge** on
2. Generate a **token** (required for network access)
3. Tick **Allow other machines on my network to connect**
4. Press **Save** — the app offers to add the Windows Firewall rule. Accept it.

Then add the integration in Home Assistant with the PC's IP, the port (8757 by
default) and that token.

Check it first if you like:

```bash
curl -H "Authorization: Bearer <token>" http://<pc-ip>:8757/status
```

## The automation worth having

The app's historical weakness is failing *silently* — it keeps running while
presence is frozen, and nothing tells you. This catches that:

```yaml
alias: Teams randomiser has stopped working
triggers:
  - trigger: state
    entity_id: binary_sensor.teams_status_randomiser_connected_to_teams
    to: "off"
    for: "00:15:00"
conditions:
  - condition: state
    entity_id: binary_sensor.teams_status_randomiser_in_work_hours
    state: "on"
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: Teams randomiser
      message: >-
        Not connected for 15 minutes — your status is probably stuck.
        {{ states('sensor.teams_status_randomiser_last_error') }}
mode: single
```

## Notes

- Setting a status from Home Assistant is a **manual override**: it takes
  precedence over the randomiser's schedule and ends any simulated break or
  lunch early. The switch pauses future changes; the reset button hands
  presence back to Teams entirely.
- The bridge is **plain HTTP**. Keep it on a home network — the token and your
  presence cross the network unencrypted.
- Commands need **Teams running**. With Teams closed they fail with a clear
  error rather than silently doing nothing.
- **Work location is licence-gated behind Microsoft Places.** Where it is not
  enabled, Teams still *renders* the menu option and silently ignores the click
  — app versions before 2.16.3 reported success for a write that never applied.
  The app verifies now, so the control fails honestly instead. Its current value
  is read back from Teams (app 2.16.3+), and is blank when nothing is set.
- **"Next change" is blank outside working hours and on days off** — the
  randomiser has nothing scheduled then, which is correct rather than a fault.
  The *Day off* and *In work hours* sensors say why.
- **Buttons show `unknown` until pressed.** That is Home Assistant's convention:
  a button's state is the timestamp of its last press.

## Licence

MIT

# Tado HomeKit Local API

Runbook and architecture notes for Leo.

## Goal

Provide **local-only heating control** for Dani's legacy Tado setup via the Internet Bridge's HomeKit/HAP interface, without depending on Tado cloud polling or Home Assistant's cloud integration.

This service is the current **Plan A** for heating zones.

Hot water (`BU0542969600`) is **not** implemented here yet and can stay on cloud if needed.

---

## Current production deployment

### Host
- Hostname: `domo-server`
- IP: `192.168.200.2`
- OS: Ubuntu 22.04

### Install path
- `/opt/tado-local-homekit`

### Service
- systemd unit: `tado-local-homekit.service`
- TCP port: `4407`

### Runtime
- Python venv: `/opt/tado-local-homekit/.venv`
- App entrypoint: `/opt/tado-local-homekit/app.py`
- Pairing file: `/opt/tado-local-homekit/tado-homekit-pairing.json`

### API base URL
- `http://192.168.200.2:4407`

---

## What is already proven

### Local pairing
The old Tado Internet Bridge (`IB0090508800`) exposes HomeKit/HAP on:
- bridge IP: `192.168.200.10`
- bridge port: `80`

Successful HomeKit setup code used during pairing:
- `653-11-104`

### Local read
All four heating zones are visible locally via HomeKit/HAP.

### Local write
Writing target temperature locally works and propagates into the real Tado system.

Validated example:
- PLANTA 1 (`RU2165705728`) changed locally from `16 °C` to `18 °C`
- Dani confirmed the change appeared in the official Tado app

This proves end-to-end local control for heating zones.

---

## House mapping

### Infrastructure
- `IB0090508800` -> Internet Bridge (`IB01`)
- `BU0542969600` -> Extension Kit / hot water

### Heating zones
- `RU2165705728` -> `PLANTA 1`
- `RU0572525568` -> `PLANTA 2`
- `RU3827043328` -> `ATICO`
- `RU3948940800` -> `MERENDERO`

### API slug mapping
The service exposes these slugs:
- `planta1`
- `planta2`
- `atico`
- `merendero`

---

## API contract

### `GET /status`
Health and discovery summary.

Example:
```json
{
  "status": "ok",
  "bridge_host": "192.168.200.10",
  "bridge_port": 80,
  "pairing_path": "/opt/tado-local-homekit/tado-homekit-pairing.json",
  "zones_count": 4,
  "zones": ["planta2", "atico", "planta1", "merendero"]
}
```

### `GET /zones`
Returns all zone states.

Per zone fields currently exposed:
- `slug`
- `name`
- `serial`
- `aid`
- `current_temperature`
- `target_temperature`
- `humidity`
- `target_hvac_state`
- `current_hvac_state`
- `hvac_mode`
- `hvac_action`

### `GET /zones/{slug}`
Returns one zone state.

Example:
```bash
curl http://192.168.200.2:4407/zones/planta1
```

### `POST /zones/{slug}/set`
Writes zone state locally through HomeKit.

Payload:
```json
{
  "temperature": 18,
  "mode": "heat"
}
```

Rules:
- `mode` supports `off`, `heat`, or `auto`
- if `temperature` is provided without `mode`, service forces `heat`
- `auto` currently means: re-enable heating without changing target temperature (AUTO-like UX; not guaranteed full cloud schedule semantics)
- no support yet for true Tado schedule/auto semantics beyond this basic mapping

Examples:
```bash
curl -X POST http://192.168.200.2:4407/zones/planta1/set \
  -H 'Content-Type: application/json' \
  -d '{"temperature": 18}'
```

```bash
curl -X POST http://192.168.200.2:4407/zones/atico/set \
  -H 'Content-Type: application/json' \
  -d '{"mode": "off"}'
```

### `POST /refresh`
Forces HomeKit rediscovery of accessories and rebuilds internal zone map.

---

## HomeKit/HAP details used

### Bridge target
- Accessory host: `192.168.200.10`
- Accessory port: `80`

### Per-zone characteristic model
For each thermostat accessory, the service maps:
- `CurrentHeatingCoolingState`
- `TargetHeatingCoolingState`
- `CurrentTemperature`
- `TargetTemperature`
- `CurrentRelativeHumidity`

### HVAC mode mapping used by current service
- `TargetHeatingCoolingState = 0` -> `off`
- `TargetHeatingCoolingState = 1` -> `heat`
- `CurrentHeatingCoolingState = 1` -> `heating`
- otherwise current action -> `idle`

### Important caveat
There is also a hidden proprietary Tado service:
- service UUID: `E44673A0-247B-4360-8A76-DB9DA69C0100`
- characteristic UUID: `E44673A0-247B-4360-8A76-DB9DA69C0101`

Observed facts:
- present on bridge and thermostat accessories
- hidden
- write-only
- not decoded yet

This may be relevant later for schedule/advanced semantics, but is not needed for current heating control MVP.

---

## Operational commands

### Check service status
```bash
sudo systemctl status tado-local-homekit.service
```

### Follow logs
```bash
sudo journalctl -u tado-local-homekit.service -f
```

### Restart service
```bash
sudo systemctl restart tado-local-homekit.service
```

### Stop service
```bash
sudo systemctl stop tado-local-homekit.service
```

### Start service
```bash
sudo systemctl start tado-local-homekit.service
```

### Verify locally on host
```bash
curl http://127.0.0.1:4407/status
curl http://127.0.0.1:4407/zones
```

### Verify from LAN
```bash
curl http://192.168.200.2:4407/status
```

---

## Redeploy / update procedure

If editing the app in the workspace and redeploying to `domo-server`:

### Local source files
- `/root/.openclaw/workspace/services/tado-homekit-server/app.py`
- `/root/.openclaw/workspace/services/tado-homekit-server/requirements.txt`
- `/root/.openclaw/workspace/services/tado-homekit-server/tado-local-homekit.service`

### Copy updated app to server
```bash
sshpass -p '***' scp /root/.openclaw/workspace/services/tado-homekit-server/app.py dani@192.168.200.2:/opt/tado-local-homekit/app.py
```

### If requirements changed
```bash
sshpass -p '***' scp /root/.openclaw/workspace/services/tado-homekit-server/requirements.txt dani@192.168.200.2:/opt/tado-local-homekit/requirements.txt
sshpass -p '***' ssh dani@192.168.200.2 '/opt/tado-local-homekit/.venv/bin/pip install -r /opt/tado-local-homekit/requirements.txt'
```

### If systemd unit changed
```bash
sshpass -p '***' scp /root/.openclaw/workspace/services/tado-homekit-server/tado-local-homekit.service dani@192.168.200.2:/tmp/tado-local-homekit.service
sshpass -p '***' ssh dani@192.168.200.2 "printf '***\n' | sudo -S mv /tmp/tado-local-homekit.service /etc/systemd/system/tado-local-homekit.service && printf '***\n' | sudo -S systemctl daemon-reload"
```

### Restart after update
```bash
sshpass -p '***' ssh dani@192.168.200.2 "printf '***\n' | sudo -S systemctl restart tado-local-homekit.service"
```

Do **not** hardcode passwords into documentation beyond placeholders.

---

## Home Assistant integration strategy

### Recommended phased approach

#### Phase 1
Use this backend as the stable local source of truth.

#### Phase 2
Expose it cleanly into Home Assistant, preferably by one of:
1. MQTT Discovery bridge (recommended first)
2. Custom Home Assistant integration (for polished UX)

### Why backend stays outside HA
- better isolation from HA restarts and upgrades
- easier debugging and dependency management
- cleaner separation between protocol logic and UX layer

### Current recommendation
- backend remains on `domo-server`
- HA consumes the backend
- do not embed the HomeKit/HAP logic directly inside HA as first implementation

---

## Known limitations / pending work

### Done
- local pairing
- local read of all four heating zones
- local write of setpoint
- confirmed propagation into official Tado app
- service deployed on permanent host

### Pending
- HA-facing integration layer (MQTT or custom component)
- support for true Tado `AUTO` / resume schedule semantics
- hot water / `BU0542969600`
- battery exposure
- long-term reconnect hardening / event subscriptions
- auth on local API (currently open on LAN)

### Important note on cloud
Cloud remains **non-goal for heating control**.

A cloud proxy may exist as Plan B if needed, but current direction is:
- local-only for heating zones
- cloud optional only for water or future fallback cases

---

## Security notes

- Pairing file is sensitive: `/opt/tado-local-homekit/tado-homekit-pairing.json`
- Keep permissions tight (`600` is appropriate)
- Current API is unauthenticated on LAN
- If exposing beyond trusted LAN, add auth before doing so

---

## Troubleshooting

### Service is up but `/zones` fails
Check:
- bridge still reachable at `192.168.200.10`
- pairing file still present
- journal logs for reconnect/pairing errors

### No zones discovered
Use:
```bash
curl -X POST http://127.0.0.1:4407/refresh
```
Then inspect logs.

### Need to verify bridge directly again
There are research artifacts in:
- `/root/.openclaw/workspace/research/tado-homekit/`

Useful files there:
- `tado-homekit-accessories.json`
- `tado-homekit-pair.py`
- `tado-homekit-list.py`

---

## Summary for future Leo

If Dani asks about Tado heating local control, the important facts are:

1. **The old Tado Internet Bridge supports HomeKit/HAP locally on port 80.**
2. **All four heating zones are reachable locally.**
3. **Local writes work and are reflected in the official Tado app.**
4. **The backend is already deployed on `domo-server:4407`.**
5. **Next product step is HA integration, not more reverse engineering.**

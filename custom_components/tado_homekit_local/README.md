# Home Assistant custom component: Tado HomeKit Local

This custom component connects Home Assistant to the local backend exposed by the Tado HomeKit Local service running on `domo-server`.

## Current intended backend
- URL: `http://192.168.200.2:4407`

## Entities exposed
- 1 climate entity per heating zone
- 1 temperature sensor per zone
- 1 humidity sensor per zone
- 1 heating-active binary sensor per zone

## Current scope
- Local heating zones only
- No hot water yet
- Includes an AUTO-like mode that re-enables heating without changing target temperature; readback still reflects local heat/off state, not guaranteed full Tado cloud schedule semantics

## Install (manual)
Copy `custom_components/tado_homekit_local` into your HA config `custom_components/` directory and restart Home Assistant.

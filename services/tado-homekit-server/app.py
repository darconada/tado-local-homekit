from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from aiohomekit.controller.ip.pairing import IpPairing
from aiohomekit.controller.ip.controller import IpController
from aiohomekit.characteristic_cache import CharacteristicCacheMemory

PAIRING_PATH = Path(os.environ.get("TADO_PAIRING_PATH", "/opt/tado-local-homekit/tado-homekit-pairing.json"))
HOST = os.environ.get("TADO_BRIDGE_HOST", "192.168.200.10")
PORT = int(os.environ.get("TADO_BRIDGE_PORT", "80"))
POLL_CACHE_SECONDS = float(os.environ.get("TADO_POLL_CACHE_SECONDS", "2"))

# HomeKit characteristic UUIDs
CHAR_NAME = "00000023-0000-1000-8000-0026BB765291"
CHAR_SERIAL = "00000030-0000-1000-8000-0026BB765291"
CHAR_CURRENT_HEATING_COOLING = "0000000F-0000-1000-8000-0026BB765291"
CHAR_TARGET_HEATING_COOLING = "00000033-0000-1000-8000-0026BB765291"
CHAR_CURRENT_TEMPERATURE = "00000011-0000-1000-8000-0026BB765291"
CHAR_TARGET_TEMPERATURE = "00000035-0000-1000-8000-0026BB765291"
CHAR_TEMP_DISPLAY_UNITS = "00000036-0000-1000-8000-0026BB765291"
CHAR_CURRENT_HUMIDITY = "00000010-0000-1000-8000-0026BB765291"
THERMOSTAT_SERVICE = "0000004A-0000-1000-8000-0026BB765291"
ACCESSORY_INFO_SERVICE = "0000003E-0000-1000-8000-0026BB765291"

SERIAL_TO_SLUG = {
    "RU2165705728": "planta1",
    "RU0572525568": "planta2",
    "RU3827043328": "atico",
    "RU3948940800": "merendero",
}
SLUG_TO_NAME = {
    "planta1": "PLANTA 1",
    "planta2": "PLANTA 2",
    "atico": "ATICO",
    "merendero": "MERENDERO",
}


class ZoneSetRequest(BaseModel):
    temperature: Optional[float] = None
    mode: Optional[str] = None  # off|heat


@dataclass
class ZoneMeta:
    slug: str
    name: str
    serial: str
    aid: int
    iids: Dict[str, int]


class TadoBridge:
    def __init__(self) -> None:
        self._controller = IpController(
            char_cache=CharacteristicCacheMemory(), zeroconf_instance=None
        )
        self._pairing: Optional[IpPairing] = None
        self._lock = asyncio.Lock()
        self._zones: Dict[str, ZoneMeta] = {}
        self._last_state_cache: tuple[float, dict[str, Any]] = (0.0, {})

    async def startup(self) -> None:
        await self._connect()
        await self._discover()

    async def shutdown(self) -> None:
        if self._pairing is not None:
            await self._pairing.close()
            self._pairing = None

    async def _connect(self) -> None:
        if not PAIRING_PATH.exists():
            raise RuntimeError(f"Pairing file not found: {PAIRING_PATH}")
        pairing_data = json.loads(PAIRING_PATH.read_text())
        pairing_data.setdefault("AccessoryIP", HOST)
        pairing_data.setdefault("AccessoryPort", PORT)
        self._pairing = IpPairing(self._controller, pairing_data)
        await self._pairing._ensure_connected()

    async def _ensure_connected(self) -> None:
        if self._pairing is None:
            await self._connect()
        else:
            await self._pairing._ensure_connected()

    async def _discover(self) -> None:
        await self._ensure_connected()
        assert self._pairing is not None
        accessories = await self._pairing.list_accessories_and_characteristics()
        zones: Dict[str, ZoneMeta] = {}
        for accessory in accessories:
            aid = accessory.get("aid")
            serial = None
            display_name = None
            iids: Dict[str, int] = {}
            for service in accessory.get("services", []):
                service_type = (service.get("type") or "").upper()
                if service_type == ACCESSORY_INFO_SERVICE:
                    for char in service.get("characteristics", []):
                        ctype = (char.get("type") or "").upper()
                        if ctype == CHAR_SERIAL:
                            serial = char.get("value")
                        elif ctype == CHAR_NAME:
                            display_name = char.get("value")
                if service_type == THERMOSTAT_SERVICE:
                    for char in service.get("characteristics", []):
                        ctype = (char.get("type") or "").upper()
                        iid = char.get("iid")
                        if ctype == CHAR_CURRENT_HEATING_COOLING:
                            iids["current_hvac"] = iid
                        elif ctype == CHAR_TARGET_HEATING_COOLING:
                            iids["target_hvac"] = iid
                        elif ctype == CHAR_CURRENT_TEMPERATURE:
                            iids["current_temp"] = iid
                        elif ctype == CHAR_TARGET_TEMPERATURE:
                            iids["target_temp"] = iid
                        elif ctype == CHAR_TEMP_DISPLAY_UNITS:
                            iids["temp_units"] = iid
                        elif ctype == CHAR_CURRENT_HUMIDITY:
                            iids["humidity"] = iid
            if serial in SERIAL_TO_SLUG and {"current_hvac", "target_hvac", "current_temp", "target_temp", "humidity"}.issubset(iids):
                slug = SERIAL_TO_SLUG[serial]
                zones[slug] = ZoneMeta(
                    slug=slug,
                    name=SLUG_TO_NAME.get(slug, display_name or serial),
                    serial=serial,
                    aid=aid,
                    iids=iids,
                )
        self._zones = zones

    async def refresh_discovery(self) -> dict[str, Any]:
        async with self._lock:
            await self._discover()
            return {slug: vars(meta) for slug, meta in self._zones.items()}

    def _format_zone_state(self, zone: ZoneMeta, raw: Dict[tuple[int, int], Dict[str, Any]]) -> Dict[str, Any]:
        def get(name: str):
            item = raw.get((zone.aid, zone.iids[name]), {})
            return item.get("value")

        target_hvac = get("target_hvac")
        current_hvac = get("current_hvac")
        current_temp = get("current_temp")
        target_temp = get("target_temp")
        humidity = get("humidity")

        if target_hvac == 0:
            hvac_mode = "off"
        elif target_hvac == 1:
            hvac_mode = "heat"
        else:
            hvac_mode = f"unknown:{target_hvac}"

        if current_hvac == 1:
            hvac_action = "heating"
        else:
            hvac_action = "idle"

        return {
            "slug": zone.slug,
            "name": zone.name,
            "serial": zone.serial,
            "aid": zone.aid,
            "current_temperature": current_temp,
            "target_temperature": target_temp,
            "humidity": humidity,
            "target_hvac_state": target_hvac,
            "current_hvac_state": current_hvac,
            "hvac_mode": hvac_mode,
            "hvac_action": hvac_action,
        }

    async def get_all_zones(self, force: bool = False) -> Dict[str, Any]:
        now = asyncio.get_running_loop().time()
        cached_at, cached = self._last_state_cache
        if not force and cached and (now - cached_at) < POLL_CACHE_SECONDS:
            return cached
        async with self._lock:
            await self._ensure_connected()
            if not self._zones:
                await self._discover()
            assert self._pairing is not None
            chars = []
            for zone in self._zones.values():
                for iid in zone.iids.values():
                    chars.append((zone.aid, iid))
            raw = await self._pairing.get_characteristics(chars)
            data = {
                slug: self._format_zone_state(zone, raw)
                for slug, zone in self._zones.items()
            }
            self._last_state_cache = (asyncio.get_running_loop().time(), data)
            return data

    async def get_zone(self, slug: str, force: bool = False) -> Dict[str, Any]:
        zones = await self.get_all_zones(force=force)
        if slug not in zones:
            raise KeyError(slug)
        return zones[slug]

    async def _read_zone_state_locked(self, zone: ZoneMeta) -> Dict[str, Any]:
        """Read one zone while assuming the caller already holds the bridge lock."""
        assert self._pairing is not None
        chars = [(zone.aid, iid) for iid in zone.iids.values()]
        raw = await self._pairing.get_characteristics(chars)
        return self._format_zone_state(zone, raw)

    async def set_zone(self, slug: str, temperature: Optional[float], mode: Optional[str]) -> Dict[str, Any]:
        async with self._lock:
            await self._ensure_connected()
            if not self._zones:
                await self._discover()
            zone = self._zones.get(slug)
            if zone is None:
                raise KeyError(slug)
            assert self._pairing is not None
            writes = []
            if mode is not None:
                mode = mode.lower()
                if mode == "off":
                    writes.append((zone.aid, zone.iids["target_hvac"], 0))
                elif mode == "heat":
                    writes.append((zone.aid, zone.iids["target_hvac"], 1))
                else:
                    raise ValueError("mode must be 'off' or 'heat'")
            if temperature is not None:
                writes.append((zone.aid, zone.iids["target_temp"], float(temperature)))
                # If setting temp and mode omitted, force heat for practical UX.
                if mode is None:
                    writes.append((zone.aid, zone.iids["target_hvac"], 1))
            if not writes:
                raise ValueError("nothing to write")
            result = await self._pairing.put_characteristics(writes)
            await asyncio.sleep(1.0)
            self._last_state_cache = (0.0, {})
            zone_state = await self._read_zone_state_locked(zone)
            return {"write_result": result, "zone": zone_state}


bridge = TadoBridge()
app = FastAPI(title="Tado HomeKit Local API", version="0.1.0")


@app.on_event("startup")
async def on_startup() -> None:
    await bridge.startup()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await bridge.shutdown()


@app.get("/status")
async def status() -> Dict[str, Any]:
    zones = await bridge.get_all_zones(force=True)
    return {
        "status": "ok",
        "bridge_host": HOST,
        "bridge_port": PORT,
        "pairing_path": str(PAIRING_PATH),
        "zones_count": len(zones),
        "zones": list(zones.keys()),
    }


@app.get("/zones")
async def zones() -> Dict[str, Any]:
    return {"zones": list((await bridge.get_all_zones()).values())}


@app.get("/zones/{slug}")
async def zone(slug: str) -> Dict[str, Any]:
    try:
        return {"zone": await bridge.get_zone(slug)}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown zone: {slug}")


@app.post("/zones/{slug}/set")
async def zone_set(slug: str, request: ZoneSetRequest) -> Dict[str, Any]:
    try:
        return await bridge.set_zone(slug, request.temperature, request.mode)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown zone: {slug}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/refresh")
async def refresh() -> Dict[str, Any]:
    data = await bridge.refresh_discovery()
    return {"discovered": data}

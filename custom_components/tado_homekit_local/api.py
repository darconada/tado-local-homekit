from __future__ import annotations

from typing import Any

from aiohttp import ClientError, ClientSession


class TadoHomeKitLocalApiError(Exception):
    """Raised when the local Tado backend cannot be reached or returns an error."""


class TadoHomeKitLocalApiClient:
    def __init__(self, session: ClientSession, host: str, port: int) -> None:
        self._session = session
        self._host = host
        self._port = port

    @property
    def base_url(self) -> str:
        return f"http://{self._host}:{self._port}"

    async def async_get_status(self) -> dict[str, Any]:
        return await self._async_request("GET", "/status")

    async def async_get_zones(self) -> list[dict[str, Any]]:
        payload = await self._async_request("GET", "/zones")
        return payload.get("zones", [])

    async def async_set_zone(
        self, slug: str, *, temperature: float | None = None, mode: str | None = None
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if temperature is not None:
            payload["temperature"] = float(temperature)
        if mode is not None:
            payload["mode"] = mode
        return await self._async_request("POST", f"/zones/{slug}/set", json=payload)

    async def _async_request(
        self, method: str, path: str, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        try:
            async with self._session.request(
                method, f"{self.base_url}{path}", json=json
            ) as response:
                if response.status >= 400:
                    body = await response.text()
                    raise TadoHomeKitLocalApiError(
                        f"{method} {path} failed: {response.status} {body}"
                    )
                return await response.json()
        except (ClientError, TimeoutError) as err:
            raise TadoHomeKitLocalApiError(str(err)) from err

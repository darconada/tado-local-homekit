from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TadoHomeKitLocalApiClient, TadoHomeKitLocalApiError
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN


class TadoHomeKitLocalCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    def __init__(
        self,
        hass: HomeAssistant,
        client: TadoHomeKitLocalApiClient,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        self.client = client
        super().__init__(
            hass,
            logger=hass.data[DOMAIN]["logger"],
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            zones = await self.client.async_get_zones()
            return {zone["slug"]: zone for zone in zones}
        except TadoHomeKitLocalApiError as err:
            raise UpdateFailed(str(err)) from err

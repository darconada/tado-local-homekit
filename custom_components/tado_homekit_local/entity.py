from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class TadoHomeKitLocalEntity(CoordinatorEntity):
    def __init__(self, coordinator, client, slug: str) -> None:
        super().__init__(coordinator)
        self._client = client
        self._slug = slug

    @property
    def zone(self) -> dict:
        return self.coordinator.data[self._slug]

    @property
    def device_info(self) -> DeviceInfo:
        zone = self.zone
        return DeviceInfo(
            identifiers={(DOMAIN, zone["serial"])},
            name=zone["name"],
            manufacturer="tado",
            model="Smart Thermostat",
            serial_number=zone["serial"],
            configuration_url=f"{self._client.base_url}/zones/{self._slug}",
        )

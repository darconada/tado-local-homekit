from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TadoHomeKitLocalRuntime
from .const import DOMAIN
from .entity import TadoHomeKitLocalEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: TadoHomeKitLocalRuntime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        TadoHomeKitLocalHeatingBinarySensor(runtime.coordinator, runtime.client, slug)
        for slug in runtime.coordinator.data
    )


class TadoHomeKitLocalHeatingBinarySensor(TadoHomeKitLocalEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.HEAT

    def __init__(self, coordinator, client, slug: str) -> None:
        super().__init__(coordinator, client, slug)
        self._attr_unique_id = f"{self.zone['serial']}_heating_active"

    @property
    def name(self) -> str:
        return f"{self.zone['name']} Heating Active"

    @property
    def is_on(self) -> bool:
        return self.zone["hvac_action"] == "heating"

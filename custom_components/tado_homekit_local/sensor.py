from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import TadoHomeKitLocalRuntime
from .const import DOMAIN
from .entity import TadoHomeKitLocalEntity


@dataclass(frozen=True)
class TadoZoneSensorDescription(SensorEntityDescription):
    value_key: str = ""


SENSORS = (
    TadoZoneSensorDescription(
        key="current_temperature",
        translation_key="current_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_key="current_temperature",
    ),
    TadoZoneSensorDescription(
        key="humidity",
        translation_key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_key="humidity",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime: TadoHomeKitLocalRuntime = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for slug in runtime.coordinator.data:
        for description in SENSORS:
            entities.append(
                TadoHomeKitLocalSensor(runtime.coordinator, runtime.client, slug, description)
            )
    async_add_entities(entities)


class TadoHomeKitLocalSensor(TadoHomeKitLocalEntity, SensorEntity):
    entity_description: TadoZoneSensorDescription

    def __init__(self, coordinator, client, slug: str, description: TadoZoneSensorDescription) -> None:
        super().__init__(coordinator, client, slug)
        self.entity_description = description
        self._attr_unique_id = f"{self.zone['serial']}_{description.key}"

    @property
    def name(self) -> str:
        suffix = "Temperature" if self.entity_description.key == "current_temperature" else "Humidity"
        return f"{self.zone['name']} {suffix}"

    @property
    def native_value(self):
        return self.zone[self.entity_description.value_key]

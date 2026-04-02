from __future__ import annotations

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature
from homeassistant.components.climate.const import HVACAction, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
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
        TadoHomeKitLocalClimate(runtime.coordinator, runtime.client, slug)
        for slug in runtime.coordinator.data
    )


class TadoHomeKitLocalClimate(TadoHomeKitLocalEntity, ClimateEntity):
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.AUTO, HVACMode.OFF]
    _attr_min_temp = 5.0
    _attr_max_temp = 25.0
    _attr_target_temperature_step = 0.1
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, coordinator, client, slug: str) -> None:
        super().__init__(coordinator, client, slug)
        self._attr_unique_id = f"{self.zone['serial']}_climate"

    @property
    def name(self) -> str:
        return self.zone["name"]

    @property
    def current_temperature(self):
        return self.zone["current_temperature"]

    @property
    def target_temperature(self):
        return self.zone["target_temperature"]

    @property
    def hvac_mode(self) -> HVACMode:
        mode = self.zone["hvac_mode"]
        if mode == "off":
            return HVACMode.OFF
        # Backend cannot distinguish true schedule from resumed heating yet;
        # we surface AUTO-capable UX via set_hvac_mode even though readback remains heat/off.
        return HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction:
        if self.zone["hvac_mode"] == "off":
            return HVACAction.OFF
        return HVACAction.HEATING if self.zone["hvac_action"] == "heating" else HVACAction.IDLE

    async def async_set_temperature(self, **kwargs) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        await self._client.async_set_zone(self._slug, temperature=temperature)
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.HEAT:
            mode = "heat"
        elif hvac_mode == HVACMode.AUTO:
            mode = "auto"
        else:
            mode = "off"
        await self._client.async_set_zone(self._slug, mode=mode)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_turn_on(self) -> None:
        await self.async_set_hvac_mode(HVACMode.HEAT)

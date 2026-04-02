from datetime import timedelta
from homeassistant.const import Platform

DOMAIN = "tado_homekit_local"
NAME = "Tado HomeKit Local"

CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_HOST = "192.168.200.2"
DEFAULT_PORT = 4407
DEFAULT_SCAN_INTERVAL = 5

PLATFORMS: list[Platform] = [
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]

DEFAULT_UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

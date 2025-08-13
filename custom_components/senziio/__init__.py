"""Senziio integration."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from homeassistant.components import mqtt
from homeassistant.components.mqtt import async_publish, async_subscribe
from homeassistant.config_entries import ConfigEntry, ConfigType
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .entity import DOMAIN
from .senziio import Senziio, SenziioMQTT
from .utils import init_resource, register_static_path

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.EVENT,
    Platform.UPDATE,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Senziio device from a config entry."""

    # Make sure MQTT integration is enabled and the client is available.
    if not await mqtt.async_wait_for_mqtt_client(hass):
        _LOGGER.error("MQTT integration is not available")
        return False

    device_id = entry.data["serial-number"]
    device_model = entry.data["model"]
    device = Senziio(device_id, device_model, mqtt=SenziioHAMQTT(hass))

    if info := await device.get_info():
        hass.config_entries.async_update_entry(entry, data=info)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = device

    # forward setup to all platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Setup senziio frontend resources."""
    path = Path(__file__).parent / "frontend"
    version = getattr(hass.data["integrations"][DOMAIN], "version", 0)
    register_static_path(hass.http.app, "/senziio/senziio-card.js", path / "senziio-card.js")
    await init_resource(hass, "/senziio/senziio-card.js", str(version))
    return True


class SenziioHAMQTT(SenziioMQTT):
    """Senziio MQTT interface using available integration."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize MQTT interface for Senziio devices."""
        self._hass = hass

    async def publish(self, topic: str, payload: str) -> None:
        """Publish to topic with a payload."""
        try:
            return await async_publish(self._hass, topic, payload)
        except HomeAssistantError as error:
            _LOGGER.error("Could not publish to MQTT topic")
            raise MQTTError from error

    async def subscribe(self, topic: str, callback: Callable) -> Callable:
        """Subscribe to topic with a callback."""
        try:
            return await async_subscribe(self._hass, topic, callback)
        except HomeAssistantError as error:
            _LOGGER.error("Could not subscribe to MQTT topic")
            raise MQTTError from error


class MQTTError(HomeAssistantError):
    """Error to indicate that required MQTT integration is not enabled."""

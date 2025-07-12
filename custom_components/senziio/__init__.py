"""Senziio integration."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from senziio import Senziio, SenziioMQTT

from homeassistant.components import mqtt
from homeassistant.components.mqtt import async_publish, async_subscribe
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from homeassistant.components.frontend import (
    async_register_built_in_panel,
    add_extra_js_url,
)

from .entity import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

PANEL_JS = "/senziio-panel/panel-senziio-overview.js"
PANEL_PATH = "senziio-overview"


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

    # register the panel
    await register_panel(hass)

    return True


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    static_dir = Path(hass.config.path("custom_components/senziio/frontend"))

    try:
        # Home Assistant >= 2024.6
        from homeassistant.components.http import StaticPathConfig
        await hass.http.async_register_static_paths([
            StaticPathConfig("/senziio-panel", str(static_dir), False)
        ])
    except ImportError:
        # Fallback for older HA versions
        # http://192.168.1.41:8123/senziio-panel/panel-senziio-overview.js
        hass.http.register_static_path(
            "/senziio-panel",
            str(static_dir),
            False
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


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


async def register_panel(hass):
    """Register the Senziio side panel."""
    add_extra_js_url(hass, PANEL_JS)

    async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title="Senziio Overview",
        sidebar_icon="mdi:thermometer",
        frontend_url_path=PANEL_PATH,
        config={
            "_panel_custom": {
                "name": PANEL_PATH,
                "embed_iframe": False,
                "trust_external": False,
                "module_url": PANEL_JS,
            }
        },
        require_admin=False,
    )

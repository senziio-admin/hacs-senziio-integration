"""Senziio binary sensor entities."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.components.mqtt import async_subscribe
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.json import json_loads_object

from custom_components.senziio import Senziio

from .entity import DOMAIN, SenziioEntity


@dataclass(frozen=True, kw_only=True)
class SenziioBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Class describing Senziio sensor entities."""

    value_key: str


BINARY_SENSOR_DESCRIPTIONS: tuple[SenziioBinarySensorEntityDescription, ...] = (
    SenziioBinarySensorEntityDescription(
        name="Presence",
        key="presence",
        value_key="presence",
        translation_key="presence",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
    ),
    SenziioBinarySensorEntityDescription(
        name="Motion",
        key="motion",
        value_key="motion",
        translation_key="motion",
        device_class=BinarySensorDeviceClass.MOTION,
    ),
    SenziioBinarySensorEntityDescription(
        name="Radar",
        key="radar",
        value_key="radar",
        translation_key="radar",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
    ),
    SenziioBinarySensorEntityDescription(
        name="Beacon",
        key="beacon",
        value_key="beacon",
        translation_key="beacon",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
    ),
    SenziioBinarySensorEntityDescription(
        name="PIR",
        key="pir",
        value_key="pir",
        translation_key="pir",
        device_class=BinarySensorDeviceClass.MOTION,
    ),
    SenziioBinarySensorEntityDescription(
        name="Camera",
        key="camera",
        value_key="camera",
        translation_key="camera",
        device_class=BinarySensorDeviceClass.OCCUPANCY,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Senziio entities."""
    device = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            SenziioBinarySensorEntity(hass, entity_description, entry, device)
            for entity_description in BINARY_SENSOR_DESCRIPTIONS
        ]
    )


class SenziioBinarySensorEntity(SenziioEntity, BinarySensorEntity):
    """Senziio binary sensor entity."""

    def __init__(
        self,
        hass: HomeAssistant,
        entity_description: SenziioBinarySensorEntityDescription,
        entry: ConfigEntry,
        device: Senziio,
    ) -> None:
        """Initialize entity."""
        super().__init__(entry)
        self.entity_id = f"binary_sensor.senziio_{entity_description.key}_{device.id}"
        self.entity_description = entity_description
        self._attr_unique_id = f"{device.id}_{entity_description.key}"
        self._hass = hass
        self._dt_topic = device.entity_topic(entity_description.key)

    async def async_added_to_hass(self) -> None:
        """Subscribe to MQTT data event."""

        @callback
        def message_received(message):
            """Handle new MQTT messages."""
            data = json_loads_object(message.payload)
            self._attr_is_on = data.get(self.entity_description.value_key) is True
            self.async_write_ha_state()

        await async_subscribe(self._hass, self._dt_topic, message_received, 1)

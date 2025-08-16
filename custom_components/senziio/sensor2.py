"""Support for Senziio API."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.mqtt import async_subscribe
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONCENTRATION_PARTS_PER_MILLION,
    LIGHT_LUX,
    PERCENTAGE,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.json import json_loads_object

from custom_components.senziio import Senziio

from .entity import DOMAIN, SenziioEntity


@dataclass(frozen=True, kw_only=True)
class SenziioSensorEntityDescription(SensorEntityDescription):
    """Class describing Senziio sensor entities."""

    value_key: str


SENSOR_DESCRIPTIONS: tuple[SenziioSensorEntityDescription, ...] = (
    SenziioSensorEntityDescription(
        name="CO2",
        key="co2",
        value_key="co2",
        translation_key="co2",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CO2,
        native_unit_of_measurement=CONCENTRATION_PARTS_PER_MILLION,
    ),
    SenziioSensorEntityDescription(
        name="Illuminance",
        key="illuminance",
        value_key="light_level",
        translation_key="illuminance",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=LIGHT_LUX,
        suggested_display_precision=0,
    ),
    SenziioSensorEntityDescription(
        name="Temperature",
        key="temperature",
        value_key="temperature",
        translation_key="temperature",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
    ),
    SenziioSensorEntityDescription(
        name="Humidity",
        key="humidity",
        value_key="humidity",
        translation_key="humidity",
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=0,
    ),
    SenziioSensorEntityDescription(
        name="Atmospheric Pressure",
        key="atm-pressure",
        value_key="pressure",
        translation_key="atmospheric-pressure",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.PRESSURE,
        native_unit_of_measurement=UnitOfPressure.HPA,
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
            SenziioSensorEntity(hass, entity_description, entry, device)
            for entity_description in SENSOR_DESCRIPTIONS
        ] + [EventSensor(hass, entry, device)]
    )


class SenziioSensorEntity(SenziioEntity, SensorEntity):
    """Senziio binary sensor entity."""

    def __init__(
        self,
        hass: HomeAssistant,
        entity_description: SenziioSensorEntityDescription,
        entry: ConfigEntry,
        device: Senziio,
    ) -> None:
        """Initialize entity."""
        super().__init__(entry)
        self.entity_id = f"sensor.senziio_{entity_description.key}_{device.id}"
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
            self._attr_native_value = data.get(self.entity_description.value_key)
            self.async_write_ha_state()

        await async_subscribe(self._hass, self._dt_topic, message_received, 1)


###############################################


from typing import Any, Tuple
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util import dt as dt_util
import asyncio
import logging

_LOGGER = logging.getLogger(__name__)


class EventSensor(SenziioEntity, SensorEntity):
    """Last Senziio event: single custom Logbook row, no default rows."""

    _attr_has_entity_name = True
    _attr_name = "Event"
    # IMPORTANT: no TIMESTAMP device class (we keep state constant)
    # _attr_device_class = SensorDeviceClass.TIMESTAMP  # <-- leave this OUT

    # Show custom row inside the entity dialog (clickable)
    _SHOW_CUSTOM_ROW_IN_ENTITY_LOGBOOK = True

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, device: Senziio) -> None:
        super().__init__(entry)
        self._hass = hass
        self._device = device
        self.entity_id = f"sensor.senziio_event_{device.id}"
        self._attr_unique_id = f"{device.id}_event"
        self._event_topic = device.entity_topic("event")

        # Keep a constant state so Logbook never adds "Changed to ..." lines
        self._attr_native_value = "idle"   # constant string (any constant is fine)
        self._attr_extra_state_attributes: dict[str, Any] = {}

        self._unsub = None
        self._last_sig: Tuple[Any, Any, Any] | None = None  # simple de-dupe

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attr_extra_state_attributes

    async def _exclude_when_registered(self) -> None:
        """After the entity is registered, exclude it from Logbook (belt & suspenders)."""
        reg = er.async_get(self._hass)
        for _ in range(60):
            entry = reg.async_get(self.entity_id)
            if entry:
                reg.async_update_entity_options(self.entity_id, "logbook", {"exclude": True})
                _LOGGER.debug("EventSensor: logbook exclude set for %s", self.entity_id)
                return
            await asyncio.sleep(0.05)
        _LOGGER.warning("EventSensor: could not set logbook exclude for %s", self.entity_id)

    async def async_added_to_hass(self) -> None:
        self._hass.async_create_task(self._exclude_when_registered())

        @callback
        def _message_received(message):
            try:
                data = json_loads_object(message.payload)
            except Exception:
                return

            event_id = data.get("event_id")
            event_name = str(data.get("event_name") or "")
            payload = data.get("data")
            if not event_name:
                return

            # de-dupe back-to-back identical messages
            sig = (event_id, event_name, payload)
            if sig == self._last_sig:
                return
            self._last_sig = sig

            # 1) Update ATTRIBUTES ONLY (state stays "idle" -> no default logbook line)
            now_iso = dt_util.utcnow().isoformat(timespec="seconds")
            self._attr_extra_state_attributes = {
                "event_name": event_name,
                "event_id": event_id,
                "data": payload,
                "received": now_iso,
            }
            self.async_write_ha_state()  # attribute-only update

            # 2) One custom Logbook row (appears in entity dialog & global logbook)
            msg = f"{event_name}: {'' if payload is None else str(payload)}".rstrip(': ')
            service_data = {
                "name": "Event",
                "message": msg,
                "domain": "homeassistant",
            }
            if self._SHOW_CUSTOM_ROW_IN_ENTITY_LOGBOOK:
                service_data["entity_id"] = self.entity_id  # clickable & visible in entity dialog

            self._hass.async_create_task(
                self._hass.services.async_call("logbook", "log", service_data, blocking=False)
            )

        self._unsub = await async_subscribe(self._hass, self._event_topic, _message_received, 1)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

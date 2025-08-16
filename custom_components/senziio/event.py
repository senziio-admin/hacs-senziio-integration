from __future__ import annotations
import logging, re
from typing import Any, Tuple

from homeassistant.components.event import EventEntity
from homeassistant.components.mqtt import async_subscribe
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.json import json_loads_object

from .entity import DOMAIN, MANUFACTURER
from .senziio import Senziio

_LOGGER = logging.getLogger(__name__)

SENZIIO_AUTOMATION_EVENT = "senziio_event"  # custom bus event
BASE_TYPES = {"intrusionEvent", "co2Event", "hotspotEvent", "beaconEvent"}


class SenziioEvent(EventEntity):
    _attr_has_entity_name = True
    _attr_name = "Event"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass: HomeAssistant, device: Senziio, entry: ConfigEntry) -> None:
        self._hass = hass
        self._device = device
        self._entry = entry
        self._attr_unique_id = f"{device.id}_events"
        self._attr_device_info = {"identifiers": {(DOMAIN, device.id)}, "manufacturer": MANUFACTURER}
        self._event_types = set(BASE_TYPES)
        self._attr_event_types = sorted(self._event_types)
        self._unsub = None
        self._last_sig: Tuple[Any, Any, Any] | None = None  # de-duplication key

    def _allow_and_normalize(self, event_name: str) -> tuple[str, dict]:
        extra = {"raw_event_name": event_name}
        if event_name in self._event_types:
            return event_name, extra
        m = re.search(r"(\d+)$", event_name)
        if m:
            base = event_name[: -len(m.group(1))]
            if base in self._event_types:
                extra["index"] = int(m.group(1))
                return base, extra
        # new type
        self._event_types.add(event_name)
        self._attr_event_types = sorted(self._event_types)
        return event_name, extra

    async def async_added_to_hass(self) -> None:
        topic = self._device.entity_topic("event")

        @callback
        def _on_msg(message):
            try:
                data = json_loads_object(message.payload)
            except Exception:
                _LOGGER.warning("SenziioEvent: bad payload: %s", message.payload)
                return

            event_id = data.get("event_id")
            event_name = str(data.get("event_name") or "")
            payload = data.get("data")
            if not event_name:
                return

            # de-duplicate messages
            sig = (event_id, event_name, payload)
            if sig == self._last_sig:
                return
            self._last_sig = sig

            # update entity
            event_type, extra = self._allow_and_normalize(event_name)
            extra.update({"event_id": event_id, "data": payload})
            self._trigger_event(event_type, extra)
            self.async_write_ha_state()

            # event for automations
            message_text = f"{event_name}: {'' if payload is None else str(payload)}".rstrip(": ")
            self.hass.bus.async_fire(
                SENZIIO_AUTOMATION_EVENT,
                {
                    "name": "Event",
                    "event_id": event_id,
                    "event_type": event_type,
                    "event_name": event_name,
                    "data": payload,
                    "message": message_text,
                    "entity_id": self.entity_id,
                    "device_id": self._device.id,
                    "domain": "event",
                },
            )

        self._unsub = await async_subscribe(self._hass, topic, _on_msg, 1)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    device: Senziio = hass.data[DOMAIN][entry.entry_id]
    add([SenziioEvent(hass, device, entry)], update_before_add=False)


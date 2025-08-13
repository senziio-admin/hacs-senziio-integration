# custom_components/senziio/event.py
"""Senziio event entity (discrete alerts with history)."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory
from homeassistant.components.mqtt import async_subscribe
from homeassistant.util.json import json_loads_object
from homeassistant.util import dt as dt_util
from homeassistant.components.logbook import EVENT_LOGBOOK_ENTRY
from homeassistant.helpers import entity_registry as er

from .entity import DOMAIN, MANUFACTURER
from .senziio import Senziio

_LOGGER = logging.getLogger(__name__)

EVENT_TYPES = ["intrusionEvent", "co2Event", "hotspotEvent", "beaconEvent"]


class SenziioEvent(EventEntity):
    """Shows the last Senziio event, with attributes for details."""

    _attr_has_entity_name = True
    _attr_name = "Event"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_event_types = EVENT_TYPES

    def __init__(self, hass: HomeAssistant, device: Senziio, entry: ConfigEntry) -> None:
        self._hass = hass
        self._device = device
        self._entry = entry
        self._attr_unique_id = f"{device.id}_events"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device.id)},
            "manufacturer": MANUFACTURER,
        }

        self._last_ts: str | None = None      # ISO timestamp string (state)
        self._last_type: str | None = None    # event type
        self._attrs: dict[str, Any] = {}
        self._seq = 0
        self._unsub = None

    @property
    def state(self) -> str | None:
        """State is the timestamp of the last event (ISO 8601)."""
        return self._last_ts

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose event_type and additional data."""
        return self._attrs

    async def async_added_to_hass(self) -> None:
        """Subscribe to the 'event' entity topic."""

        # exclude entity from logging the default logbook line (avoid duplicates)
        reg = er.async_get(self.hass)
        if (ent := reg.async_get(self.entity_id)):
            if not ent.options.get("logbook", {}).get("exclude"):
                reg.async_update_entity_options(self.entity_id, "logbook", {"exclude": True})

        topic = self._device.entity_topic("event")

        @callback
        def _message_received(message):
            try:
                data = json_loads_object(message.payload)
            except Exception:  # bad JSON; ignore
                _LOGGER.warning("Bad event payload: %s", message.payload)
                return

            event_id = data.get("event_id")
            event_name = data.get("event_name")
            payload = data.get("data")

            if not event_name:
                return

            # State must be a timestamp; details go in attributes
            now = dt_util.utcnow().isoformat(timespec="seconds")
            self._last_ts = now
            self._last_type = str(event_name)
            self._seq += 1

            self._attrs = {
                "event_type": self._last_type,
                "event_id": event_id,
                "data": payload,
                "sequence": self._seq,  # store repeated events
                "received": now,
            }

            self.async_write_ha_state()

            payload_text = "" if payload is None else str(payload)
            log_line = f"{event_name}: {payload_text}"

            self._hass.bus.async_fire(
                EVENT_LOGBOOK_ENTRY,
                {
                    "name": "Event",              # blue label text
                    "message": log_line,          # e.g. "intrusionEvent2: bar" or "fooEvent: "
                    "entity_id": self.entity_id,
                    "domain": DOMAIN,
                    # "icon": "mdi:alert"         # optional custom icon
                },
            )

        self._unsub = await async_subscribe(self._hass, topic, _message_received, 1)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    device: Senziio = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SenziioEvent(hass, device, entry)], update_before_add=False)

"""Senziio event entity (discrete alerts with history)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.components.logbook import EVENT_LOGBOOK_ENTRY
from homeassistant.components.mqtt import async_subscribe
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util
from homeassistant.util.json import json_loads_object

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

        self._last_ts: str | None = None
        self._last_type: str | None = None
        self._attrs: dict[str, Any] = {}
        self._seq = 0
        self._unsub = None

    @property
    def state(self) -> str | None:
        """State is the timestamp of the last event."""
        return self._last_ts

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose event_type and additional data."""
        return self._attrs

    async def async_added_to_hass(self) -> None:
        """Subscribe to the 'event' topic and push custom log line."""
        topic = self._device.entity_topic("event")

        @callback
        def _message_received(message):
            try:
                data = json_loads_object(message.payload)
            except Exception:
                _LOGGER.warning("Bad event payload: %s", message.payload)
                return

            event_id = data.get("event_id")
            event_name = data.get("event_name")
            payload = data.get("data")

            if not event_name:
                return

            # Update entity state/attributes for history
            now = dt_util.utcnow().isoformat(timespec="seconds")
            self._last_ts = now
            self._last_type = str(event_name)
            self._seq += 1
            self._attrs = {
                "event_type": self._last_type,
                "event_id": event_id,
                "data": payload,
                "sequence": self._seq,
                "received": now,
            }
            self.async_write_ha_state()

            # One clean Logbook line (no "triggered by action …")
            msg = f"{event_name}: {'' if payload is None else str(payload)}".rstrip(": ")
            self.hass.bus.async_fire(
                EVENT_LOGBOOK_ENTRY,
                {
                    "name": "Event",             # blue label
                    "message": msg,              # e.g. "intrusionEvent3: foo bar"
                    "entity_id": self.entity_id, # click opens this entity
                    "domain": DOMAIN,
                },
            )

        self._unsub = await async_subscribe(self._hass, topic, _message_received, 1)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None


async def _exclude_from_logbook_when_registered(
    hass: HomeAssistant, unique_id: str
) -> None:
    """Wait until the entity is in the registry, then exclude it from Logbook."""
    reg = er.async_get(hass)

    for _ in range(20):  # 2 seconds worst case
        ent_id = reg.async_get_entity_id("event", DOMAIN, unique_id)
        if ent_id:
            ent = reg.async_get(ent_id)
            current = ent.options.get("logbook", {})
            if not current.get("exclude"):
                reg.async_update_entity_options(ent_id, "logbook", {"exclude": True})
                _LOGGER.debug("SenziioEvent: set logbook exclude for %s", ent_id)
            return
        await asyncio.sleep(0.1)

    _LOGGER.debug(
        "SenziioEvent: could not resolve entity_id for unique_id=%s to set logbook exclude",
        unique_id,
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Register the entity and hide the default logbook line."""
    device: Senziio = hass.data[DOMAIN][entry.entry_id]
    ent = SenziioEvent(hass, device, entry)
    async_add_entities([ent], update_before_add=False)

    # Ensure ONLY custom Logbook line is shown (disable default one)
    unique_id = ent.unique_id  # f"{device.id}_events"
    hass.async_create_task(_exclude_from_logbook_when_registered(hass, unique_id))

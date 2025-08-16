from __future__ import annotations
from typing import Callable
from homeassistant.core import HomeAssistant, Event, callback

DOMAIN = "senziio"
SENZIIO_AUTOMATION_EVENT = "senziio_event"


@callback
def async_describe_events(
    hass: HomeAssistant,
    async_describe_event: Callable[[str, str, Callable[[Event], dict]], None],
) -> None:
    @callback
    def _describe(evt: Event) -> dict:
        d = evt.data or {}
        name = d.get("event_name") or d.get("name") or "Event"

        msg = d.get("message")
        if msg is None:
            nm = d.get("event_name") or ""
            dat = d.get("data")
            msg = f"{nm}: {dat}" if dat not in (None, "") else nm

        return {
            "name": name,
            "message": msg,
            "entity_id": d.get("entity_id"),
            "domain": "event",
        }

    async_describe_event(DOMAIN, SENZIIO_AUTOMATION_EVENT, _describe)

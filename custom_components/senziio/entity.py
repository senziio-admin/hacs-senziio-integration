"""Senziio base entity."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

DOMAIN = "senziio"
MANUFACTURER = "Senziio"


class SenziioEntity(Entity):
    """Representation of a Senziio entity."""

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize base entity."""
        self.entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        dev_reg = dr.async_get(self.hass)
        dev_entry = dev_reg.async_get_device(
            identifiers={(DOMAIN, self.entry.data["serial-number"])}
        )
        if dev_entry:
            sw_version = dev_entry.sw_version
            serial_number = dev_entry.serial_number
            connections = dev_entry.connections or set()
        else:
            sw_version = self.entry.data.get("fw-version")
            serial_number = self.entry.data.get("serial-number")
            mac = self.entry.data.get("mac-address")
            connections = {(dr.CONNECTION_NETWORK_MAC, mac)} if mac else set()

        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.data["serial-number"])},
            name=self.entry.title,
            manufacturer=MANUFACTURER,
            model=self.entry.data["model"],
            sw_version=sw_version,
            serial_number=serial_number,
            connections=connections,
        )

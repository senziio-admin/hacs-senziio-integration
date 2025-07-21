"""Senziio firmware update entity."""

from __future__ import annotations

import logging

from homeassistant.components.update import (
    UpdateEntity,
    UpdateEntityFeature,
    UpdateDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import EntityCategory

from .entity import DOMAIN, MANUFACTURER
from .senziio import Senziio

logger = logging.getLogger(__name__)


class SenziioUpdate(UpdateEntity):
    """Update entity for Senziio devices."""

    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_entity_category = EntityCategory.CONFIG
    _attr_supported_features = (
        UpdateEntityFeature.INSTALL |
        UpdateEntityFeature.PROGRESS
    )

    def __init__(self, device: Senziio, entry: ConfigEntry) -> None:
        self._device = device
        self._entry = entry
        self._attr_unique_id = f"{device.id}_update"
        self._identifiers = {(DOMAIN, device.id)}

        self._installed: str | None = None
        self._latest: str | None = None
        self._progress: int | None = None
        self._installed_saved: str | None = None

        self._attr_device_info = {
            "identifiers": self._identifiers,
            "manufacturer": MANUFACTURER,
        }

    @property
    def installed_version(self) -> str | None:
        return self._installed

    @property
    def latest_version(self) -> str | None:
        return self._latest

    @property
    def in_progress(self) -> bool | None:
        return self._progress is not None

    @property
    def update_percentage(self) -> int | None:
        """0-100 while flashing, None otherwise."""
        return self._progress

    @property
    def progress(self) -> int | None:
        return self._progress

    async def async_install(self, version=None, backup=False, **kwargs):
        """Triggered by the INSTALL button in the UI."""
        self._progress = 0
        self.async_write_ha_state()

    async def _handle_firmware_update(
        self,
        current: str,
        latest: str | None,
        progress: int | None,
    ) -> None:
        """Handle firmware update flow.

        TODO: topic not implemented, logic not defined.
        """
        changed = False

        if current and current != self._installed:
            self._installed = current
            changed = True

        if latest and latest != self._latest:
            self._latest = latest
            changed = True

        if progress is not None:
            pct = int(progress)
            if pct != self._progress:
                self._progress = pct
                changed = True
        else:
            if self._progress is not None:
                self._progress = None
                changed = True

        if changed:
            self.async_write_ha_state()

            # If no update is running AND the reported version differs from what
            # we previously have stored, write it into device registry
            if progress is None and current and current != self._installed_saved:
                await self._save_firmware_version_to_registry(cur)
                self._installed_saved = current

    async def _handle_device_info_update(
        self,
        firmware_version: str | None,
        serial_number: str | None,
        mac: int | None,
    ) -> None:
        """Handle messages to update device info in registry."""
        if firmware_version:
            self._installed = firmware_version
            self._latest = firmware_version
            await self._save_firmware_version_to_registry(firmware_version)
        if serial_number:
            await self._save_serial_number_to_registry(serial_number)
        if mac:
            await self._save_mac_to_registry(mac)
        self.async_write_ha_state()

    async def _save_firmware_version_to_registry(self, firmware_version: str) -> None:
        dev_reg = dr.async_get(self.hass)
        dev_entry = dev_reg.async_get_device(self._identifiers)
        if dev_entry and dev_entry.sw_version != firmware_version:
            logger.debug(
                "Updating Device Registry firmware version from %s to %s",
                dev_entry.sw_version, firmware_version
            )
            dev_reg.async_update_device(dev_entry.id, sw_version=firmware_version)

    async def _save_serial_number_to_registry(self, serial_number: str) -> None:
        dev_reg = dr.async_get(self.hass)
        dev_entry = dev_reg.async_get_device(self._identifiers)
        if dev_entry and dev_entry.serial_number != serial_number:
            logger.debug(
                "Updating Device Registry serial number from %s to %s",
                dev_entry.serial_number, serial_number
            )
            dev_reg.async_update_device(dev_entry.id, serial_number=serial_number)

    async def _save_mac_to_registry(self, mac: str) -> None:
        dev_reg = dr.async_get(self.hass)
        dev_entry = dev_reg.async_get_device(self._identifiers)
        if dev_entry is None:
            return

        conns = {c for c in dev_entry.connections
                if c[0] != dr.CONNECTION_NETWORK_MAC}
        conns.add((dr.CONNECTION_NETWORK_MAC, mac))

        if conns == dev_entry.connections:
            return

        logger.debug(
            "Updating Device Registry MAC from %s to %s",
            next((c[1] for c in dev_entry.connections
                if c[0] == dr.CONNECTION_NETWORK_MAC), "none"),
            mac,
        )

        await dev_reg.async_update_device(
            dev_entry.id,
            new_connections=conns,
        )

        # also update mac in config entry
        new_data = {**self._entry.data, "mac-address": mac}
        self.hass.config_entries.async_update_entry(self._entry, data=new_data)

    async def async_added_to_hass(self) -> None:
        dev_reg = dr.async_get(self.hass)
        dev_entry = dev_reg.async_get_device(self._identifiers)
        if dev_entry and dev_entry.sw_version:
            self._installed = dev_entry.sw_version
            self._latest = dev_entry.sw_version
            self._installed_saved = dev_entry.sw_version
            self.async_write_ha_state()


async def async_setup_entry(hass, entry, async_add_entities):
    """Create the entity and hook it to firmware-info messages."""
    device: Senziio = hass.data["senziio"][entry.entry_id]
    entity = SenziioUpdate(device, entry)
    async_add_entities([entity])
    await device.listen_device_info_updates(entity._handle_device_info_update)

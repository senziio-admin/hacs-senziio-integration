"""Senziio test fixtures."""

import pytest

from custom_components.senziio.entity import DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry

from . import A_DEVICE_ID, A_FRIENDLY_NAME, ENTRY_DATA


@pytest.fixture
def config_entry():
    """Mock a Senziio device config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title=A_FRIENDLY_NAME,
        unique_id=A_DEVICE_ID,
        data=ENTRY_DATA,
    )


import pytest
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

@pytest.fixture
async def setup_integration(hass: HomeAssistant):
    """Set up the integration for testing."""
    entry = MockConfigEntry(
        domain="senziio",
        data={
            "friendly_name": "Test Senziio",
            "model": "Test Model",
            "unique_id": "123456"
        }
    )
    entry.add_to_hass(hass)
    await async_setup_component(hass, "mqtt", {"mqtt": {"broker": "mock-broker"}})
    await hass.async_block_till_done()
    await async_setup_component(hass, "senziio", {"senziio": {}})
    await hass.async_block_till_done()
    return entry
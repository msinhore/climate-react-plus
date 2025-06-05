# File: custom_components/climate_react_plus/switch.py

from __future__ import annotations
from typing import Any
import logging

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.const import CONF_NAME

from .climate_react_switch import ClimateReactSwitch
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Climate React Plus switch helpers from a config entry."""

    zone = entry.data[CONF_NAME]
    entity = ClimateReactSwitch(hass, zone)

    async_add_entities([entity])

# File: custom_components/climate_react_plus/__init__.py

import logging
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import config_validation as cv
import voluptuous as vol

from .const import DOMAIN
from .climate_react import ClimateReactController

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                cv.string: vol.Schema(
                    {
                        vol.Required("climate_entity"): cv.entity_id,
                        vol.Required("temperature_sensor"): cv.entity_id,
                        vol.Optional("enabled_entity"): cv.entity_id,
                        vol.Optional("min_temp_entity"): cv.entity_id,
                        vol.Optional("max_temp_entity"): cv.entity_id,
                        vol.Optional("setpoint_entity"): cv.entity_id,
                        vol.Optional("mode_entity"): cv.entity_id,
                        vol.Optional("fan_entity"): cv.entity_id,
                    }
                )
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """YAML-based setup (legacy)."""
    hass.data.setdefault(DOMAIN, {})

    if DOMAIN in config:
        zones = config[DOMAIN]
        for zone_name, zone_config in zones.items():
            _LOGGER.debug("YAML setup for Climate React Plus zone: %s", zone_name)

            controller = ClimateReactController(hass, zone_name, zone_config)
            await controller.async_initialize()
            hass.data[DOMAIN][zone_name] = controller

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """UI-based setup (Config Flow)."""
    _LOGGER.debug("Setting up Climate React Plus from UI for: %s", entry.title)

    config = entry.data
    controller = ClimateReactController(hass, entry.title, config)
    await controller.async_initialize()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = controller
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    controller: ClimateReactController = hass.data[DOMAIN].pop(entry.entry_id, None)
    if controller:
        await controller.async_unload()
    return True

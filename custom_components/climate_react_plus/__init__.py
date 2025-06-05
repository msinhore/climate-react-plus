# File: custom_components/climate_react_plus/__init__.py

import logging
import voluptuous as vol

from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import config_validation as cv

from .climate_react import ClimateReactController

DOMAIN = "climate_react_plus"

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
    """Set up the Climate React Plus component."""
    hass.data[DOMAIN] = {}

    if DOMAIN not in config:
        return True

    zones = config[DOMAIN]
    for zone_name, zone_config in zones.items():
        _LOGGER.debug("Setting up Climate React Plus for zone: %s", zone_name)

        controller = ClimateReactController(hass, zone_name, zone_config)
        await controller.async_initialize()
        hass.data[DOMAIN][zone_name] = controller

    return True


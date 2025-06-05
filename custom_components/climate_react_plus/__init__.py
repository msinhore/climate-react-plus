# File: custom_components/climate_react_plus/__init__.py

import logging
import voluptuous as vol

from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import config_validation as cv

from .climate_react import ClimateReactController
from .const import DOMAIN

# Importa as APIs internas para helpers
from homeassistant.components.input_number import async_create_input_number
from homeassistant.components.input_boolean import async_create_input_boolean

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


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up from config entry."""
    hass.data.setdefault(DOMAIN, {})
    config = entry.data

    zone = config[CONF_NAME]

    def helper_id(suffix):
        return f"react_{zone}_{suffix}"

    await _create_input_boolean(hass, helper_id("enabled"), f"Climate React {zone} Enabled")
    await _create_input_number(hass, helper_id("temp_min"), f"{zone} Temp Min", 17, 30, 0.1, config["min_temp"])
    await _create_input_number(hass, helper_id("temp_max"), f"{zone} Temp Max", 17, 30, 0.1, config["max_temp"])
    await _create_input_number(hass, helper_id("setpoint"), f"{zone} Setpoint", 17, 30, 1, config["setpoint"])

    controller = ClimateReactController(hass, zone, {
        "climate_entity": config["climate_entity"],
        "temperature_sensor": config["temperature_sensor"],
        "enabled_entity": f"input_boolean.{helper_id('enabled')}",
        "min_temp_entity": f"input_number.{helper_id('temp_min')}",
        "max_temp_entity": f"input_number.{helper_id('temp_max')}",
        "setpoint_entity": f"input_number.{helper_id('setpoint')}",
        "mode_entity": config.get("mode_entity"),
        "fan_entity": config.get("fan_entity"),
    })

    await controller.async_initialize()
    hass.data[DOMAIN][zone] = controller

    return True


async def _create_input_number(hass, object_id, name, min_val, max_val, step, initial):
    if f"input_number.{object_id}" in hass.states.async_entity_ids("input_number"):
        _LOGGER.debug("Helper %s already exists, skipping creation", object_id)
        return

    await async_create_input_number(
        hass,
        {
            "name": name,
            "initial": initial,
            "min": min_val,
            "max": max_val,
            "step": step,
            "mode": "box",
            "unique_id": object_id,
        }
    )
    _LOGGER.info("Created helper input_number.%s", object_id)


async def _create_input_boolean(hass, object_id, name):
    if f"input_boolean.{object_id}" in hass.states.async_entity_ids("input_boolean"):
        _LOGGER.debug("Helper %s already exists, skipping creation", object_id)
        return

    await async_create_input_boolean(
        hass,
        {
            "name": name,
            "initial": True,
            "unique_id": object_id,
        }
    )
    _LOGGER.info("Created helper input_boolean.%s", object_id)

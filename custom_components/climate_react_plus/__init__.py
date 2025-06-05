import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol
from homeassistant.const import CONF_NAME
from homeassistant.helpers import config_validation as cv

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
    hass.data.setdefault(DOMAIN, {})
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up integration from config entry."""
    hass.data.setdefault(DOMAIN, {})
    config = entry.data
    zone = config[CONF_NAME]

    use_fahrenheit = config.get("use_fahrenheit", False)
    unit = "°F" if use_fahrenheit else "°C"

    # Salva config para as plataformas acessarem
    hass.data[DOMAIN][zone] = {
        "zone": zone,
        "config": config,
        "unit": unit,  # <-- IMPORTANTE: agora number.py pode usar isso
    }

    # Ativa as plataformas que conterão os helpers
    await hass.config_entries.async_forward_entry_setups(entry, ["number", "switch"])

    controller = ClimateReactController(hass, zone, {
        "climate_entity": config["climate_entity"],
        "temperature_sensor": config["temperature_sensor"],
        "enabled_entity": f"switch.climate_react_{zone}_enabled",
        "min_temp_entity": f"number.climate_react_{zone}_temp_min",
        "max_temp_entity": f"number.climate_react_{zone}_temp_max",
        "setpoint_entity": f"number.climate_react_{zone}_setpoint",
        "mode_entity": config.get("mode_entity"),
        "fan_entity": config.get("fan_entity"),
    })

    await controller.async_initialize()
    return True

from __future__ import annotations

import logging
from typing import Any, Final

import voluptuous as vol
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .helpers import ensure_helpers


_LOGGER: Final = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Legacy YAML support (optional)
# -----------------------------------------------------------------------------
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                cv.string: vol.Schema(
                    {
                        # mandatory entities ------------------------------------------------
                        vol.Required("climate_entity"): cv.entity_id,
                        vol.Required("temp_in"): cv.entity_id,   # indoor temperature sensor
                        vol.Required("temp_out"): cv.entity_id,  # outdoor temperature sensor

                        # optional entities -------------------------------------------------
                        vol.Optional("hum_in"): cv.entity_id,    # indoor RH sensor
                        vol.Optional("trv_entity"): cv.entity_id,  # smart TRV / radiator

                        # optional comfort parameters ---------------------------------------
                        vol.Optional("temp_min"): vol.Coerce(float),
                        vol.Optional("temp_max"): vol.Coerce(float),
                        vol.Optional("setpoint"): vol.Coerce(float),
                        vol.Optional("deadband"): vol.Coerce(float),
                        vol.Optional("humid_max"): vol.Coerce(int),
                        vol.Optional("heat_base"): vol.Coerce(float),
                        vol.Optional("k_heat"): vol.Coerce(float),

                        # flags -------------------------------------------------------------
                        vol.Optional("use_fahrenheit", default=False): cv.boolean,
                    }
                )
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

# -----------------------------------------------------------------------------


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Bootstrap namespace when YAML is used."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Handle a Config-Entry created via the UI (Config-Flow)."""

    hass.data.setdefault(DOMAIN, {})

    cfg: dict[str, Any] = entry.data
    zone: str = cfg[CONF_NAME]

    use_fahrenheit = cfg.get("use_fahrenheit", False)
    unit = "°F" if use_fahrenheit else "°C"  # display-only (helpers / card)

    # Persist runtime context for the zone so every platform can read it
    hass.data[DOMAIN][zone] = {
        "zone": zone,
        "config": cfg,
        "unit": unit,
    }

    await ensure_helpers(hass, zone)
    await hass.config_entries.async_forward_entry_setups(entry, ["climate"])
    
    _LOGGER.debug("ThermoAdapt zone “%s” initialised (unit %s).", zone, unit)
    return True

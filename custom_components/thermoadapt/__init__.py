import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
import voluptuous as vol
from homeassistant.const import CONF_NAME
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# YAML configuration schema (legacy path)
# -----------------------------------------------------------------------------
# Users who still prefer configuration.yaml can supply entities manually.
# In a typical setup the UI Config-Flow will be used instead, but we keep
# this schema for backward-compatibility.
# -----------------------------------------------------------------------------
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                cv.string: vol.Schema(
                    {
                        # ─── entidades obrigatórias ──────────────────────────
                        vol.Required("climate_entity"): cv.entity_id,
                        vol.Required("temp_in"):        cv.entity_id,   # sensor temperatura interna
                        vol.Required("temp_out"):       cv.entity_id,   # sensor temperatura externa

                        # ─── entidades opcionais ───────────────────────────
                        vol.Optional("hum_in"):    cv.entity_id,        # sensor UR interna
                        vol.Optional("trv_entity"):cv.entity_id,        # válvula TRV (aquecimento)

                        # ─── parâmetros de conforto (opcionais; se ausentes,
                        #      defaults de const.py serão aplicados) ─────────
                        vol.Optional("temp_min"):   vol.Coerce(float),
                        vol.Optional("temp_max"):   vol.Coerce(float),
                        vol.Optional("setpoint"):   vol.Coerce(float),
                        vol.Optional("deadband"):   vol.Coerce(float),
                        vol.Optional("humid_max"):  vol.Coerce(int),
                        vol.Optional("heat_base"):  vol.Coerce(float),
                        vol.Optional("k_heat"):     vol.Coerce(float),

                        # ─── flags ──────────────────────────────────────────
                        vol.Optional("use_fahrenheit", default=False): cv.boolean,
                    }
                )
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Legacy YAML setup. Simply bootstrap the integration namespace."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """UI-driven setup (Config-Flow).

    Workflow:
      1. Persist zone configuration so helper platforms (number/switch) can
         access comfort parameters (T_base, dead-band, UA, Q_int, etc.).
      2. Forward the entry to those helper platforms so they materialise
         the sliders and toggles in HA.
      3. Forward the entry to the *climate* platform
         where `ThermoAdaptClimate` implements the Dear & Brager model.
    """

    hass.data.setdefault(DOMAIN, {})

    cfg   = entry.data
    zone  = cfg[CONF_NAME]

    use_f = cfg.get("use_fahrenheit", False)
    unit  = "°F" if use_f else "°C"   # helper/card display unit

    # ------------------------------------------------------------------
    # Store runtime data for this zone so that other platform files can
    # retrieve configuration and units without parsing the entry again.
    # ------------------------------------------------------------------
    hass.data[DOMAIN][zone] = {
        "zone":   zone,
        "config": cfg,
        "unit":   unit,
    }

    # ------------------------------------------------------------------
    # Forward the entry to helper **and** climate platforms.
    #   number  → sliders (dead-band, set-point…)
    #   switch  → master enable toggle
    #   climate → adaptive logic entity (ThermoAdaptClimate)
    # ------------------------------------------------------------------
    await hass.config_entries.async_forward_entry_setups(
        entry, ["number", "switch", "climate"]
    )

    return True


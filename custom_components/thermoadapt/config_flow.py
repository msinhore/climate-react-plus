"""ThermoAdapt – Config-Flow (UI wizard) and Options-Flow

Compact version – no external dependencies (only stdlib + Home Assistant).
Collects:
  • Zone name, sensors, AC (and optional TRV)
  • Comfort parameters (min/max T, dead-band, etc.)
Stores comfort sliders in *entry.options* so they are editable later.  Helpers
(input_number / input_boolean) are created on-the-fly via `ensure_helpers()`.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import selector

from .const import (
    DOMAIN,
    CONF_TEMP_IN,
    CONF_TEMP_OUT,
    CONF_HUM_IN,
    CONF_CLIMATE_ENTITY,
    CONF_TRV_ENTITY,
    HELPER_SUFFIXES,
)
from .helpers import ensure_helpers  # util inside the same component

_LOGGER = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# DEFAULTS – hard-coded here to avoid extra imports/deps
# -----------------------------------------------------------------------------
DEFAULTS: Dict[str, float | int] = {
    "temp_min":   23.0,
    "temp_max":   27.0,
    "setpoint":   25.0,
    "deadband":   0.5,
    "humid_max":  65,
    "heat_base":  20.5,
    "k_heat":     0.18,
}


class ThermoAdaptConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """ThermoAdapt onboarding wizard (two simple steps)."""

    VERSION = 1
    _data: Dict[str, Any]

    # ------------------------------------------------------------------
    # STEP 1 – basic entities
    # ------------------------------------------------------------------
    async def async_step_user(self, user_input: Dict[str, Any] | None = None):
        if user_input is None:
            schema = vol.Schema({
                vol.Required(CONF_NAME): selector({"text": {}}),
                vol.Required(CONF_CLIMATE_ENTITY): selector({"entity": {"domain": "climate"}}),
                vol.Optional(CONF_TRV_ENTITY, default=""): selector({"entity": {"domain": "number"}}),
                vol.Required(CONF_TEMP_IN): selector({"entity": {"domain": "sensor", "device_class": "temperature"}}),
                vol.Required(CONF_TEMP_OUT): selector({"entity": {"domain": "sensor", "device_class": "temperature"}}),
                vol.Optional(CONF_HUM_IN, default=""): selector({"entity": {"domain": "sensor", "device_class": "humidity"}}),
            })
            return self.async_show_form(step_id="user", data_schema=schema)

        # Store and move on
        self._data = dict(user_input)
        return await self.async_step_comfort()

    # ------------------------------------------------------------------
    # STEP 2 – comfort parameters (sliders)
    # ------------------------------------------------------------------
    async def async_step_comfort(self, user_input: Dict[str, Any] | None = None):
        if user_input is None:
            # Build a schema dynamically from DEFAULTS so adding fields later is trivial
            schema_dict: Dict[Any, Any] = {
                vol.Required(fid, default=DEFAULTS[fid]): vol.All(vol.Coerce(float)) if "humid" not in fid else vol.All(vol.Coerce(int))
                for fid in HELPER_SUFFIXES if fid in DEFAULTS
            }
            return self.async_show_form(step_id="comfort", data_schema=vol.Schema(schema_dict))

        # Merge and create helpers
        self._data.update(user_input)
        await ensure_helpers(self.hass, self._data[CONF_NAME])

        return self.async_create_entry(title=self._data[CONF_NAME], data=self._data, options=user_input)

    # ------------------------------------------------------------------
    # OPTIONS FLOW – identical slider set, editable after setup
    # ------------------------------------------------------------------
    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry):  # noqa: D401
        return ThermoAdaptOptionsFlow(entry)


class ThermoAdaptOptionsFlow(config_entries.OptionsFlow):
    """Re-expose comfort sliders so user can retune later."""

    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input: Dict[str, Any] | None = None):
        if user_input is None:
            current = {k: self.entry.options.get(k, DEFAULTS.get(k)) for k in HELPER_SUFFIXES}
            schema_dict: Dict[Any, Any] = {
                vol.Required(fid, default=current[fid]): vol.All(vol.Coerce(float)) if "humid" not in fid else vol.All(vol.Coerce(int))
                for fid in HELPER_SUFFIXES if fid in DEFAULTS
            }
            return self.async_show_form(step_id="init", data_schema=vol.Schema(schema_dict))

        return self.async_create_entry(title="ThermoAdapt options", data=user_input)

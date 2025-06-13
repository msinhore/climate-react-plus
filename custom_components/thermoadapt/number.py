"""custom_components/thermoadapt/number.py

Helper *NumberEntity* sliders exposed by ThermoAdapt so users can tune the
adaptive-comfort algorithm directly from the UI (Settings ▸ Devices & Services)
without writing YAML.

For every **zone** created via Config-Flow the file instantiates one slider per
item in the *PARAMS* dictionary and restores the last value after a restart.

Why sliders?
-------------
• *temp_min* / *temp_max*  – static thresholds when adaptive mode is OFF.  
• *setpoint*               – fixed target when manual.  
• *deadband*               – neutral zone before switching HVAC.  
• *humid_max*              – UR (%) that triggers *dry* mode.  
• *heat_base* & *k_heat*   – coefficients for Dear & Brager adaptive heating.

Each entity is marked **EntityCategory.CONFIG** so it shows up under
*Settings ▸ Devices & Services ▸ Entities* and not in the “main” dashboard.  
Unit-of-measurement is inherited from the zone (°C/°F) when relevant.
"""

from __future__ import annotations

import logging
from typing import Final

from homeassistant.components.number import NumberEntity
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN

_LOGGER: Final = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Slider specification
# slug -> (friendly-name, min, max, step, unit, default)
# -----------------------------------------------------------------------------
PARAMS: Final = {
    "temp_min":  ("Temp Min",           16, 26, 0.5, "°C", 23.0),
    "temp_max":  ("Temp Max",           20, 40, 0.5, "°C", 27.0),
    "setpoint":  ("Set-point Fixed",    18, 30, 0.1, "°C", 25.0),
    "deadband":  ("Dead-band",            0,  5, 0.1, "°C",  0.5),
    "humid_max": ("UR Max",             40, 80, 1.0, "%",  65),
    "heat_base": ("Heat Base",          18, 24, 0.1, "°C", 20.5),
    "k_heat":    ("k Heat ΔT/ΔText",   0.05, 0.40, 0.01, None, 0.18),
}

# -----------------------------------------------------------------------------
# Platform entry-point – called once per Config-Entry / zone
# -----------------------------------------------------------------------------

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    """Create Number entities for the zone specified in *entry*."""

    zone: str = entry.data[CONF_NAME]
    unit = hass.data[DOMAIN][zone]["unit"]  # "°C" or "°F" for display only

    entities: list[NumberEntity] = []
    for slug, meta in PARAMS.items():
        friendly, v_min, v_max, step, uom, default = meta
        entities.append(
            ThermoAdaptNumber(
                zone=zone,
                slug=slug,
                name=f"{zone.capitalize()} {friendly}",
                native_min=v_min,
                native_max=v_max,
                native_step=step,
                native_unit=uom or unit,
                initial_value=default,
            )
        )

    async_add_entities(entities)


# -----------------------------------------------------------------------------
# Entity class
# -----------------------------------------------------------------------------

class ThermoAdaptNumber(RestoreEntity, NumberEntity):
    """Single slider tied to an adaptive-comfort parameter."""

    _attr_entity_category = EntityCategory.CONFIG

    # pylint: disable=too-many-arguments – explicit is better than implicit
    def __init__(
        self,
        *,
        zone: str,
        slug: str,
        name: str,
        native_min: float,
        native_max: float,
        native_step: float,
        native_unit: str | None,
        initial_value: float,
    ) -> None:
        self._attr_unique_id = f"thermoadapt_{zone}_{slug}"
        self._attr_name = name
        self._attr_native_min_value = native_min
        self._attr_native_max_value = native_max
        self._attr_native_step = native_step
        self._attr_native_unit_of_measurement = native_unit
        self._native_value = initial_value

    # ------------------------------------------------------------------
    # Restore last value after restart so fine-tuning is not lost.
    # ------------------------------------------------------------------
    async def async_added_to_hass(self) -> None:
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._native_value = float(last_state.state)
            except ValueError:
                _LOGGER.warning("Invalid restore value for %s: %s", self.entity_id, last_state.state)

    # ------------------------------------------------------------------
    # Properties/commands expected by NumberEntity
    # ------------------------------------------------------------------
    @property
    def native_value(self) -> float:  # type: ignore[override]
        return self._native_value

    async def async_set_native_value(self, value: float) -> None:  # type: ignore[override]
        self._native_value = value
        self.async_write_ha_state()

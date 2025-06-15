from __future__ import annotations

import logging
from typing import Final, Any

from homeassistant.components.number import NumberEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from dataclasses import dataclass

from .const import DOMAIN

_LOGGER: Final = logging.getLogger(__name__)

@dataclass
class ComfortParams:
    tc_base: float
    tc_min: float
    th_base: float
    k_heat: float
    deadband_cool: float
    deadband_heat: float
    humid_max: int
    ua_total: float
    q_int: float

def tset_cool(t_out: float, p: ComfortParams) -> float:
    """Cooling set-point as a linear function of outdoor temperature."""
    return p.tc_base - p.k_heat * (t_out - p.tc_base)

def tset_heat(t_out: float, p: ComfortParams) -> float:
    """Heating set-point as a linear function of outdoor temperature."""
    return p.th_base + p.k_heat * (p.th_base - t_out)

# -----------------------------------------------------------------------------
# Configurable parameters
# -----------------------------------------------------------------------------

NUMBER_PARAMS: Final = {
    "temp_min":   ("Temp Min",          16, 26, 0.5, "°C", 23.0),
    "temp_max":   ("Temp Max",          20, 40, 0.5, "°C", 27.0),
    "setpoint":   ("Set-point Fixed",   18, 30, 0.1, "°C", 25.0),
    "deadband":   ("Dead-band",          0,  5, 0.1, "°C", 0.5),
    "humid_max":  ("UR Max",            40, 80, 1.0, "%",  65),
    "heat_base":  ("Heat Base",         18, 24, 0.1, "°C", 20.5),
    "k_heat":     ("k Heat ΔT/ΔText",  0.05, 0.40, 0.01, None, 0.18),
    "ua_total":   ("UA Total",           5, 150, 1.0, "W/K", 30.0),
    "q_int":      ("Q Internal",         0, 800, 10, "W", 200.0),
}

SWITCH_PARAMS: Final = {
    "enabled":  ("ThermoAdapt Enabled", True),
    "adaptive": ("Adaptive Mode", False),
}

# -----------------------------------------------------------------------------
# Setup platform entry points
# -----------------------------------------------------------------------------

async def async_setup_entry_numbers(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    zone = entry.data[CONF_NAME]
    unit = hass.data[DOMAIN][zone].get("unit", "°C")
    entities: list[NumberEntity] = []

    for slug, (friendly, v_min, v_max, step, uom, default) in NUMBER_PARAMS.items():
        name = f"ThermoAdapt {zone.capitalize()} {friendly}"
        entities.append(
            ThermoAdaptNumber(
                zone=zone,
                slug=slug,
                name=name,
                native_min=v_min,
                native_max=v_max,
                native_step=step,
                native_unit=uom or unit,
                initial_value=default,
            )
        )

    async_add_entities(entities)

async def async_setup_entry_switches(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback
) -> None:
    zone = entry.data[CONF_NAME]
    entities: list[SwitchEntity] = []

    for slug, (friendly, default) in SWITCH_PARAMS.items():
        name = f"ThermoAdapt {zone.capitalize()} {friendly}"
        entities.append(
            ThermoAdaptSwitch(
                zone=zone,
                slug=slug,
                name=name,
                initial_state=default,
            )
        )

    async_add_entities(entities)

# -----------------------------------------------------------------------------
# NumberEntity
# -----------------------------------------------------------------------------

class ThermoAdaptNumber(RestoreEntity, NumberEntity):
    _attr_entity_category = EntityCategory.CONFIG

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

    async def async_added_to_hass(self) -> None:
        if (last_state := await self.async_get_last_state()) is not None:
            try:
                self._native_value = float(last_state.state)
            except ValueError:
                _LOGGER.warning("Invalid restore value for %s: %s", self.entity_id, last_state.state)

    @property
    def native_value(self) -> float:
        return self._native_value

    async def async_set_native_value(self, value: float) -> None:
        self._native_value = value
        self.async_write_ha_state()

# -----------------------------------------------------------------------------
# SwitchEntity
# -----------------------------------------------------------------------------

class ThermoAdaptSwitch(RestoreEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        *,
        zone: str,
        slug: str,
        name: str,
        initial_state: bool,
    ) -> None:
        self._attr_unique_id = f"thermoadapt_{zone}_{slug}"
        self._attr_name = name
        self._attr_entity_id = f"switch.thermoadapt_{zone}_{slug}"
        self._is_on = initial_state

    async def async_added_to_hass(self) -> None:
        if (last := await self.async_get_last_state()) is not None:
            self._is_on = last.state == "on"

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._is_on = False
        self.async_write_ha_state()

PLATFORM = __name__.rsplit(".", 1)[-1]  # Detects 'number' or 'switch'

async def async_setup_entry_all(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Setup Number and Switch entities."""
    await async_setup_entry_numbers(hass, entry, async_add_entities)
    await async_setup_entry_switches(hass, entry, async_add_entities)

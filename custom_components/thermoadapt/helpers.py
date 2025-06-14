from __future__ import annotations

import logging
from typing import Dict, Final, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.exceptions import ServiceNotFound

from .const import DOMAIN

_LOGGER: Final = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Slider specification – slug -> (friendly-name, min, max, step, unit, default)
# -----------------------------------------------------------------------------
PARAMS: Final = {
    "temp_min":  ("Temp Min",           16, 26, 0.5, "°C", 23.0),
    "temp_max":  ("Temp Max",           20, 40, 0.5, "°C", 27.0),
    "setpoint":  ("Set-point Fixed",    18, 30, 0.1, "°C", 25.0),
    "deadband":  ("Dead-band",            0,  5, 0.1, "°C",  0.5),
    "humid_max": ("UR Max",             40, 80, 1.0, "%",  65),
    "heat_base": ("Heat Base",          18, 24, 0.1, "°C", 20.5),
    "k_heat":    ("k Heat ΔT/ΔText",   0.05, 0.40, 0.01, None, 0.18),
    "ua_total": ("UA Total",  5, 150, 1, "W/K", 30),
    "q_int":    ("Q Internal", 0, 800, 10, "W", 200),
}

SWITCH_PARAMS: Final = {
    "enabled":  ("ThermoAdapt Enabled", True),
    "adaptive": ("Adaptive Mode", False),
}

# -----------------------------------------------------------------------------
# Adaptive equations
# -----------------------------------------------------------------------------

def tset_cool(t_out: float, p) -> float:
    t_bal = p.tc_base - p.q_int / p.ua_total
    k_cool = (p.tc_base - p.tc_min) / (t_out - t_bal) if t_out > t_bal else 0
    return p.tc_base if t_out <= t_bal else p.tc_base - k_cool * (t_out - t_bal)

def tset_heat(t_out: float, p) -> float:
    t_bal = p.th_base - p.q_int / p.ua_total
    return p.th_base if t_out >= t_bal else p.th_base + p.k_heat * (t_bal - t_out)

# -----------------------------------------------------------------------------
# Unified helper creation
# -----------------------------------------------------------------------------

async def ensure_helpers(hass: HomeAssistant, zone: str) -> None:
    """Create all Number and Switch entities for this zone if missing."""
    to_create: Dict[str, Dict] = {}

    for slug, (_friendly, v_min, v_max, step, _uom, default) in PARAMS.items():
        eid = f"number.thermoadapt_{zone}_{slug}"
        if eid not in hass.states.async_entity_ids():
            to_create[eid] = {
                "service": "number/create",
                "data": {
                    "name": f"ThermoAdapt {zone.capitalize()} {slug.replace('_', ' ').capitalize()}",
                    "min": v_min,
                    "max": v_max,
                    "step": step,
                    "initial": default,
                    "unit_of_measurement": _uom,
                    "entity_id": eid,
                },
            }

    for slug, (friendly, default) in SWITCH_PARAMS.items():
        eid = f"switch.thermoadapt_{zone}_{slug}"
        if eid not in hass.states.async_entity_ids():
            to_create[eid] = {
                "service": "switch/create",
                "data": {
                    "name": f"ThermoAdapt {zone.capitalize()} {friendly}",
                    "initial": default,
                    "entity_id": eid,
                },
            }

    for eid, info in to_create.items():
        domain = info["service"].split("/")[0]
        service = info["service"].split("/")[1]
        data = info["data"]

        try:
            await hass.services.async_call(domain, service, data, blocking=True)
            _LOGGER.debug("Created helper: %s", eid)
        except ServiceNotFound:
            _LOGGER.error(
                "Service %s.%s not available — is the frontend running?",
                domain, service
            )

# -----------------------------------------------------------------------------
# Optional: entry-point for native SwitchEntity + NumberEntity support
# -----------------------------------------------------------------------------

async def async_setup_switches(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    zone = entry.data[CONF_NAME]
    entities = [ThermoAdaptSwitch(zone, slug, friendly, default) for slug, (friendly, default) in SWITCH_PARAMS.items()]
    async_add_entities(entities)

async def async_setup_numbers(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    zone = entry.data[CONF_NAME]
    unit = hass.data[DOMAIN][zone]["unit"]
    entities = [
        ThermoAdaptNumber(
            zone=zone,
            slug=slug,
            name=f"ThermoAdapt {zone.capitalize()} {friendly}",
            native_min=v_min,
            native_max=v_max,
            native_step=step,
            native_unit=uom or unit,
            initial_value=default,
        )
        for slug, (friendly, v_min, v_max, step, uom, default) in PARAMS.items()
    ]
    async_add_entities(entities)

class ThermoAdaptSwitch(RestoreEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, zone: str, slug: str, friendly: str, default: bool) -> None:
        self._attr_unique_id = f"thermoadapt_{zone}_{slug}"
        self._attr_name = f"ThermoAdapt {zone.capitalize()} {friendly}"
        self._attr_entity_id = f"switch.thermoadapt_{zone}_{slug}"
        self._is_on = default

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


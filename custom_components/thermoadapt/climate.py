"""ThermoAdapt – Adaptive climate controller entity

Implements the Dear & Brager (1998, 2001) adaptive comfort equations for both
cooling and heating.  Drives a split-AC (climate.*) and, optionally, a smart
TRV (number.*) in the same zone.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Final

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .helpers import tset_cool, tset_heat
from .models import ComfortParams
from .number import PARAMS  # reuse default values

_LOGGER: Final = logging.getLogger(__name__)
SCAN_INTERVAL: Final = timedelta(seconds=30)

# -----------------------------------------------------------------------------
# Coordinator – reads sensors & calculates adaptive set-point
# -----------------------------------------------------------------------------

class ThermoAdaptCoordinator(DataUpdateCoordinator[float]):
    """Periodically provides the adaptive set-point (°C)."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, params: ComfortParams):
        super().__init__(
            hass,
            _LOGGER,
            name=f"thermoadapt_{entry.data[CONF_NAME]}",
            update_interval=SCAN_INTERVAL,
        )
        self.entry = entry
        self.params = params

    async def _async_update_data(self) -> float:  # type: ignore[override]
        s = self.hass.states
        t_out = float(s.get(self.entry.data["temp_out"]).state)

        # Choose equation based on outdoor vs. balance temperature
        sp = (
            tset_cool(t_out, self.params)
            if t_out > (self.params.tc_base - self.params.q_int / self.params.ua_total)
            else tset_heat(t_out, self.params)
        )
        _LOGGER.debug("[%s] Adaptive set-point %.1f °C (Tout %.1f °C)", self.entry.data[CONF_NAME], sp, t_out)
        return round(sp, 1)


# -----------------------------------------------------------------------------
# Climate Entity – applies coordinator output to devices
# -----------------------------------------------------------------------------

class ThermoAdaptClimate(ClimateEntity):
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        coordinator: ThermoAdaptCoordinator,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self._zone = entry.data[CONF_NAME]

        self._climate_entity = entry.data["climate_entity"]
        self._trv_entity = entry.data.get("trv_entity")

        # Read dead-band slider once; updates will be caught via helpers → params in next release.
        def _slider(slug: str, default: float) -> float:
            st = hass.states.get(f"number.thermoadapt_{self._zone}_{slug}")
            try:
                return float(st.state) if st and st.state not in ("unknown", "unavailable") else default
            except (TypeError, ValueError):
                return default

        self._deadband_cool = _slider("deadband", PARAMS["deadband"][-1])
        self._deadband_heat = self._deadband_cool  # using same slider for heat for now

        self._attr_name = f"ThermoAdapt {self._zone.capitalize()}"
        self._attr_unique_id = f"thermoadapt_{self._zone}"

        # Initial state
        self._attr_target_temperature = None
        self._attr_hvac_mode = HVACMode.OFF

    # ------------------------------------------------------------------
    # Home Assistant hooks
    # ------------------------------------------------------------------
    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )
        await self.coordinator.async_config_entry_first_refresh()

    # ------------------------------------------------------------------
    # Coordinator callback
    # ------------------------------------------------------------------
    @callback
    def _handle_coordinator_update(self) -> None:
        sp: float = self.coordinator.data
        self._attr_target_temperature = sp

        t_in_state = self.hass.states.get(self.entry.data["temp_in"])
        try:
            t_in = float(t_in_state.state) if t_in_state and t_in_state.state not in ("unknown", "unavailable") else None
        except ValueError:
            t_in = None

        if t_in is None:
            _LOGGER.warning("[%s] Indoor temperature sensor unavailable.", self._zone)
            return

        mode_before = self._attr_hvac_mode

        # Decide HVAC mode based on dead-bands
        if t_in > sp + self._deadband_cool:
            self._attr_hvac_mode = HVACMode.COOL
        elif t_in < sp - self._deadband_heat:
            self._attr_hvac_mode = HVACMode.HEAT if self._trv_entity else HVACMode.OFF
        else:
            self._attr_hvac_mode = HVACMode.OFF

        if self._attr_hvac_mode != mode_before:
            self.hass.async_create_task(self._apply_mode(sp))

        self.async_write_ha_state()

    # ------------------------------------------------------------------
    # Device commands
    # ------------------------------------------------------------------
    async def _apply_mode(self, sp: float) -> None:
        """Push target temperature to the appropriate device."""
        if self._attr_hvac_mode == HVACMode.COOL:
            await self.hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {"entity_id": self._climate_entity, "hvac_mode": HVACMode.COOL},
                blocking=False,
            )
            await self.hass.services.async_call(
                "climate",
                "set_temperature",
                {"entity_id": self._climate_entity, "temperature": sp},
                blocking=False,
            )
        elif self._attr_hvac_mode == HVACMode.HEAT and self._trv_entity:
            await self.hass.services.async_call(
                "number",
                "set_value",
                {"entity_id": self._trv_entity, "value": sp},
                blocking=False,
            )
        else:  # OFF
            await self.hass.services.async_call(
                "climate",
                "set_hvac_mode",
                {"entity_id": self._climate_entity, "hvac_mode": HVACMode.OFF},
                blocking=False,
            )
            if self._trv_entity:
                await self.hass.services.async_call(
                    "number",
                    "set_value",
                    {"entity_id": self._trv_entity, "value": 7},  # frost-protection
                    blocking=False,
                )


# ---------------------------------------------------------------------------
# Platform entry-point – registers ThermoAdaptClimate for each Config-Entry
# ---------------------------------------------------------------------------


def _load_params_from_helpers(hass: HomeAssistant, zone: str) -> ComfortParams:
    """Build ComfortParams from current helper values (input_number)."""
    g = hass.states.get

    def f(slug: str, dflt: float) -> float:
        st = g(f"number.thermoadapt_{zone}_{slug}")
        try:
            return float(st.state) if st and st.state not in ("unknown", "unavailable") else dflt
        except (TypeError, ValueError):
            return dflt

    return ComfortParams(
        tc_base       = f("setpoint", PARAMS["setpoint"][-1]),
        tc_min        = f("temp_min", PARAMS["temp_min"][-1]),
        th_base       = f("heat_base", PARAMS["heat_base"][-1]),
        k_heat        = f("k_heat",   PARAMS["k_heat"][-1]),
        deadband_cool = f("deadband", PARAMS["deadband"][-1]),
        deadband_heat = f("deadband", PARAMS["deadband"][-1]),  # same slider for now
        humid_max     = int(f("humid_max", PARAMS["humid_max"][-1])),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register ThermoAdaptClimate entity for this zone."""
    zone = entry.data[CONF_NAME]
    params = _load_params_from_helpers(hass, zone)

    coordinator = ThermoAdaptCoordinator(hass, entry, params)
    entity = ThermoAdaptClimate(hass, entry, coordinator)

    async_add_entities([entity])

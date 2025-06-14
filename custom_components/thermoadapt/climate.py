"""
ThermoAdapt – Adaptive climate controller entity
===============================================

Implements the Dear & Brager (1998 / 2001) adaptive-comfort equations for both
cooling and heating.

Equipment handled per zone
--------------------------
• _cool_entity_  → split-AC in COOL / DRY mode
• _trv_entity_   → smart TRV / radiator in HEAT mode
• _aux_entity_   → same split-AC used as auxiliary HEAT (optional)

Home-Assistant minimum version: 2025.5.x
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
from homeassistant.const import CONF_NAME, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .helpers import tset_cool, tset_heat
from .models import ComfortParams
from .number import PARAMS

_LOGGER: Final = logging.getLogger(__name__)
SCAN_INTERVAL: Final = timedelta(seconds=30)
AUX_MARGIN: Final = 1.0  # °C below set-point that triggers auxiliary heat


# ───────────────────────────────────────────────────────────────
# COORDINATOR  – computes adaptive set-point
# ───────────────────────────────────────────────────────────────
class ThermoAdaptCoordinator(DataUpdateCoordinator[float]):
    """Returns the adaptive set-point (°C) every SCAN_INTERVAL."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        params: ComfortParams,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"thermoadapt_{entry.data[CONF_NAME]}",
            update_interval=SCAN_INTERVAL,
        )
        self.entry = entry
        self.params = params

    async def _async_update_data(self) -> float:  # type: ignore[override]
        t_out = float(self.hass.states.get(self.entry.data["temp_out"]).state)

        sp = (
            tset_cool(t_out, self.params)
            if t_out > (self.params.tc_base - self.params.q_int / self.params.ua_total)
            else tset_heat(t_out, self.params)
        )
        _LOGGER.debug(
            "[%s] Adaptive set-point %.1f °C (Tout %.1f °C)",
            self.entry.data[CONF_NAME],
            sp,
            t_out,
        )
        return round(sp, 1)


# ───────────────────────────────────────────────────────────────
# CLIMATE ENTITY  – sends commands to AC / TRV
# ───────────────────────────────────────────────────────────────
class ThermoAdaptClimate(ClimateEntity):
    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    # -----------------------------------------------------------
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

        # —— equipment entities ————————————————————————
        self._cool_entity: str = entry.data["climate_entity"]          # split-AC
        self._trv_entity: str | None = entry.data.get("trv_entity")    # radiator
        self._aux_entity: str | None = entry.data.get("aux_entity")    # AC as HEAT

        # If aux-entity not specified but the AC supports HEAT,
        # reuse the same device as auxiliary heater.
        if not self._aux_entity:
            st = hass.states.get(self._cool_entity)
            if st and "heat" in st.attributes.get("hvac_modes", []):
                self._aux_entity = self._cool_entity

        # —— read dead-band slider (single value for now) —————
        def _slider(slug: str, dflt: float) -> float:
            st = hass.states.get(f"number.thermoadapt_{self._zone}_{slug}")
            try:
                return float(st.state) if st and st.state not in ("unknown", "unavailable") else dflt
            except (TypeError, ValueError):
                return dflt

        self._deadband = _slider("deadband", PARAMS["deadband"][-1])

        # —— HA entity metadata ————————————————————————
        self._attr_name = f"ThermoAdapt {self._zone.capitalize()}"
        self._attr_unique_id = f"thermoadapt_{self._zone}"
        self._attr_target_temperature: float | None = None
        self._attr_hvac_mode: HVACMode = HVACMode.OFF

    # -----------------------------------------------------------
    # Home-Assistant hooks
    # -----------------------------------------------------------
    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )
        await self.coordinator.async_config_entry_first_refresh()

    # -----------------------------------------------------------
    # Coordinator callback
    # -----------------------------------------------------------
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
            _LOGGER.warning("[%s] Indoor temperature sensor unavailable", self._zone)
            return

        mode_before = self._attr_hvac_mode
        use_aux = False

        # —— decide HVAC mode ————————————————————————
        if t_in > sp + self._deadband:                      # needs cooling
            self._attr_hvac_mode = HVACMode.COOL
        elif t_in < sp - self._deadband:                    # needs heating
            self._attr_hvac_mode = HVACMode.HEAT if self._trv_entity else HVACMode.OFF
            # trigger auxiliary heat if still far below set-point
            if self._aux_entity and t_in < sp - AUX_MARGIN:
                use_aux = True
        else:
            self._attr_hvac_mode = HVACMode.OFF

        if self._attr_hvac_mode != mode_before or use_aux:
            self.hass.async_create_task(self._apply_mode(sp, use_aux))

        self.async_write_ha_state()

    # -----------------------------------------------------------
    # Command dispatcher
    # -----------------------------------------------------------
    async def _apply_mode(self, sp: float, use_aux: bool) -> None:
        """Send target temperature / mode to the relevant devices."""
        # —— COOL (split-AC) —————————————————————————
        if self._attr_hvac_mode == HVACMode.COOL:
            await self._ensure_mode(self._cool_entity, HVACMode.COOL)
            await self.hass.services.async_call(
                "climate", "set_temperature",
                {"entity_id": self._cool_entity, "temperature": sp},
                blocking=False,
            )
            await self.hass.services.async_call(
                "climate", "set_fan_mode",
                {"entity_id": self._cool_entity, "fan_mode": "auto"},
                blocking=False,
            )

        # —— HEAT (radiator + optional aux-heat) —————————
        elif self._attr_hvac_mode == HVACMode.HEAT:
            if self._trv_entity:
                await self._ensure_mode(self._trv_entity, HVACMode.HEAT)
                await self.hass.services.async_call(
                    "climate", "set_temperature",
                    {"entity_id": self._trv_entity, "temperature": sp},
                    blocking=False,
                )
            if use_aux and self._aux_entity:
                await self._ensure_mode(self._aux_entity, HVACMode.HEAT)
                await self.hass.services.async_call(
                    "climate", "set_temperature",
                    {"entity_id": self._aux_entity, "temperature": sp},
                    blocking=False,
                )

        # —— OFF (all devices) ——————————————————————
        else:
            await self._ensure_mode(self._cool_entity, HVACMode.OFF)
            if self._trv_entity:
                await self._ensure_mode(self._trv_entity, HVACMode.OFF)
            if self._aux_entity and self._aux_entity != self._cool_entity:
                await self._ensure_mode(self._aux_entity, HVACMode.OFF)

    # -----------------------------------------------------------
    async def _ensure_mode(self, eid: str, mode: HVACMode) -> None:
        """Some ACs lock in AUTO; send OFF first, then target mode."""
        st = self.hass.states.get(eid)
        if not st:
            return
        if st.state == HVACMode.AUTO and mode != HVACMode.AUTO:
            await self.hass.services.async_call(
                "climate", "set_hvac_mode",
                {"entity_id": eid, "hvac_mode": HVACMode.OFF},
                blocking=False,
            )
        if st.state != mode:
            await self.hass.services.async_call(
                "climate", "set_hvac_mode",
                {"entity_id": eid, "hvac_mode": mode},
                blocking=False,
            )


# ───────────────────────────────────────────────────────────────
# PLATFORM ENTRY-POINT
# ───────────────────────────────────────────────────────────────
def _load_params_from_helpers(hass: HomeAssistant, zone: str) -> ComfortParams:
    """Create ComfortParams by reading current helper sliders."""
    g = hass.states.get

    def f(slug: str, dflt: float) -> float:
        st = g(f"number.thermoadapt_{zone}_{slug}")
        try:
            return float(st.state) if st and st.state not in ("unknown", "unavailable") else dflt
        except (TypeError, ValueError):
            return dflt

    return ComfortParams(
        tc_base=f("setpoint", PARAMS["setpoint"][-1]),
        tc_min=f("temp_min", PARAMS["temp_min"][-1]),
        th_base=f("heat_base", PARAMS["heat_base"][-1]),
        k_heat=f("k_heat", PARAMS["k_heat"][-1]),
        deadband_cool=f("deadband", PARAMS["deadband"][-1]),
        deadband_heat=f("deadband", PARAMS["deadband"][-1]),
        humid_max=int(f("humid_max", PARAMS["humid_max"][-1])),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register one ThermoAdaptClimate entity per config entry."""
    zone = entry.data[CONF_NAME]
    params = _load_params_from_helpers(hass, zone)

    coordinator = ThermoAdaptCoordinator(hass, entry, params)
    async_add_entities([ThermoAdaptClimate(hass, entry, coordinator)])

"""
ThermoAdapt – Adaptive climate controller entity
===============================================

Implements the Dear & Brager (1998 / 2001) adaptive-comfort equations for both
cooling and heating.

Equipment handled per zone
--------------------------
• split-AC (cool_entity) ........... COOL / DRY  (always present)
• smart TRV / radiator (trv_entity)  HEAT        (optional)
• auxiliary heater  (aux_entity) .... extra HEAT (optional – defaults to AC if
  it advertises hvac_mode "heat")

Master switch ....................... switch.thermoadapt_<zone>_enabled
Home-Assistant minimum version ...... 2025.5.x
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
from homeassistant.helpers.event import async_track_state_change
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .helpers import tset_cool, tset_heat
from .models import ComfortParams
from .number import PARAMS

_LOGGER: Final = logging.getLogger(__name__)

SCAN_INTERVAL: Final = timedelta(seconds=30)
AUX_MARGIN: Final = 1.0  # °C below set-point that triggers auxiliary heat
# Extra margin below set-point that activates the split-AC as auxiliary heat
# when a dedicated radiator/TRV cannot keep up.

# ───────────────────────────────────────────────────────────────
# COORDINATOR – computes the adaptive set-point
# ───────────────────────────────────────────────────────────────
class ThermoAdaptCoordinator(DataUpdateCoordinator[float]):
    """Pushes a fresh adaptive set-point every *SCAN_INTERVAL*."""

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
        """Executed by the coordinator — do NOT call directly.
        Returns a *fallback* set-point when the outdoor-temperature sensor
        is still ``unknown`` during Home-Assistant start-up so that the
        ThermoAdapt entity can be created immediately.
        """

        # ── Outdoor temperature (robust fetch) ─────────────────────────
        st = self.hass.states.get(self.entry.data["temp_out"])
        try:
            t_out: float | None = (
                float(st.state)
                if st and st.state not in ("unknown", "unavailable")
                else None
            )
        except ValueError:
            t_out = None

        # Sensor not ready yet -> return base cooling set-point and retry
        if t_out is None:
            _LOGGER.warning(
                "[%s] Outdoor temperature sensor unavailable; "
                "using fallback set-point until sensor recovers",
                self.entry.data[CONF_NAME],
            )
            return round(self.params.tc_base, 1)

        # Cooling curve above the balance point, heating curve otherwise
        sp = (
            tset_cool(t_out, self.params)
            if t_out > (self.params.tc_base - self.params.q_int / self.params.ua_total)
            else tset_heat(t_out, self.params)
        )
        _LOGGER.debug(
            "[%s] Adaptive set-point %.1f °C  (Tout %.1f °C)",
            self.entry.data[CONF_NAME],
            sp,
            t_out,
        )
        return round(sp, 1)


# ───────────────────────────────────────────────────────────────
# CLIMATE ENTITY – dispatches commands to equipment
# ───────────────────────────────────────────────────────────────
class ThermoAdaptClimate(ClimateEntity):
    """One entity per zone; exposes target-temperature and hvac_mode."""

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

        self._zone: str = entry.data[CONF_NAME]
        self._enable_switch = f"switch.thermoadapt_{self._zone}_enabled"

        # ── equipment entities ─────────────────────────────────
        self._cool_entity: str = entry.data["climate_entity"]
        self._trv_entity: str | None = entry.data.get("trv_entity")
        self._aux_entity: str | None = entry.data.get("aux_entity")

        # If aux not given but the AC supports HEAT → reuse AC
        if not self._aux_entity:
            st = hass.states.get(self._cool_entity)
            if st and "heat" in st.attributes.get("hvac_modes", []):
                self._aux_entity = self._cool_entity
                _LOGGER.debug(
                    "[%s] Using %s as auxiliary heater (heat-capable AC)",
                    self._zone,
                    self._cool_entity,
                )
        # ── advertise supported HVAC modes to HA ────────────────────
        modes = [HVACMode.OFF, HVACMode.COOL]          # always present
        if self._trv_entity or self._aux_entity:       # heating available
            modes.append(HVACMode.HEAT)
        # Optional: include HVACMode.DRY when the AC supports it.
        if "dry" in (hass.states.get(self._cool_entity).attributes.get("hvac_modes", [])):
            modes.append(HVACMode.DRY)
        self._attr_hvac_modes = modes


        # ── comfort parameters (cached) ───────────────────────
        def _slider(slug: str, dflt: float) -> float:
            st = hass.states.get(f"number.thermoadapt_{self._zone}_{slug}")
            try:
                return float(st.state) if st and st.state not in ("unknown", "unavailable") else dflt
            except (TypeError, ValueError):
                return dflt

        self._deadband: float = _slider("deadband", PARAMS["deadband"][-1])

        # ── HA metadata ───────────────────────────────────────
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
        """Wire coordinator & master switch callbacks."""
        # 1) Coordinator (periodic fallback refresh)
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )
        # 2) Master enable switch — instant reaction
        self.async_on_remove(
            async_track_state_change(
                self.hass,
                self._enable_switch,
                lambda *_: self._handle_coordinator_update(),
            )
        )
        # 3) Event-driven refresh: whenever any relevant sensor/slider changes
        entities_to_watch = [
            self.entry.data["temp_in"],
            self.entry.data["temp_out"],
            self.entry.data.get("hum_in"),
        ] + [
            f"number.thermoadapt_{self._zone}_{slug}" for slug in PARAMS.keys()
        ]
        self.async_on_remove(
            async_track_state_change(
                self.hass,
                [eid for eid in entities_to_watch if eid],
                lambda *_: self.coordinator.async_request_refresh(),
            )
        )
 
        await self.coordinator.async_config_entry_first_refresh()

    # -----------------------------------------------------------
    # Core decision logic
    # -----------------------------------------------------------
    @callback
    def _handle_coordinator_update(self) -> None:
        """Runs whenever sensors OR the enable switch change."""
        # ── Master-switch guard ──
        # If the supervisor switch is OFF we must:
        #   1) Turn every controlled device OFF
        #   2) Publish the new state immediately so the UI reflects it
        #      (no need to evaluate temperatures, dead-band, etc.)
        
        if not self.hass.states.is_state(self._enable_switch, "on"):
            # 1) Force HVAC mode to OFF (skip aux-heat)
            if self._attr_hvac_mode != HVACMode.OFF:
                self._attr_hvac_mode = HVACMode.OFF
                self.hass.async_create_task(
                    self._apply_mode(self.coordinator.data, use_aux=False)
                )

            # 2) Write state so dashboards update right away
            self.async_write_ha_state()
            return
        # -----------------------------------------------------

        sp: float = self.coordinator.data
        self._attr_target_temperature = sp

        # Indoor temperature
        t_in_state = self.hass.states.get(self.entry.data["temp_in"])
        try:
            t_in = float(t_in_state.state) if t_in_state and t_in_state.state not in ("unknown", "unavailable") else None
        except ValueError:
            t_in = None
        if t_in is None:
            _LOGGER.warning("[%s] Indoor temperature sensor unavailable", self._zone)
            return

        previous_mode = self._attr_hvac_mode
        use_aux = False

        # ── decide cooling / heating / off ───────────────────
        if t_in > sp + self._deadband:
            self._attr_hvac_mode = HVACMode.COOL
        elif t_in < sp - self._deadband:
            self._attr_hvac_mode = HVACMode.HEAT if self._trv_entity else HVACMode.OFF
            # auxiliary heat if *well* below set-point
            if self._aux_entity and t_in < sp - AUX_MARGIN:
                use_aux = True
        else:
            self._attr_hvac_mode = HVACMode.OFF

        if self._attr_hvac_mode != previous_mode or use_aux:
            self.hass.async_create_task(self._apply_mode(sp, use_aux))

        # reflect new state to HA UI
        self.async_write_ha_state()

    # -----------------------------------------------------------
    # Command dispatcher
    # -----------------------------------------------------------
    async def _apply_mode(self, sp: float, use_aux: bool) -> None:
        """Send hvac_mode + target temperature to the right devices."""

        # COOL (split-AC) ------------------------------------------------
        if self._attr_hvac_mode == HVACMode.COOL:
            await self._ensure_mode(self._cool_entity, HVACMode.COOL)
            await self.hass.services.async_call(
                "climate",
                "set_temperature",
                {"entity_id": self._cool_entity, "temperature": sp},
                blocking=False,
            )

        # HEAT (radiator + optional auxiliary AC) ------------------------
        elif self._attr_hvac_mode == HVACMode.HEAT:
            if self._trv_entity:
                await self._ensure_mode(self._trv_entity, HVACMode.HEAT)
                await self.hass.services.async_call(
                    "climate",
                    "set_temperature",
                    {"entity_id": self._trv_entity, "temperature": sp},
                    blocking=False,
                )
            if use_aux and self._aux_entity:
                await self._ensure_mode(self._aux_entity, HVACMode.HEAT)
                await self.hass.services.async_call(
                    "climate",
                    "set_temperature",
                    {"entity_id": self._aux_entity, "temperature": sp},
                    blocking=False,
                )

        # OFF (everything) ----------------------------------------------
        else:
            await self._ensure_mode(self._cool_entity, HVACMode.OFF)
            if self._trv_entity:
                await self._ensure_mode(self._trv_entity, HVACMode.OFF)
            if self._aux_entity and self._aux_entity != self._cool_entity:
                await self._ensure_mode(self._aux_entity, HVACMode.OFF)

    # -----------------------------------------------------------
    async def _ensure_mode(self, eid: str, mode: HVACMode) -> None:
        """Reliably set *hvac_mode* even on devices that resist mode changes."""
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
    """Gather current slider values into a ComfortParams dataclass."""
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
        ua_total   = f("ua_total", PARAMS["ua_total"][-1]),
        q_int      = f("q_int",    PARAMS["q_int"][-1]),
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Register a ThermoAdaptClimate entity for the supplied config entry."""
    zone = entry.data[CONF_NAME]
    params = _load_params_from_helpers(hass, zone)

    coordinator = ThermoAdaptCoordinator(hass, entry, params)
    async_add_entities([ThermoAdaptClimate(hass, entry, coordinator)])

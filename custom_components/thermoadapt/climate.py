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

from .entities import tset_cool, tset_heat, ComfortParams, NUMBER_PARAMS as PARAMS

_LOGGER: Final = logging.getLogger(__name__)

SCAN_INTERVAL: Final = timedelta(seconds=30)
AUX_MARGIN: Final = 1.0  # °C below set-point that triggers auxiliary heat

class ThermoAdaptCoordinator(DataUpdateCoordinator[float]):
    """Pushes a fresh adaptive set-point every SCAN_INTERVAL."""

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
        st = self.hass.states.get(self.entry.data["temp_out"])
        try:
            t_out: float | None = (
                float(st.state)
                if st and st.state not in ("unknown", "unavailable")
                else None
            )
        except ValueError:
            t_out = None

        if t_out is None:
            _LOGGER.warning(
                "[%s] Outdoor sensor unavailable; returning fallback set-point",
                self.entry.data[CONF_NAME],
            )
            return round(self.params.tc_base, 1)

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

class ThermoAdaptClimate(ClimateEntity):
    """One entity per zone; exposes target-temperature and hvac_mode."""

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

        self._zone: str = entry.data[CONF_NAME]
        self._enable_switch = f"switch.thermoadapt_{self._zone}_enabled"
        self._cool_entity: str = entry.data["climate_entity"]
        self._trv_entity: str | None = entry.data.get("trv_entity")
        self._aux_entity: str | None = entry.data.get("aux_entity")

        # Se auxiliar não foi definido, reutiliza climática se suportar HEAT.
        if not self._aux_entity:
            st = hass.states.get(self._cool_entity)
            if st and "heat" in st.attributes.get("hvac_modes", []):
                self._aux_entity = self._cool_entity
                _LOGGER.debug(
                    "[%s] Using %s as auxiliary heater (heat-capable AC)",
                    self._zone,
                    self._cool_entity,
                )

        modes = [HVACMode.OFF, HVACMode.COOL]
        if self._trv_entity or self._aux_entity:
            modes.append(HVACMode.HEAT)
        if "dry" in (hass.states.get(self._cool_entity).attributes.get("hvac_modes", [])):
            modes.append(HVACMode.DRY)
        self._attr_hvac_modes = modes

        # Configuração inicial dos parâmetros.
        self._attr_name = f"ThermoAdapt {self._zone.capitalize()}"
        self._attr_unique_id = f"thermoadapt_{self._zone}"
        self._attr_target_temperature = None
        self._attr_hvac_mode = HVACMode.OFF

    async def async_added_to_hass(self) -> None:
        """Registra callbacks para atualizar a entidade em resposta às mudanças."""
        # Callback para atualizações periódicas.
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )
        # Callback para o switch de habilitação.
        self.async_on_remove(
            async_track_state_change(
                self.hass,
                self._enable_switch,
                lambda *_: self._handle_coordinator_update(),
            )
        )
        # --- NOVO: Inscreva-se para reagir a alterações de outras entidades ---
        entities_to_watch = [
            self.entry.data["temp_in"],
            self.entry.data["temp_out"],
            self.entry.data.get("hum_in"),
            # Se desejar, você pode cadastrar outros inputs (input_number, input_boolean, etc.)
            # Exemplo:
            # "input_boolean.react_sala_ativo",
            # "input_select.react_sala_mode",
        ] + [
            f"number.thermoadapt_{self._zone}_{slug}" for slug in PARAMS.keys()
        ]
        self.async_on_remove(
            async_track_state_change(
                self.hass,
                [eid for eid in entities_to_watch if eid],
                self._handle_entity_update,
            )
        )
        await self.coordinator.async_config_entry_first_refresh()

    @callback
    def _handle_entity_update(self, entity_id, old_state, new_state) -> None:
        """Callback acionado quando uma entidade monitorada muda.
        
        Aqui você pode replicar parte da lógica usada em sua automação manual.
        Por exemplo, pode verificar se determinadas condições (como estado de input_boolean,
        variação de temperatura ou humidade) foram atendidas e, com base nisso, disparar
        mudanças de hvac_mode, setpoint, ou fan_mode chamando os serviços climate.
        """
        # Exemplo simples: se o input boolean 'react_sala_ativo' mudar para 'on', atualiza o clima.
        if entity_id == "input_boolean.react_sala_ativo" and new_state.state == "on":
            self.hass.async_create_task(
                self._apply_mode(self.coordinator.data, use_aux=False)
            )
        # Você pode expandir essa lógica conforme os diferentes gatilhos presentes na sua automação.
        # Lembre-se de usar as funções async_call dos serviços do HA para atualizar o clima.

    @callback
    def _handle_coordinator_update(self) -> None:
        """Chamado quando os sensores ou o switch principal mudam."""
        if not self.hass.states.is_state(self._enable_switch, "on"):
            if self._attr_hvac_mode != HVACMode.OFF:
                self._attr_hvac_mode = HVACMode.OFF
                self.hass.async_create_task(
                    self._apply_mode(self.coordinator.data, use_aux=False)
                )
            self.async_write_ha_state()
            return

        sp: float = self.coordinator.data
        self._attr_target_temperature = sp

        t_in_state = self.hass.states.get(self.entry.data["temp_in"])
        try:
            t_in = float(t_in_state.state) if t_in_state and t_in_state.state not in ("unknown", "unavailable") else None
        except ValueError:
            t_in = None
        if t_in is None:
            _LOGGER.warning("[%s] Indoor sensor unavailable", self._zone)
            return

        previous_mode = self._attr_hvac_mode
        use_aux = False

        if t_in > sp + 0.5:  # Exemplo de deadband estático; ajuste conforme necessidade
            self._attr_hvac_mode = HVACMode.COOL
        elif t_in < sp - 0.5:
            self._attr_hvac_mode = HVACMode.HEAT if self._trv_entity else HVACMode.OFF
            if self._aux_entity and t_in < sp - AUX_MARGIN:
                use_aux = True
        else:
            self._attr_hvac_mode = HVACMode.OFF

        if self._attr_hvac_mode != previous_mode or use_aux:
            self.hass.async_create_task(self._apply_mode(sp, use_aux))

        self.async_write_ha_state()

    async def _apply_mode(self, sp: float, use_aux: bool) -> None:
        """Envia o comando de hvac_mode e temperatura para os dispositivos apropriados."""
        if self._attr_hvac_mode == HVACMode.COOL:
            await self._ensure_mode(self._cool_entity, HVACMode.COOL)
            await self.hass.services.async_call(
                "climate",
                "set_temperature",
                {"entity_id": self._cool_entity, "temperature": sp},
                blocking=False,
            )
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
        else:
            await self._ensure_mode(self._cool_entity, HVACMode.OFF)
            if self._trv_entity:
                await self._ensure_mode(self._trv_entity, HVACMode.OFF)
            if self._aux_entity and self._aux_entity != self._cool_entity:
                await self._ensure_mode(self._aux_entity, HVACMode.OFF)

    async def _ensure_mode(self, eid: str, mode: HVACMode) -> None:
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

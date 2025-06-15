import logging
from datetime import timedelta

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .entities import tset_cool, tset_heat, ComfortParams  # Certifique-se de que esses itens estejam definidos

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)
AUX_MARGIN = 1.0  # Exemplo de margem para acionamento de modo auxiliar

class ThermoAdaptCoordinator(DataUpdateCoordinator):
    """Coordena atualizações do ponto de ajuste (setpoint) adaptativo."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, params: ComfortParams) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"thermoadapt_{entry.data[CONF_NAME]}",
            update_interval=SCAN_INTERVAL,
        )
        self.entry = entry
        self.params = params

    async def _async_update_data(self):
        """Atualiza dados dos sensores e calcula o novo setpoint."""
        sensor_id = self.entry.data.get("temp_out")
        state = self.hass.states.get(sensor_id)
        try:
            t_out = float(state.state) if state and state.state not in ("unknown", "unavailable") else None
        except ValueError:
            t_out = None

        if t_out is None:
            _LOGGER.warning(
                "[%s] Sensor externo indisponível; retornando ponto de ajuste base",
                self.entry.data[CONF_NAME],
            )
            return self.params.tc_base

        # Calcula setpoint usando funções auxiliares
        if t_out > (self.params.tc_base - self.params.q_int / self.params.ua_total):
            sp = tset_cool(t_out, self.params)
        else:
            sp = tset_heat(t_out, self.params)
        return round(sp, 1)

class ThermoAdaptClimate(ClimateEntity):
    """Representa a entidade de clima para ThermoAdapt."""

    _attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, coordinator: ThermoAdaptCoordinator) -> None:
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self._zone = entry.data[CONF_NAME]

        self._attr_name = f"ThermoAdapt {self._zone.capitalize()}"
        self._attr_unique_id = f"thermoadapt_{self._zone}"
        self._attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL, HVACMode.HEAT, HVACMode.DRY]
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_target_temperature = None

    async def async_update(self) -> None:
        """Atualiza a entidade chamando o coordinator."""
        await self.coordinator.async_request_refresh()
        self._attr_target_temperature = self.coordinator.data

    async def async_set_temperature(self, **kwargs):
        """Lógica para definição de temperatura manual, se necessário."""
        temperature = kwargs.get("temperature")
        _LOGGER.debug("Definindo temperatura para %s", temperature)
        self._attr_target_temperature = temperature
        # Aqui você pode chamar serviços ou atualizar dispositivos externos

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> bool:
    """Configura a entidade ThermoAdapt de clima usando a entrada do ConfigFlow."""
    # Prepare os parâmetros de conforto; certifique-se de que os campos existam em entry.data
    cfg = entry.data
    params = ComfortParams(
        tc_base=cfg.get("tc_base", 22.0),
        q_int=cfg.get("q_int", 1.0),
        ua_total=cfg.get("ua_total", 1.0),
        # Adicione outros campos conforme necessário
    )

    coordinator = ThermoAdaptCoordinator(hass, entry, params)
    await coordinator.async_config_entry_first_refresh()

    async_add_entities([ThermoAdaptClimate(hass, entry, coordinator)])
    return True

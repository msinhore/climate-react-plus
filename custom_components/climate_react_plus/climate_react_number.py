from homeassistant.components.number import RestoreNumber
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.const import TEMP_CELSIUS

class ClimateReactNumber(RestoreNumber):
    def __init__(
        self,
        hass: HomeAssistant,
        zone: str,
        param: str,
        name: str,
        initial: float,
        min_value: float,
        max_value: float,
        step: float,
    ) -> None:
        self.hass = hass
        self._zone = zone
        self._param = param

        self._attr_name = name
        self._attr_unique_id = f"climate_react_{zone}_{param}"
        self._attr_object_id = f"climate_react_{zone}_{param}"
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = TEMP_CELSIUS
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_native_value = initial

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (restored := await self.async_get_last_number_data()) is not None:
            self._attr_native_value = restored.native_value

    @property
    def should_poll(self) -> bool:
        return False

    @property
    def native_value(self) -> float:
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()

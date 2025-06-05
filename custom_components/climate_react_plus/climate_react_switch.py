from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

class ClimateReactSwitch(RestoreEntity, SwitchEntity):
    def __init__(self, hass: HomeAssistant, zone: str):
        self.hass = hass
        self._zone = zone

        self._attr_name = f"Climate React {zone} Enabled"
        self._attr_unique_id = f"climate_react_{zone}_enabled"
        self._attr_object_id = f"climate_react_{zone}_enabled"
        self._attr_is_on = True
        self._attr_entity_category = EntityCategory.CONFIG

    async def async_turn_on(self, **kwargs):
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._attr_is_on = last_state.state == "on"

    @property
    def should_poll(self) -> bool:
        return False

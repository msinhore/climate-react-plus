# custom_components/climate_react_plus/number.py
from homeassistant.components.number import NumberEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.const import CONF_NAME

from .const import DOMAIN

async def async_setup_entry(hass: HomeAssistant, entry, async_add_entities):
    zone = entry.data[CONF_NAME]
    zone_data = hass.data[DOMAIN][zone]
    config = zone_data["config"]
    unit = zone_data["unit"]

    entities = [
        ClimateReactNumber(hass, zone, "temp_min", f"{zone} Temp Min", config["min_temp"], 17, 30, 0.1, unit),
        ClimateReactNumber(hass, zone, "temp_max", f"{zone} Temp Max", config["max_temp"], 17, 30, 0.1, unit),
        ClimateReactNumber(hass, zone, "setpoint", f"{zone} Setpoint", config["setpoint"], 17, 30, 1.0, unit),
    ]
    async_add_entities(entities)

class ClimateReactNumber(RestoreEntity, NumberEntity):
    def __init__(self, hass, zone, param, name, initial, min_val, max_val, step, unit):
        self._attr_name = name
        self._attr_unique_id = f"climate_react_{zone}_{param}"
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_entity_category = EntityCategory.CONFIG
        self._attr_native_value = initial

    async def async_added_to_hass(self):
        if (last := await self.async_get_last_state()) is not None:
            self._attr_native_value = float(last.state)

    @property
    def native_value(self):
        return self._attr_native_value

    async def async_set_native_value(self, value):
        self._attr_native_value = value
        self.async_write_ha_state()


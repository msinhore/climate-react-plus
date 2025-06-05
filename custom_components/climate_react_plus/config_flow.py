import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers.selector import selector

from .const import DOMAIN

STEP_USER_SELECT_SCHEMA = {
    vol.Required(CONF_NAME): selector({"text": {}}),
    vol.Required("climate_entity"): selector({
        "entity": {"domain": "climate"}
    }),
    vol.Required("temperature_sensor"): selector({
        "entity": {"domain": "sensor", "device_class": "temperature"}
    }),
}

class ClimateReactPlusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self):
        self._data = {}

    async def async_step_user(self, user_input=None):
        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(STEP_USER_SELECT_SCHEMA)
            )

        self._data.update(user_input)

        climate_state = self.hass.states.get(user_input["climate_entity"])
        hvac_modes = climate_state.attributes.get("hvac_modes", [])
        fan_modes = climate_state.attributes.get("fan_modes", [])

        self._data["hvac_modes"] = hvac_modes
        self._data["fan_modes"] = fan_modes

        return await self.async_step_details()

    async def async_step_details(self, user_input=None):
        hvac_modes = self._data.get("hvac_modes", [])
        fan_modes = self._data.get("fan_modes", [])

        schema = vol.Schema({
            vol.Required("enabled", default=True): bool,
            vol.Required("min_temp", default=20): vol.All(vol.Coerce(float), vol.Range(min=10, max=35)),
            vol.Required("max_temp", default=26): vol.All(vol.Coerce(float), vol.Range(min=10, max=35)),
            vol.Required("setpoint", default=24): vol.All(vol.Coerce(float), vol.Range(min=10, max=35)),
        })

        if hvac_modes:
            schema = schema.extend({
                vol.Optional("mode", default=hvac_modes[0]): vol.In(hvac_modes)
            })

        if fan_modes:
            schema = schema.extend({
                vol.Optional("fan", default=fan_modes[0]): vol.In(fan_modes)
            })

        if user_input is None:
            return self.async_show_form(
                step_id="details",
                data_schema=schema
            )

        self._data.update(user_input)
        return self.async_create_entry(title=self._data[CONF_NAME], data=self._data)

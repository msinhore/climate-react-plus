import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_ENTITY_ID
from homeassistant.core import callback
from homeassistant.helpers.selector import selector
from .const import DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): str,
    vol.Required("climate_entity"): selector({"entity": {"domain": "climate"}}),
    vol.Required("temperature_sensor"): selector({"entity": {"domain": "sensor", "device_class": "temperature"}}),
    vol.Required("enabled_entity"): selector({"entity": {"domain": "input_boolean"}}),
    vol.Required("min_temp_entity"): selector({"entity": {"domain": "input_number"}}),
    vol.Required("max_temp_entity"): selector({"entity": {"domain": "input_number"}}),
    vol.Required("setpoint_entity"): selector({"entity": {"domain": "input_number"}}),
    vol.Optional("mode_entity"): selector({"entity": {"domain": "input_select"}}),
    vol.Optional("fan_entity"): selector({"entity": {"domain": "input_select"}}),
})

class ClimateReactPlusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA
        )

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_NAME, CONF_ENTITY_ID
from .const import DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME): str,
    vol.Required("climate_entity"): str,
    vol.Required("temperature_sensor"): str,
    vol.Required("enabled_entity"): str,
    vol.Required("min_temp_entity"): str,
    vol.Required("max_temp_entity"): str,
    vol.Required("setpoint_entity"): str,
    vol.Optional("mode_entity"): str,
    vol.Optional("fan_entity"): str,
})

@config_entries.HANDLERS.register(DOMAIN)
class ClimateReactPlusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA
        )

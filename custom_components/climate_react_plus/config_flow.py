from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers.selector import (
    selector,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    BooleanSelector,
    SelectSelector,
    SelectSelectorConfig
)
from .const import DOMAIN

class ClimateReactPlusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=None,
            data_schema_ext={
                CONF_NAME: selector({"text": {}}),
                "climate_entity": selector({"entity": {"domain": "climate"}}),
                "temperature_sensor": selector({"entity": {"domain": "sensor"}}),
                "enabled_entity": selector({"entity": {"domain": "input_boolean"}}),
                "min_temp_entity": selector({"entity": {"domain": "input_number"}}),
                "max_temp_entity": selector({"entity": {"domain": "input_number"}}),
                "setpoint_entity": selector({"entity": {"domain": "input_number"}}),
                "mode_entity": selector({"entity": {"domain": "input_select"}}),
                "fan_entity": selector({"entity": {"domain": "input_select"}})
            }
        )

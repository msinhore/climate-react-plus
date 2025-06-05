# File: custom_components/climate_react_plus/climate_react.py

import logging
from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.typing import HomeAssistantType

_LOGGER = logging.getLogger(__name__)

REQUIRED_ENTITIES = [
    "climate_entity",
    "temperature_sensor"
]

class ClimateReactController:
    def __init__(self, hass: HomeAssistantType, zone_name: str, config: dict):
        self.hass = hass
        self.zone = zone_name
        self.config = config
        self._unsub = []

    async def async_initialize(self):
        missing = [k for k in REQUIRED_ENTITIES if k not in self.config]
        if missing:
            _LOGGER.warning("Zone %s missing required config keys: %s", self.zone, missing)
            return

        self._unsub.append(
            async_track_state_change_event(
                self.hass,
                [
                    self.config["temperature_sensor"],
                    self.config.get("enabled_entity"),
                    self.config.get("min_temp_entity"),
                    self.config.get("max_temp_entity"),
                    self.config.get("setpoint_entity"),
                    self.config.get("mode_entity"),
                    self.config.get("fan_entity")
                ],
                self._handle_state_change
            )
        )

        _LOGGER.info("Climate React active for zone: %s", self.zone)

    @callback
    async def _handle_state_change(self, event):
        try:
            temp = float(self.hass.states.get(self.config["temperature_sensor"]).state)
            enabled = self.config.get("enabled_entity")
            if enabled and self.hass.states.get(enabled).state != "on":
                _LOGGER.debug("Zone %s is disabled.", self.zone)
                return

            min_temp = float(self._get_state("min_temp_entity", default="0"))
            max_temp = float(self._get_state("max_temp_entity", default="99"))

            climate = self.config["climate_entity"]

            if temp > max_temp:
                mode = self._get_state("mode_entity", default="cool")
                setpoint = float(self._get_state("setpoint_entity", default="24"))
                fan = self._get_state("fan_entity", default=None)

                _LOGGER.info("[%s] Temp %.1f > max %.1f — turning ON %s", self.zone, temp, max_temp, climate)
                await self.hass.services.async_call("climate", "set_hvac_mode", {
                    "entity_id": climate,
                    "hvac_mode": mode
                })
                await self.hass.services.async_call("climate", "set_temperature", {
                    "entity_id": climate,
                    "temperature": setpoint
                })
                if fan:
                    await self.hass.services.async_call("climate", "set_fan_mode", {
                        "entity_id": climate,
                        "fan_mode": fan
                    })

            elif temp <= min_temp:
                _LOGGER.info("[%s] Temp %.1f <= min %.1f — turning OFF %s", self.zone, temp, min_temp, climate)
                await self.hass.services.async_call("climate", "set_hvac_mode", {
                    "entity_id": climate,
                    "hvac_mode": "off"
                })

        except Exception as e:
            _LOGGER.error("Error processing Climate React zone %s: %s", self.zone, str(e))

    def _get_state(self, key, default=None):
        eid = self.config.get(key)
        if not eid:
            return default
        return self.hass.states.get(eid).state if self.hass.states.get(eid) else default

    async def async_unload(self):
        for unsub in self._unsub:
            unsub()
        self._unsub.clear()

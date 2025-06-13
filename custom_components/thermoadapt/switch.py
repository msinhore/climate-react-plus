"""ThermoAdapt – master enable/disable switch for a single zone.

This helper maps the legacy *input_boolean* to a proper HA SwitchEntity so users
can quickly toggle the control loop (both adaptive and manual) from the UI or
Dashboards.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create a single on/off switch for the ThermoAdapt zone."""

    zone: str = entry.data[CONF_NAME]
    async_add_entities([ThermoAdaptSwitch(zone)])


class ThermoAdaptSwitch(RestoreEntity, SwitchEntity):
    """Enable/Disable ThermoAdapt control for the given zone."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, zone: str) -> None:
        self._attr_unique_id = f"thermoadapt_{zone}_enabled"
        self._attr_name = f"{zone.capitalize()} ThermoAdapt Enabled"
        self._is_on: bool = True  # default ON on first install

    # ------------------------------------------------------------------
    # Restore previous state
    # ------------------------------------------------------------------
    async def async_added_to_hass(self) -> None:
        if (last_state := await self.async_get_last_state()) is not None:
            self._is_on = last_state.state == "on"

    # Properties -------------------------------------------------------
    @property
    def is_on(self) -> bool:  # type: ignore[override]
        return self._is_on

    # Commands ---------------------------------------------------------
    async def async_turn_on(self, **kwargs: Any) -> None:  # noqa: D401
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:  # noqa: D401
        self._is_on = False
        self.async_write_ha_state()


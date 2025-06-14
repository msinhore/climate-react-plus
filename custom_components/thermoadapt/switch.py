# custom_components/thermoadapt/switch.py
"""ThermoAdapt – two configuration switches per zone.
*  <zone> ThermoAdapt Enabled   – master on/off
*  <zone> Adaptive Mode         – toggle adaptive vs. manual set-points
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

_LOGGER = logging.getLogger(__name__)

SWITCHES = {
    "enabled":  ("ThermoAdapt Enabled",  True),
    "adaptive": ("Adaptive Mode",       False),
}


async def async_setup_entry(
    hass, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create two switches for this zone."""
    zone = entry.data[CONF_NAME]
    entities = [ThermoAdaptSwitch(zone, slug, friendly, default)
                for slug, (friendly, default) in SWITCHES.items()]
    async_add_entities(entities)


class ThermoAdaptSwitch(RestoreEntity, SwitchEntity):
    """On/off switch stored in Home-Assistant registry (restored after reboot)."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, zone: str, slug: str, friendly: str, default: bool) -> None:
        _LOGGER.warning(f"Creating ThermoAdaptSwitch: zone={zone}, slug={slug}, friendly={friendly}")
        # ──────────────── identifiers ───────────────────────
        self._attr_unique_id = f"thermoadapt_{zone}_{slug}"

        # Friendly name as displayed in the UI
        self._attr_name = f"ThermoAdapt {zone.capitalize()} {friendly}"

        # Stable entity_id: switch.thermoadapt_<zone>_<slug>
        # (overrides Home Assistant's automatic id generation)
        self._attr_entity_id = f"switch.thermoadapt_{zone}_{slug}"

        # initial on/off state (restored later if available)
        self._is_on = default

    # Restore -----------------------------------------------------------
    async def async_added_to_hass(self) -> None:
        if (last := await self.async_get_last_state()) is not None:
            self._is_on = last.state == "on"

    # Properties --------------------------------------------------------
    @property
    def is_on(self) -> bool:  # type: ignore[override]
        return self._is_on

    # Commands ----------------------------------------------------------
    async def async_turn_on(self, **kwargs: Any) -> None:
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._is_on = False
        self.async_write_ha_state()

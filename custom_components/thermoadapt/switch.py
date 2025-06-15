from .entities import async_setup_entry_switches

async def async_setup_entry(hass, entry, async_add_entities):
    """Setup ThermoAdapt Switch entities for this config entry."""
    await async_setup_entry_switches(hass, entry, async_add_entities)

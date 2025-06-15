from .entities import async_setup_entry_numbers

async def async_setup_entry(hass, entry, async_add_entities):
    """Setup ThermoAdapt Number entities (sliders) for this config entry."""
    await async_setup_entry_numbers(hass, entry, async_add_entities)

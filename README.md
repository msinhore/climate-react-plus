# Climate React Plus

**Smart temperature-based climate control for Home Assistant.**

Climate React Plus automates HVAC entities based on external or internal temperature sensors, with fine control over modes, thresholds and user preferences. It supports Broadlink + SmartIR, Sensibo, Tado, and any standard `climate.*` entity.

## 💡 Features

- Auto on/off based on temperature range
- Configurable:
  - Minimum and maximum temperature thresholds
  - Setpoint temperature (°C or °F)
  - HVAC mode (`cool`, `heat`, `auto`, etc.)
  - Fan level (`auto`, `low`, `medium`, `high`)
- Optional UI card built with Lit + TypeScript
- Multi-zone support (bedroom, office, etc.)
- Local-first — no cloud dependency

## 🧩 Installation via HACS

1. Go to HACS → Integrations → Add custom repository:
   - URL: `https://github.com/msinhore/climate-react-plus`
   - Category: **Integration**
2. Install **Climate React Plus**
3. Restart Home Assistant

> The UI card will be automatically available as a resource in Lovelace.

## ⚙️  Configuration

In your `configuration.yaml` or via UI helpers, each zone uses the following entities:

```yaml
climate_react_plus:
  bedroom:
    climate_entity: climate.bedroom
    temperature_sensor: sensor.bedroom_temperature
    enabled_entity: input_boolean.react_bedroom_enabled
    min_temp_entity: input_number.react_bedroom_temp_min
    max_temp_entity: input_number.react_bedroom_temp_max
    setpoint_entity: input_number.react_bedroom_target
    mode_entity: input_select.react_bedroom_mode
    fan_entity: input_select.react_bedroom_fan
```

## Lovelace Card
The custom card allows full control of the climate logic per zone:
- Toggle automation
- Set temperature range and setpoint
- Select mode and fan level
- Visual feedback on current temperature

To use it in a dashboard:

```yaml
type: module
url: /local/climate-react-card/dist/climate-react-card.js
```

You can include the card using HACS → Frontend if needed.

## Author
Developed by @msinhore — MIT Licensed.


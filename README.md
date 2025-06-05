# Climate React Plus

A smart climate control logic for Home Assistant, based on external temperature sensors and any climate entity (`climate.*`).

**Works with:** Broadlink + SmartIR, Sensibo, Tado, or any compatible HVAC entity.

## Features

- Automatically turns on/off the AC based on ambient temperature
- Configurable min/max thresholds
- Custom target temperature, HVAC mode, and fan mode
- Supports multiple zones (rooms)
- Local and independent — no external cloud required
- Lovelace card for full control

## Installation (via HACS)

1. Add this repository to HACS as a custom repository (type: integration)
2. Install `climate-react-plus`
3. Restart Home Assistant

## Configuration

Each zone is configured with:

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

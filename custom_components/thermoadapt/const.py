from __future__ import annotations

# -----------------------------------------------------------------------------
# Core identifiers
# -----------------------------------------------------------------------------
DOMAIN: str = "thermoadapt"

CONF_NAME = "name"

# Config-flow keys (UI)
CONF_TEMP_IN:        str = "temp_in"
CONF_HUM_IN:         str = "hum_in"
CONF_TEMP_OUT:       str = "temp_out"
CONF_CLIMATE_ENTITY: str = "climate_entity"
CONF_TRV_ENTITY:     str = "trv_entity"

# Default comfort parameters (Dear & Brager category II)
DEF_TEMP_MIN:   float = 23.0  # °C – lower comfort threshold in manual mode
DEF_TEMP_MAX:   float = 27.0  # °C – upper comfort threshold in manual mode
DEF_SETPOINT:   float = 25.0  # °C – fixed set-point when adaptive algo is off
DEF_DEADBAND:   float = 0.5   # °C – neutral zone before switching
DEF_HUMID_MAX:  int   = 65    # %  – triggers *dry* mode above this
DEF_HEAT_BASE:  float = 20.5  # °C – T_base for heating curve
DEF_K_HEAT:     float = 0.18  # slope for adaptive heating (Dear & Brager 2001)

# Update interval for coordinator
SCAN_INTERVAL_SEC: int = 30

DEFAULTS: dict[str, float | int] = {
    "temp_min":   DEF_TEMP_MIN,
    "temp_max":   DEF_TEMP_MAX,
    "setpoint":   DEF_SETPOINT,
    "deadband":   DEF_DEADBAND,
    "humid_max":  DEF_HUMID_MAX,
    "heat_base":  DEF_HEAT_BASE,
    "k_heat":     DEF_K_HEAT,
}

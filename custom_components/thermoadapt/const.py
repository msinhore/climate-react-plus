"""ThermoAdapt – Constants and defaults

This file centralises identifiers that are used across the custom component so
we avoid string-litter throughout the code-base.  Terms match the original
Dear & Brager papers (e.g. *dead-band*, *k_heat*, *UA*, *Q_int*).
"""

from __future__ import annotations

# -----------------------------------------------------------------------------
# Core identifiers
# -----------------------------------------------------------------------------
DOMAIN: str = "thermoadapt"
LEGACY_DOMAIN: str = "climate_react_plus"  # ← kept for one release cycle

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

# Helper suffixes used to auto-generate input_numbers / booleans
HELPER_SUFFIXES = [
    "temp_min",
    "temp_max",
    "setpoint",
    "deadband",
    "humid_max",
    "heat_base",
    "k_heat",
    "ativo",     # master enable (switch)
    "dinamico",  # adaptive algorithm toggle
]

# Update interval for coordinator
SCAN_INTERVAL_SEC: int = 30


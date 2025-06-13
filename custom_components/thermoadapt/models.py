# custom_components/thermoadapt/models.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass(slots=True)
class ComfortParams:
    """All adaptive-comfort coefficients for a single zone."""
    tc_base: float = 25.5      # Base set-point (cool)
    tc_min:  float = 23.0
    th_base: float = 20.5      # Base set-point (heat)
    k_heat:  float = 0.18
    deadband_cool: float = 0.5
    deadband_heat: float = 0.5
    ua_total:  float = 30.0    # W / K
    q_int:    float = 200.0    # W
    humid_max: int   = 65

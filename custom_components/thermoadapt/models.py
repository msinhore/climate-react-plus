from dataclasses import dataclass

@dataclass
class ComfortParams:
    tc_base: float
    tc_min: float
    th_base: float
    k_heat: float
    deadband_cool: float
    deadband_heat: float
    humid_max: int
    ua_total: float
    q_int: float

"""ThermoAdapt – helper functions

* Adaptive-comfort equations (Dear & Brager)
* Utility to auto-create missing input_number / input_boolean helpers so the
  user can install via UI without editing YAML.
"""

from __future__ import annotations

import logging
from typing import Dict

from homeassistant.core import HomeAssistant

from .number import PARAMS
from .const import DOMAIN, HELPER_SUFFIXES

_LOGGER = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Equations – used by ThermoAdaptCoordinator
# -----------------------------------------------------------------------------

def tset_cool(t_out: float, p) -> float:  # p: ComfortParams or Mapping
    """Adaptive cooling set-point (Dear & Brager 1998, Eq. 7)."""
    t_bal = p.tc_base - p.q_int / p.ua_total
    k_cool = (p.tc_base - p.tc_min) / (t_out - t_bal) if t_out > t_bal else 0
    return p.tc_base if t_out <= t_bal else p.tc_base - k_cool * (t_out - t_bal)


def tset_heat(t_out: float, p) -> float:  # p: ComfortParams or Mapping
    """Adaptive heating set-point (Dear & Brager 2001)."""
    t_bal = p.th_base - p.q_int / p.ua_total
    return p.th_base if t_out >= t_bal else p.th_base + p.k_heat * (t_bal - t_out)

# -----------------------------------------------------------------------------
# Helper creation – makes onboarding 100 % UI-based
# -----------------------------------------------------------------------------

async def ensure_helpers(hass: HomeAssistant, zone: str) -> None:
    """Create sliders and toggles if they do not yet exist.

    Args:
        hass: Home Assistant instance
        zone: prefix used for this zone (e.g. "quarto")
    """

    # Build map slug -> default & meta from PARAMS (input_number) and
    # HELPER_SUFFIXES for booleans.
    to_create: Dict[str, Dict] = {}

    # Numeric sliders ---------------------------------------------------
    for slug, (_friendly, v_min, v_max, step, _uom, default) in PARAMS.items():
        eid = f"input_number.thermoadapt_{zone}_{slug}"
        if eid not in hass.states.async_entity_ids():
            to_create[eid] = {
                "service": "input_number/create",
                "data": {
                    "name": f"{zone.capitalize()} {slug}",
                    "min": v_min,
                    "max": v_max,
                    "step": step,
                    "initial": default,
                    "unit_of_measurement": _uom if _uom else None,
                    "entity_id": eid,
                },
            }

    # Boolean toggles ----------------------------------------------------
    for slug in ("ativo", "dinamico"):
        eid = f"input_boolean.thermoadapt_{zone}_{slug}"
        if eid not in hass.states.async_entity_ids():
            to_create[eid] = {
                "service": "input_boolean/create",
                "data": {
                    "name": f"{zone.capitalize()} {slug}",
                    "initial": slug == "ativo",  # enabled by default
                    "entity_id": eid,
                },
            }

    # Call creation services -------------------------------------------
    for eid, meta in to_create.items():
        domain, service = meta["service"].split("/")
        _LOGGER.debug("Creating helper %s via %s.%s", eid, domain, service)
        try:
            await hass.services.async_call(domain, service, meta["data"], blocking=True)
        except Exception as exc:  # pragma: no cover
            _LOGGER.error("Could not create helper %s: %s", eid, exc)

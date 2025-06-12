"""Duplex service load calculator."""

from dataclasses import asdict
from math import ceil
from typing import Any, Dict, Tuple

from ..models import Dwelling
from ..utils.breakers import next_standard_breaker


def _unit_loads(dw: Dwelling) -> Tuple[int, int, Dict[str, int]]:
    """Return tuple of (base_watts_without_heat_ac, heat_ac_watts, details)."""
    details: Dict[str, int] = {}

    basic_load = 5000
    details["basic_load"] = basic_load
    if dw.floor_area_m2 > 90:
        extra_area = dw.floor_area_m2 - 90
        extra = ceil(extra_area / 90) * 1000
        basic_load += extra
        details["extra_area_load"] = extra

    range_load = 0
    if dw.has_range:
        range_load = 6000 if dw.range_kw <= 12 else int(dw.range_kw * 1000)
    details["range_load"] = range_load
    ev_load = dw.ev_amps * 240 if dw.has_ev else 0
    details["ev_load"] = ev_load
    dryer_load = int((dw.dryer_kw or 0) * 1000 * 0.25)
    details["dryer_load"] = dryer_load
    wh_load = int((dw.water_heater_kw or 0) * 1000 * 0.25)
    details["wh_load"] = wh_load
    extra_load = 0
    if dw.extra_loads:
        extra_load = int(sum(kW for _lbl, kW in dw.extra_loads) * 1000 * 0.25)
    details["extra_load"] = extra_load
    heat_ac = int(max(dw.heat_kw or 0, dw.ac_kw or 0) * 1000)
    details["heat_ac"] = heat_ac

    base = basic_load + range_load + ev_load + dryer_load + wh_load + extra_load
    details["base_without_heat_ac"] = base
    details["total_watts"] = base + heat_ac
    return base, heat_ac, details


def calculate_duplex_demand(a: Dwelling, b: Dwelling) -> Dict[str, Any]:
    """Calculate service demand for a duplex."""
    base_a, heat_a, det_a = _unit_loads(a)
    base_b, heat_b, det_b = _unit_loads(b)

    if base_a >= base_b:
        combined = base_a + int(base_b * 0.65)
        combined_detail = {
            "base_from_largest": base_a,
            "0.65_of_smaller": int(base_b * 0.65),
        }
    else:
        combined = base_b + int(base_a * 0.65)
        combined_detail = {
            "base_from_largest": base_b,
            "0.65_of_smaller": int(base_a * 0.65),
        }

    total = combined + heat_a + heat_b
    amps = total / 240
    breaker = next_standard_breaker(amps)

    details = {
        "unit_a": det_a,
        "unit_b": det_b,
        "combined_base": combined_detail,
        "heat_a": heat_a,
        "heat_b": heat_b,
        "total_watts": total,
    }

    return {
        "watts": total,
        "amps": amps,
        "suggested_breaker": breaker,
        "inputs": {"unit_a": asdict(a), "unit_b": asdict(b)},
        "details": details,
    }

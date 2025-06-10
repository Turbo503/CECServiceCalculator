"""Duplex service load calculator."""
from dataclasses import asdict
from math import ceil

from ..models import Dwelling
from ..utils.breakers import next_standard_breaker


def _unit_loads(dw: Dwelling) -> tuple[int, int]:
    """Return tuple of (base_watts_without_heat_ac, heat_ac_watts)."""
    basic_load = 5000
    if dw.floor_area_m2 > 90:
        extra_area = dw.floor_area_m2 - 90
        basic_load += ceil(extra_area / 90) * 1000

    range_load = 6000 if dw.range_kw <= 12 else int(dw.range_kw * 1000)
    ev_load = dw.ev_amps * 240 if dw.has_ev else 0
    dryer_load = int((dw.dryer_kw or 0) * 1000 * 0.25)
    wh_load = int((dw.water_heater_kw or 0) * 1000 * 0.25)
    heat_ac = max(dw.heat_kw or 0, dw.ac_kw or 0) * 1000

    base = basic_load + range_load + ev_load + dryer_load + wh_load
    return base, int(heat_ac)


def calculate_duplex_demand(a: Dwelling, b: Dwelling) -> dict:
    """Calculate service demand for a duplex."""
    base_a, heat_a = _unit_loads(a)
    base_b, heat_b = _unit_loads(b)

    if base_a >= base_b:
        total = base_a + int(base_b * 0.65)
    else:
        total = base_b + int(base_a * 0.65)

    total += heat_a + heat_b
    amps = total / 240
    breaker = next_standard_breaker(amps)

    return {
        "watts": total,
        "amps": amps,
        "suggested_breaker": breaker,
        "inputs": {"unit_a": asdict(a), "unit_b": asdict(b)},
    }

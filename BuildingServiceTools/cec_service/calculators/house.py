"""House service load calculator."""
from dataclasses import asdict
from math import ceil

from ..models import Dwelling
from ..utils.breakers import next_standard_breaker


def calculate_demand(dw: Dwelling) -> dict:
    """Calculate service demand for a single dwelling unit."""
    basic_load = 5000
    if dw.floor_area_m2 > 90:
        extra_area = dw.floor_area_m2 - 90
        basic_load += ceil(extra_area / 90) * 1000

    heat_ac = max(dw.heat_kw or 0, dw.ac_kw or 0) * 1000
    range_load = 6000 if dw.range_kw <= 12 else int(dw.range_kw * 1000)
    ev_load = dw.ev_amps * 240 if dw.has_ev else 0
    dryer_load = int((dw.dryer_kw or 0) * 1000 * 0.25)
    wh_load = int((dw.water_heater_kw or 0) * 1000 * 0.25)

    total_watts = basic_load + heat_ac + range_load + ev_load + dryer_load + wh_load
    amps = total_watts / 240
    breaker = next_standard_breaker(amps)

    return {
        "watts": total_watts,
        "amps": amps,
        "suggested_breaker": breaker,
        "inputs": asdict(dw),
    }

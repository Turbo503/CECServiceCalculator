"""House service load calculator."""
from dataclasses import asdict
from math import ceil, sqrt
from typing import Any, Dict

from ..models import Dwelling
from ..utils.breakers import next_standard_breaker


def calculate_demand(dw: Dwelling, volts: int = 240, phases: int = 1) -> Dict[str, Any]:
    """Calculate service demand for a single dwelling unit."""
    details: Dict[str, int] = {}

    basic_load = 5000
    details["basic_load"] = basic_load
    if dw.floor_area_m2 > 90:
        extra_area = dw.floor_area_m2 - 90
        extra = ceil(extra_area / 90) * 1000
        basic_load += extra
        details["extra_area_load"] = extra

    heat_ac = int(max(dw.heat_kw or 0, dw.ac_kw or 0) * 1000)
    details["heat_ac"] = heat_ac
    range_load = 6000 if dw.range_kw <= 12 else int(dw.range_kw * 1000)
    details["range_load"] = range_load
    ev_load = dw.ev_amps * 240 if dw.has_ev else 0
    details["ev_load"] = ev_load
    dryer_load = int((dw.dryer_kw or 0) * 1000 * 0.25)
    details["dryer_load"] = dryer_load
    wh_load = int((dw.water_heater_kw or 0) * 1000 * 0.25)
    details["wh_load"] = wh_load

    total_watts = basic_load + heat_ac + range_load + ev_load + dryer_load + wh_load
    details["total_watts"] = total_watts
    divisor = volts if phases == 1 else volts * sqrt(3)
    amps = total_watts / divisor
    breaker = next_standard_breaker(amps)
    calc = f"{volts}" if phases == 1 else f"{volts} * \u221a3"

    return {
        "watts": total_watts,
        "amps": amps,
        "calculation": calc,
        "suggested_breaker": breaker,
        "inputs": asdict(dw),
        "details": details,
    }

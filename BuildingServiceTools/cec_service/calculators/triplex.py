"""Triplex service load calculator."""

from dataclasses import asdict
from math import ceil, sqrt
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

    range_load = 6000 if dw.range_kw <= 12 else int(dw.range_kw * 1000)
    details["range_load"] = range_load
    ev_load = dw.ev_amps * 240 if dw.has_ev else 0
    details["ev_load"] = ev_load
    dryer_load = int((dw.dryer_kw or 0) * 1000 * 0.25)
    details["dryer_load"] = dryer_load
    wh_load = int((dw.water_heater_kw or 0) * 1000 * 0.25)
    details["wh_load"] = wh_load
    heat_ac = int(max(dw.heat_kw or 0, dw.ac_kw or 0) * 1000)
    details["heat_ac"] = heat_ac

    base = basic_load + range_load + ev_load + dryer_load + wh_load
    details["base_without_heat_ac"] = base
    return base, heat_ac, details


def calculate_triplex_demand(a: Dwelling, b: Dwelling, c: Dwelling, volts: int = 240, phases: int = 1) -> Dict[str, Any]:
    """Calculate service demand for a triplex."""
    units = [a, b, c]
    loads = [_unit_loads(u) for u in units]
    bases = [b for b, _h, _d in loads]

    # Largest base taken at 100%, others at 65%
    sorted_indices = sorted(range(3), key=lambda i: bases[i], reverse=True)
    largest_idx = sorted_indices[0]
    combined = bases[largest_idx]
    combined_detail = {"base_from_largest": bases[largest_idx]}
    for idx in sorted_indices[1:]:
        combined += int(bases[idx] * 0.65)
        combined_detail[f"0.65_of_unit_{idx + 1}"] = int(bases[idx] * 0.65)

    total_heat = sum(load[1] for load in loads)
    total_watts = combined + total_heat
    divisor = volts if phases == 1 else volts * sqrt(3)
    amps = total_watts / divisor
    breaker = next_standard_breaker(amps)

    details = {
        "unit_a": loads[0][2],
        "unit_b": loads[1][2],
        "unit_c": loads[2][2],
        "combined_base": combined_detail,
        "total_heat": total_heat,
        "total_watts": total_watts,
    }

    return {
        "watts": total_watts,
        "amps": amps,
        "calculation": f"{volts}" if phases == 1 else f"{volts} * \u221a3",
        "suggested_breaker": breaker,
        "inputs": {"unit_a": asdict(a), "unit_b": asdict(b), "unit_c": asdict(c)},
        "details": details,
    }

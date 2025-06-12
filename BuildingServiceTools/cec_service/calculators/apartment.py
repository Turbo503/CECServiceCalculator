"""Multi-unit apartment service load calculator."""

from dataclasses import asdict
from math import ceil
from typing import Any, Dict, List, Tuple

from ..models import Dwelling
from ..utils.breakers import next_standard_breaker


def _unit_loads(dw: Dwelling) -> Tuple[int, int, Dict[str, int]]:
    """Return tuple of (base_without_heat_ac, heat_ac_load, details)."""
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


def calculate_multi_demand(units: List[Dwelling]) -> Dict[str, Any]:
    """Calculate service demand for multiple dwelling units."""
    if not units:
        raise ValueError("No units provided")
    loads = [_unit_loads(u) for u in units]
    bases = [b for b, _h, _d in loads]
    sorted_indices = sorted(range(len(units)), key=lambda i: bases[i], reverse=True)
    largest = sorted_indices[0]
    combined = bases[largest]
    combined_detail = {"base_from_largest": bases[largest]}
    for idx in sorted_indices[1:]:
        combined += int(bases[idx] * 0.65)
        combined_detail[f"0.65_of_unit_{idx + 1}"] = int(bases[idx] * 0.65)

    total_heat = sum(h for _b, h, _d in loads)
    total_watts = combined + total_heat
    amps = total_watts / 240
    breaker = next_standard_breaker(amps)

    detail_units = {f"unit_{i + 1}": d for i, (_b, _h, d) in enumerate(loads)}
    inputs = {f"unit_{i + 1}": asdict(u) for i, u in enumerate(units)}

    details = {
        **detail_units,
        "combined_base": combined_detail,
        "total_heat": total_heat,
        "total_watts": total_watts,
    }

    return {
        "watts": total_watts,
        "amps": amps,
        "suggested_breaker": breaker,
        "inputs": inputs,
        "details": details,
    }

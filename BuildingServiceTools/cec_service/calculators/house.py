"""House service load calculator."""
from dataclasses import asdict
from math import ceil
from typing import Any, Dict, List, Tuple

from ..models import Dwelling
from ..utils.breakers import next_standard_breaker


def _unit_details(dw: Dwelling) -> Tuple[int, int, Dict[str, int], List[str]]:
    """Return base load, heat/AC watts, numeric details and explanation lines."""
    details: Dict[str, int] = {}
    steps: List[str] = []

    basic_load = 5000
    details["basic_load"] = basic_load
    steps.append("Basic load: 5000 W")
    if dw.floor_area_m2 > 90:
        extra_area = dw.floor_area_m2 - 90
        blocks = ceil(extra_area / 90)
        extra = blocks * 1000
        basic_load += extra
        details["extra_area_load"] = extra
        steps.append(
            f"Extra area {extra_area:.0f} m² -> {blocks} x 1000 W = {extra} W"
        )

    range_load = 6000 if dw.range_kw <= 12 else int(dw.range_kw * 1000)
    details["range_load"] = range_load
    steps.append(f"Range: {dw.range_kw} kW -> {range_load} W")

    ev_load = dw.ev_amps * 240 if dw.has_ev else 0
    details["ev_load"] = ev_load
    if dw.has_ev:
        steps.append(f"EVSE: {dw.ev_amps} A x 240 V = {ev_load} W")
    else:
        steps.append("EVSE: not included")

    dryer_kw = dw.dryer_kw or 0
    dryer_load = int(dryer_kw * 1000 * 0.25)
    details["dryer_load"] = dryer_load
    steps.append(
        f"Dryer: {dryer_kw * 1000:.0f} W x 25% = {dryer_load} W"
    )

    wh_kw = dw.water_heater_kw or 0
    wh_load = int(wh_kw * 1000 * 0.25)
    details["wh_load"] = wh_load
    steps.append(
        f"Water heater: {wh_kw * 1000:.0f} W x 25% = {wh_load} W"
    )

    heat_ac_kw = max(dw.heat_kw or 0, dw.ac_kw or 0)
    heat_ac = int(heat_ac_kw * 1000)
    details["heat_ac"] = heat_ac
    steps.append(f"Heat/AC: {heat_ac_kw} kW x 1000 = {heat_ac} W")

    base = basic_load + range_load + ev_load + dryer_load + wh_load
    details["base_without_heat_ac"] = base
    steps.append(f"Base without heat/AC: {base} W")

    return base, heat_ac, details, steps


def calculate_demand(dw: Dwelling) -> Dict[str, Any]:
    """Calculate service demand for a single dwelling unit."""
    base, heat_ac, details, steps = _unit_details(dw)

    total_watts = base + heat_ac
    details["total_watts"] = total_watts
    steps.append(f"Total = {base} + {heat_ac} = {total_watts} W")
    amps = total_watts / 240
    breaker = next_standard_breaker(amps)

    return {
        "watts": total_watts,
        "amps": amps,
        "suggested_breaker": breaker,
        "inputs": asdict(dw),
        "details": details,
        "steps": steps,
    }

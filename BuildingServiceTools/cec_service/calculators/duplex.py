"""Duplex service load calculator."""
from dataclasses import asdict
from typing import Any, Dict, List, Tuple

from ..models import Dwelling
from ..utils.breakers import next_standard_breaker
from .house import _unit_details


def _unit_loads(dw: Dwelling) -> Tuple[int, int, Dict[str, int], List[str]]:
    """Wrapper around :func:`_unit_details` for duplex."""
    return _unit_details(dw)


def calculate_duplex_demand(a: Dwelling, b: Dwelling) -> Dict[str, Any]:
    """Calculate service demand for a duplex."""
    base_a, heat_a, det_a, steps_a = _unit_loads(a)
    base_b, heat_b, det_b, steps_b = _unit_loads(b)

    steps: List[str] = []
    if base_a >= base_b:
        combined = base_a + int(base_b * 0.65)
        combined_detail = {
            "base_from_largest": base_a,
            "0.65_of_smaller": int(base_b * 0.65),
        }
        steps.append(
            f"Combined base: {base_a} + 65% of {base_b} = {combined} W"
        )
    else:
        combined = base_b + int(base_a * 0.65)
        combined_detail = {
            "base_from_largest": base_b,
            "0.65_of_smaller": int(base_a * 0.65),
        }
        steps.append(
            f"Combined base: {base_b} + 65% of {base_a} = {combined} W"
        )

    total = combined + heat_a + heat_b
    steps.extend([
        f"Unit A heat/AC: {heat_a} W",
        f"Unit B heat/AC: {heat_b} W",
        f"Total = {combined} + {heat_a} + {heat_b} = {total} W",
    ])
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
        "steps": steps_a + steps_b + steps,
    }

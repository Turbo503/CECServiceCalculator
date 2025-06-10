"""Triplex service load calculator."""
from dataclasses import asdict
from typing import Any, Dict, List, Tuple

from ..models import Dwelling
from ..utils.breakers import next_standard_breaker
from .house import _unit_details


def _unit_loads(dw: Dwelling) -> Tuple[int, int, Dict[str, int], List[str]]:
    """Wrapper around :func:`_unit_details` for triplex."""
    return _unit_details(dw)


def calculate_triplex_demand(a: Dwelling, b: Dwelling, c: Dwelling) -> Dict[str, Any]:
    """Calculate service demand for a triplex."""
    base_a, heat_a, det_a, steps_a = _unit_loads(a)
    base_b, heat_b, det_b, steps_b = _unit_loads(b)
    base_c, heat_c, det_c, steps_c = _unit_loads(c)

    bases: List[Tuple[str, int]] = [("A", base_a), ("B", base_b), ("C", base_c)]
    bases.sort(key=lambda x: x[1], reverse=True)
    largest_name, largest_base = bases[0]
    mid_name, mid_base = bases[1]
    small_name, small_base = bases[2]

    combined = largest_base + int(mid_base * 0.65) + int(small_base * 0.65)
    steps: List[str] = [
        f"Combined base: {largest_name} {largest_base} + 65% of {mid_name} {mid_base} + 65% of {small_name} {small_base} = {combined} W"
    ]

    total = combined + heat_a + heat_b + heat_c
    steps.extend(
        [
            f"Unit A heat/AC: {heat_a} W",
            f"Unit B heat/AC: {heat_b} W",
            f"Unit C heat/AC: {heat_c} W",
            f"Total = {combined} + {heat_a} + {heat_b} + {heat_c} = {total} W",
        ]
    )
    amps = total / 240
    breaker = next_standard_breaker(amps)

    details = {
        "unit_a": det_a,
        "unit_b": det_b,
        "unit_c": det_c,
        "combined_base": {
            "largest": {largest_name: largest_base},
            "0.65_of_mid": int(mid_base * 0.65),
            "0.65_of_small": int(small_base * 0.65),
        },
        "heat_a": heat_a,
        "heat_b": heat_b,
        "heat_c": heat_c,
        "total_watts": total,
    }

    return {
        "watts": total,
        "amps": amps,
        "suggested_breaker": breaker,
        "inputs": {"unit_a": asdict(a), "unit_b": asdict(b), "unit_c": asdict(c)},
        "details": details,
        "steps": steps_a + steps_b + steps_c + steps,
    }

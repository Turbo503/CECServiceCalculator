"""Data models for CEC service calculations."""
from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class Dwelling:
    """Representation of a dwelling unit."""

    floor_area_m2: float
    heat_kw: Optional[float]
    ac_kw: Optional[float]
    range_kw: float = 12.0
    has_range: bool = True
    dryer_kw: Optional[float] = None
    water_heater_kw: Optional[float] = None
    # List of (label, kW) for other appliances >1.5kW
    extra_loads: Optional[list[tuple[str, float]]] = None
    has_ev: bool = False
    ev_amps: int = 32

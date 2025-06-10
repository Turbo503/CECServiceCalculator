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
    dryer_kw: Optional[float] = None
    water_heater_kw: Optional[float] = None
    has_ev: bool = False
    ev_amps: int = 32

#!/usr/bin/env python3
"""Command line service load calculator."""
from __future__ import annotations

import argparse
import sys
from math import ceil, sqrt
from pathlib import Path
from typing import List

# Allow imports when run from repo root
sys.path.append(str(Path(__file__).resolve().parent / "BuildingServiceTools"))

from cec_service.models import Dwelling
from cec_service.utils.pdf import simple_pdf_table

BASE_LOAD_RULE = "8-200(1)(a)(i)"
EXTRA_AREA_RULE = "8-200(1)(a)(ii)"
RANGE_RULE = "8-200(1)(a)(iv)"
EVSE_RULE = "8-106(10)"
DRYER_RULE = "8-200(1)(a)(vi)"
WATER_RULE = "8-200(1)(a)(vi)"
HEAT_AC_RULE = "8-202(1)(b)"
TOTAL_RULE = "8-104(1)"


def _fmt(label: str, value: str, rule: str | None, show: bool) -> str:
    return f"{label}: {value}" + (f"  (CEC {rule})" if show and rule else "")


def _row(label: str, value: str, rule: str | None, show: bool) -> tuple[str, str]:
    left = f"{label}: {value}"
    right = f"CEC {rule}" if show and rule else ""
    return left, right


def calculate_with_rules(dw: Dwelling, voltage: float, three_phase: bool, show_rules: bool) -> dict:
    lines: List[str] = []
    rows: List[tuple[str, str]] = []

    basic_load = 5000
    lines.append(_fmt("Base load", f"{basic_load} W", BASE_LOAD_RULE, show_rules))
    rows.append(_row("Base load", f"{basic_load} W", BASE_LOAD_RULE, show_rules))

    if dw.floor_area_m2 > 90:
        extra_area = dw.floor_area_m2 - 90
        units = ceil(extra_area / 90)
        extra = units * 1000
        line_val = f"({extra_area:.0f} m²/90 -> {units}) x 1000 = {extra} W"
        lines.append(_fmt("Extra area", line_val, EXTRA_AREA_RULE, show_rules))
        rows.append(_row("Extra area", line_val, EXTRA_AREA_RULE, show_rules))
        basic_load += extra

    range_w = 6000 if dw.range_kw <= 12 else int(dw.range_kw * 1000)
    lines.append(_fmt("Range", f"{range_w} W", RANGE_RULE, show_rules))
    rows.append(_row("Range", f"{range_w} W", RANGE_RULE, show_rules))

    ev_load = dw.ev_amps * voltage if dw.has_ev else 0
    if dw.has_ev:
        line_val = f"{dw.ev_amps} A x {voltage} V = {ev_load} W"
        lines.append(_fmt("EVSE", line_val, EVSE_RULE, show_rules))
        rows.append(_row("EVSE", line_val, EVSE_RULE, show_rules))

    dryer_load = int((dw.dryer_kw or 0) * 1000 * 0.25)
    if dw.dryer_kw:
        line_val = f"{dw.dryer_kw*1000:.0f} W x 25% = {dryer_load} W"
        lines.append(_fmt("Dryer", line_val, DRYER_RULE, show_rules))
        rows.append(_row("Dryer", line_val, DRYER_RULE, show_rules))

    wh_load = int((dw.water_heater_kw or 0) * 1000 * 0.25)
    if dw.water_heater_kw:
        line_val = f"{dw.water_heater_kw*1000:.0f} W x 25% = {wh_load} W"
        lines.append(_fmt("Water Heater", line_val, WATER_RULE, show_rules))
        rows.append(_row("Water Heater", line_val, WATER_RULE, show_rules))

    heat_ac = int(max(dw.heat_kw or 0, dw.ac_kw or 0) * 1000)
    line_val = f"max({(dw.heat_kw or 0)*1000:.0f}, {(dw.ac_kw or 0)*1000:.0f}) = {heat_ac} W"
    lines.append(_fmt("Heat/AC", line_val, HEAT_AC_RULE, show_rules))
    rows.append(_row("Heat/AC", line_val, HEAT_AC_RULE, show_rules))

    total_watts = basic_load + range_w + ev_load + dryer_load + wh_load + heat_ac
    lines.append(_fmt("Total Watts", f"{total_watts} W", TOTAL_RULE, show_rules))
    rows.append(_row("Total Watts", f"{total_watts} W", TOTAL_RULE, show_rules))

    if three_phase:
        amps = total_watts / (voltage * sqrt(3))
        calc = f"{total_watts} W / ({voltage} V x sqrt(3)) = {amps:.1f} A"
        lines.append(f"Amps: {calc}")
        rows.append(("Amps", calc))
    else:
        amps = total_watts / voltage
        calc = f"{total_watts} W / {voltage} V = {amps:.1f} A"
        lines.append(f"Amps: {calc}")
        rows.append(("Amps", calc))

    result = {"watts": total_watts, "amps": amps, "lines": lines, "rows": rows}
    return result


def main() -> None:
    p = argparse.ArgumentParser(description="CEC Service Load Calculator")
    p.add_argument("floor_area", type=float, help="Floor area in square meters")
    p.add_argument("--heat", type=float, default=0.0, help="Heating load in watts")
    p.add_argument("--ac", type=float, help="AC load in watts")
    p.add_argument("--range", dest="range_w", type=float, default=12000.0, help="Range load in watts")
    p.add_argument("--dryer", type=float, help="Dryer load in watts")
    p.add_argument("--water-heater", type=float, help="Water heater load in watts")
    p.add_argument("--ev-amps", type=int, default=32, help="EVSE current in amps")
    p.add_argument("--no-evse", action="store_true", help="Exclude EVSE load")
    p.add_argument("--three-phase", action="store_true", help="Use 3-phase calculation (208 V)")
    p.add_argument("--pdf", help="Path to export results as PDF")
    p.add_argument("--show-rules", action="store_true", help="Include CEC rule references")
    p.add_argument("--hvac-type", choices=["heat-pump", "heating-ac"], default="heat-pump", help="HVAC system type")
    args = p.parse_args()

    ac_w = args.ac if args.hvac_type == "heating-ac" else None
    dw = Dwelling(
        floor_area_m2=args.floor_area,
        heat_kw=args.heat / 1000 if args.heat else None,
        ac_kw=ac_w / 1000 if ac_w else None,
        range_kw=args.range_w / 1000,
        dryer_kw=args.dryer / 1000 if args.dryer else None,
        water_heater_kw=args.water_heater / 1000 if args.water_heater else None,
        has_ev=not args.no_evse,
        ev_amps=args.ev_amps,
    )

    voltage = 208 if args.three_phase else 240
    result = calculate_with_rules(dw, voltage, args.three_phase, args.show_rules)
    for line in result["lines"]:
        print(line)

    if args.pdf:
        simple_pdf_table(result["rows"], args.pdf)


if __name__ == "__main__":
    main()

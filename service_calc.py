#!/usr/bin/env python3
"""Command line service load calculator with rule references."""
from __future__ import annotations

from argparse import ArgumentParser
from math import ceil, sqrt

BASE_LOAD_RULE = "8-200(1)(a)(i)"
EXTRA_AREA_RULE = "8-200(1)(a)(ii)"
RANGE_RULE = "8-200(1)(a)(iv)"
EVSE_RULE = "8-106(10)"
DRYER_RULE = "8-200(1)(a)(vi)"
WATER_RULE = "8-200(1)(a)(vi)"
HEAT_AC_RULE = "8-202(1)(b)"
TOTAL_RULE = "8-104(1)"


def step(label: str, value: str, rule: str, show: bool, lines: list[str]) -> None:
    text = f"{label}: {value}"
    if show:
        text += f"  (CEC {rule})"
    lines.append(text)


def main() -> None:
    ap = ArgumentParser(description="Calculate dwelling service load")
    ap.add_argument("--floor", type=float, required=True, help="Floor area in m²")
    ap.add_argument("--heat", type=float, default=0.0, help="Heating load in watts")
    ap.add_argument("--ac", type=float, default=0.0, help="AC load in watts")
    ap.add_argument("--range", type=float, default=12000.0, dest="range_", help="Range load in watts")
    ap.add_argument("--dryer", type=float, default=0.0, help="Dryer load in watts")
    ap.add_argument("--water", type=float, default=0.0, help="Water heater load in watts")
    ap.add_argument("--ev-amps", type=int, default=0, help="EVSE amperage")
    ap.add_argument("--phases", type=int, choices=[1, 3], default=1, help="Number of phases")
    ap.add_argument("-o", "--output", help="Write results to file")
    ap.add_argument("--show-rules", action="store_true", help="Include CEC rule references")
    args = ap.parse_args()

    lines: list[str] = []
    base = 5000
    step("Base load", f"{base} W", BASE_LOAD_RULE, args.show_rules, lines)
    if args.floor > 90:
        extra_units = ceil((args.floor - 90) / 90)
        extra = extra_units * 1000
        base += extra
        step("Extra area", f"{extra} W", EXTRA_AREA_RULE, args.show_rules, lines)

    heat_ac = int(max(args.heat, args.ac))
    step("Heating/AC", f"{heat_ac} W", HEAT_AC_RULE, args.show_rules, lines)

    range_load = 6000 if args.range_ <= 12000 else int(args.range_)
    step("Range", f"{range_load} W", RANGE_RULE, args.show_rules, lines)

    ev_load = args.ev_amps * 240 if args.ev_amps else 0
    if ev_load:
        step("EVSE", f"{ev_load} W", EVSE_RULE, args.show_rules, lines)

    dryer_load = int(args.dryer * 0.25)
    if dryer_load:
        step("Dryer", f"{dryer_load} W", DRYER_RULE, args.show_rules, lines)

    water_load = int(args.water * 0.25)
    if water_load:
        step("Water heater", f"{water_load} W", WATER_RULE, args.show_rules, lines)

    total = base + heat_ac + range_load + ev_load + dryer_load + water_load
    step("Total", f"{total} W", TOTAL_RULE, args.show_rules, lines)

    volts = 208 if args.phases == 3 else 240
    divisor = volts if args.phases == 1 else volts * sqrt(3)
    amps = total / divisor
    calc_str = f"{volts}" if args.phases == 1 else f"{volts} * \u221a3"
    lines.append(f"{total} W / {calc_str} = {amps:.1f} A")

    out_text = "\n".join(lines)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(out_text)
    else:
        print(out_text)


if __name__ == "__main__":
    main()


"""Tkinter GUI application for service calculations."""

from __future__ import annotations

import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
from math import ceil
from typing import Any

# HVAC system options
HVAC_OPTIONS = ("Heating & AC", "Heat Pump")
# Units for specifying heat pump capacity
HEAT_UNITS = ("kW", "tons")
TON_TO_KW = 3.516
EV_AMPS = (16, 24, 30, 40, 48, 60, 64, 70, 80)
DRYER_KW_OPTIONS = (4.0, 5.0, 6.0)
WH_UNITS = ("kW", "gal")
WH_GALLON_SIZES = (30, 40, 50, 65, 80)
GALLON_TO_KW = {30: 3.0, 40: 4.5, 50: 5.5, 65: 6.0, 80: 6.0}

# Allow running this file directly by adjusting sys.path for relative imports
if __package__ in {None, ""}:
    # When run directly, add the project root to sys.path so absolute imports work
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from cec_service.calculators.duplex import calculate_duplex_demand
    from cec_service.calculators.house import calculate_demand
    from cec_service.calculators.triplex import calculate_triplex_demand
    from cec_service.calculators.apartment import calculate_multi_demand
    from cec_service.models import Dwelling
    from cec_service.utils.validation import ValidationError, pos_or_none
    from cec_service.utils.pdf import simple_pdf
else:
    from ..calculators.duplex import calculate_duplex_demand
    from ..calculators.house import calculate_demand
    from ..calculators.triplex import calculate_triplex_demand
    from ..calculators.apartment import calculate_multi_demand
    from ..models import Dwelling
    from ..utils.validation import ValidationError, pos_or_none
    from ..utils.pdf import simple_pdf


def _float_from_entry(entry: ttk.Entry) -> float | None:
    text = entry.get().strip()
    return float(text) if text else None


def _describe_unit(inputs: dict[str, Any], details: dict[str, int]) -> list[str]:
    """Return human readable detail lines for a unit."""
    lines: list[str] = []
    floor = inputs["floor_area_m2"]
    lines.append("Base load: 5000 W")
    if "extra_area_load" in details:
        extra_area = floor - 90
        units = ceil(extra_area / 90)
        lines.append(
            f"Extra area: ({extra_area:.0f} m² /90 -> {units}) x 1000 W = {details['extra_area_load']} W"
        )
    if inputs.get("has_range"):
        lines.append(f"Range: {inputs['range_kw']} kW -> {details['range_load']} W")
    else:
        lines.append("No range")
    if inputs.get("has_ev"):
        lines.append(f"EVSE: {inputs['ev_amps']} A x 240 V = {details['ev_load']} W")
    if inputs.get("dryer_kw"):
        lines.append(
            f"Dryer: {inputs['dryer_kw']} kW x 25% = {details['dryer_load']} W"
        )
    if inputs.get("water_heater_kw"):
        lines.append(
            f"Water Heater: {inputs['water_heater_kw']} kW x 25% = {details['wh_load']} W"
        )
    if inputs.get("extra_loads"):
        for label, kw in inputs["extra_loads"]:
            lines.append(f"{label}: {kw} kW x 25% = {int(kw*1000*0.25)} W")
    lines.append(
        f"Heat/AC: max({inputs.get('heat_kw') or 0}, {inputs.get('ac_kw') or 0}) kW x 1000 = {details['heat_ac']} W"
    )
    lines.append(f"Total Watts: {details.get('total_watts', '?')}")
    return lines


class ServiceApp(tk.Tk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()
        self.title("CEC Service Calculator")
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)

        self._init_house_tab(notebook)
        self._init_duplex_tab(notebook)
        self._init_triplex_tab(notebook)
        self._init_apartment_tab(notebook)

    # House Tab
    def _init_house_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="House")

        labels = [
            ("Floor Area (m²)", "floor"),
            ("Heating kW", "heat"),
            ("AC kW", "ac"),
            ("Range kW", "range"),
            ("Dryer kW", "dryer"),
            ("Water Heater kW", "wh"),
            ("EV Amps", "ev"),
        ]
        self.house_entries: dict[str, ttk.Entry] = {}
        for row, (label, key) in enumerate(labels):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w")
            if key == "ev":
                entry = ttk.Combobox(frame, values=EV_AMPS)
                entry.insert(0, "32")
            elif key == "dryer":
                entry = ttk.Combobox(frame, values=DRYER_KW_OPTIONS)
            elif key == "wh":
                entry = ttk.Combobox(frame)
            else:
                entry = ttk.Entry(frame)
            entry.grid(row=row, column=1)
            self.house_entries[key] = entry
            if key == "range":
                self.house_range_var = tk.BooleanVar(value=True)
                cb = ttk.Checkbutton(
                    frame,
                    text="Has Range",
                    variable=self.house_range_var,
                )
                cb.grid(row=row, column=2, sticky="w")

                def _toggle_range(*_):
                    if self.house_range_var.get():
                        self.house_entries["range"].config(state="normal")
                    else:
                        self.house_entries["range"].delete(0, tk.END)
                        self.house_entries["range"].config(state="disabled")

                cb.bind("<ButtonRelease-1>", _toggle_range)
                _toggle_range()
            if key == "wh":
                self.house_wh_unit_var = tk.StringVar(value=WH_UNITS[0])
                box = ttk.Combobox(
                    frame,
                    values=WH_UNITS,
                    width=5,
                    textvariable=self.house_wh_unit_var,
                    state="readonly",
                )
                box.grid(row=row, column=2)

                def _update_wh(e=None, ent=entry):
                    if self.house_wh_unit_var.get() == "gal":
                        ent.config(values=WH_GALLON_SIZES)
                    else:
                        ent.config(values=())

                box.bind("<<ComboboxSelected>>", _update_wh)
                _update_wh()

        # Unit selector for heating input
        self.house_heat_unit_var = tk.StringVar(value=HEAT_UNITS[0])
        self.house_heat_unit_box = ttk.Combobox(
            frame,
            values=HEAT_UNITS,
            width=5,
            textvariable=self.house_heat_unit_var,
            state="readonly",
        )
        self.house_heat_unit_box.grid(row=1, column=2)

        # HVAC type selector
        self.house_hvac_var = tk.StringVar(value=HVAC_OPTIONS[1])
        ttk.Label(frame, text="HVAC Type").grid(row=len(labels), column=0, sticky="w")
        hvac_box = ttk.Combobox(
            frame,
            values=HVAC_OPTIONS,
            textvariable=self.house_hvac_var,
            state="readonly",
        )
        hvac_box.grid(row=len(labels), column=1)

        def _update_house_hvac(*_):
            if self.house_hvac_var.get() == "Heat Pump":
                self.house_entries["ac"].delete(0, tk.END)
                self.house_entries["ac"].config(state="disabled")
                self.house_heat_unit_box.config(state="readonly")
            else:
                self.house_entries["ac"].config(state="normal")
                self.house_heat_unit_var.set(HEAT_UNITS[0])
                self.house_heat_unit_box.config(state="disabled")

        hvac_box.bind("<<ComboboxSelected>>", _update_house_hvac)
        _update_house_hvac()

        self.house_ev_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Include EVSE", variable=self.house_ev_var).grid(
            row=len(labels) + 1, column=0, columnspan=2
        )

        # Extra loads (>1.5 kW)
        self.house_extra_frame = ttk.LabelFrame(frame, text="Extra Loads >1.5 kW")
        self.house_extra_frame.grid(
            row=len(labels) + 2, column=0, columnspan=3, pady=5, sticky="w"
        )
        self.house_extra_rows: list[tuple[ttk.Entry, ttk.Entry]] = []

        def _add_extra_row():
            row = len(self.house_extra_rows)
            lbl_entry = ttk.Entry(self.house_extra_frame)
            lbl_entry.grid(row=row, column=0)
            kw_entry = ttk.Entry(self.house_extra_frame, width=6)
            kw_entry.grid(row=row, column=1)
            self.house_extra_rows.append((lbl_entry, kw_entry))

        ttk.Button(self.house_extra_frame, text="Add", command=_add_extra_row).grid(
            row=0, column=2
        )
        _add_extra_row()

        ttk.Button(frame, text="Calculate", command=self._calc_house).grid(
            row=len(labels) + 3, column=0, columnspan=2, pady=5
        )

        ttk.Button(frame, text="Export PDF", command=self._export_house_pdf).grid(
            row=len(labels) + 4, column=0, columnspan=2
        )

        self.house_result = tk.StringVar()
        ttk.Label(frame, textvariable=self.house_result).grid(
            row=len(labels) + 5, column=0, columnspan=2
        )

    def _calc_house(self) -> None:
        try:
            ac_kw = None
            if self.house_hvac_var.get() != "Heat Pump":
                ac_kw = pos_or_none(
                    _float_from_entry(self.house_entries["ac"]), "ac_kw"
                )
            heat_kw = pos_or_none(
                _float_from_entry(self.house_entries["heat"]), "heat_kw"
            )
            if heat_kw is not None and self.house_heat_unit_var.get() == "tons":
                heat_kw *= TON_TO_KW
            wh_val = _float_from_entry(self.house_entries["wh"])
            if wh_val is not None and self.house_wh_unit_var.get() == "gal":
                wh_val = GALLON_TO_KW.get(int(wh_val))
            dw = Dwelling(
                floor_area_m2=float(self.house_entries["floor"].get()),
                heat_kw=heat_kw,
                ac_kw=ac_kw,
                range_kw=_float_from_entry(self.house_entries["range"]) or 12.0,
                has_range=self.house_range_var.get(),
                dryer_kw=pos_or_none(
                    _float_from_entry(self.house_entries["dryer"]), "dryer_kw"
                ),
                water_heater_kw=pos_or_none(wh_val, "water_heater_kw"),
                extra_loads=[
                    (
                        lbl.get() or "Load",
                        pos_or_none(_float_from_entry(kw), "extra_load") or 0.0,
                    )
                    for lbl, kw in self.house_extra_rows
                    if kw.get().strip()
                ],
                has_ev=self.house_ev_var.get(),
                ev_amps=int(_float_from_entry(self.house_entries["ev"]) or 32),
            )
            result = calculate_demand(dw)
            self.house_last_result = result
            self.house_result.set(
                f"{result['amps']:.1f} A -> {result['suggested_breaker']} A"
            )
        except (ValueError, ValidationError) as err:
            messagebox.showerror("Error", str(err))

    def _export_house_pdf(self) -> None:
        try:
            if not hasattr(self, "house_last_result"):
                self._calc_house()
            result = self.house_last_result
            if result is None:
                return
            path = filedialog.asksaveasfilename(
                defaultextension=".pdf", filetypes=[("PDF", "*.pdf")]
            )
            if not path:
                return
            lines = [
                "House Calculation",
                f"Total Watts: {result['watts']}",
                f"Total Amps: {result['amps']:.1f}",
                f"Suggested Breaker: {result['suggested_breaker']} A",
                "",
                "Details:",
            ]
            lines.extend(_describe_unit(result["inputs"], result["details"]))
            simple_pdf(lines, path)
        except (ValueError, ValidationError) as err:
            messagebox.showerror("Error", str(err))

    # Duplex Tab
    def _init_duplex_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Duplex")

        fields = [
            ("Floor Area (m²)", "floor"),
            ("Heating kW", "heat"),
            ("AC kW", "ac"),
            ("Range kW", "range"),
            ("Dryer kW", "dryer"),
            ("Water Heater kW", "wh"),
            ("EV Amps", "ev"),
        ]

        self.duplex_entries: list[dict[str, ttk.Entry]] = []
        self.duplex_ev_vars: list[tk.BooleanVar] = []
        self.duplex_hvac_vars: list[tk.StringVar] = []
        self.duplex_heat_unit_vars: list[tk.StringVar] = []
        self.duplex_range_vars: list[tk.BooleanVar] = []
        self.duplex_wh_unit_vars: list[tk.StringVar] = []
        self.duplex_extra_frames: list[ttk.LabelFrame] = []
        self.duplex_extra_rows: list[list[tuple[ttk.Entry, ttk.Entry]]] = []
        for col in range(2):
            lf = ttk.LabelFrame(frame, text=f"Unit {col + 1}")
            lf.grid(row=0, column=col, padx=5, pady=5, sticky="n")
            entries: dict[str, ttk.Entry] = {}
            for row, (label, key) in enumerate(fields):
                ttk.Label(lf, text=label).grid(row=row, column=0, sticky="w")
                if key == "ev":
                    entry = ttk.Combobox(lf, values=EV_AMPS)
                    entry.insert(0, "32")
                elif key == "dryer":
                    entry = ttk.Combobox(lf, values=DRYER_KW_OPTIONS)
                elif key == "wh":
                    entry = ttk.Combobox(lf)
                else:
                    entry = ttk.Entry(lf)
                entry.grid(row=row, column=1)
                entries[key] = entry
                if key == "range":
                    rng_var = tk.BooleanVar(value=True)
                    cb = ttk.Checkbutton(lf, text="Has Range", variable=rng_var)
                    cb.grid(row=row, column=2, sticky="w")

                    def _toggle(e=None, ent=entry, var=rng_var):
                        if var.get():
                            ent.config(state="normal")
                        else:
                            ent.delete(0, tk.END)
                            ent.config(state="disabled")

                    cb.bind("<ButtonRelease-1>", _toggle)
                    _toggle()
                    self.duplex_range_vars.append(rng_var)
                if key == "wh":
                    wh_unit_var = tk.StringVar(value=WH_UNITS[0])
                    box = ttk.Combobox(
                        lf,
                        values=WH_UNITS,
                        width=5,
                        textvariable=wh_unit_var,
                        state="readonly",
                    )
                    box.grid(row=row, column=2)

                    def _update_wh(e=None, ent=entry):
                        if wh_unit_var.get() == "gal":
                            ent.config(values=WH_GALLON_SIZES)
                        else:
                            ent.config(values=())

                    box.bind("<<ComboboxSelected>>", _update_wh)
                    _update_wh()
                    self.duplex_wh_unit_vars.append(wh_unit_var)
            # Unit selector for heating
            heat_unit_var = tk.StringVar(value=HEAT_UNITS[0])
            box = ttk.Combobox(
                lf,
                values=HEAT_UNITS,
                width=5,
                textvariable=heat_unit_var,
                state="readonly",
            )
            box.grid(row=1, column=2)
            self.duplex_heat_unit_vars.append(heat_unit_var)
            hv_var = tk.StringVar(value=HVAC_OPTIONS[1])
            ttk.Label(lf, text="HVAC Type").grid(row=len(fields), column=0, sticky="w")
            hv_box = ttk.Combobox(
                lf, values=HVAC_OPTIONS, textvariable=hv_var, state="readonly"
            )
            hv_box.grid(row=len(fields), column=1)

            def _update_hvac(e=None, ent=entries["ac"], var=hv_var, unit_box=box):
                if var.get() == "Heat Pump":
                    ent.delete(0, tk.END)
                    ent.config(state="disabled")
                    unit_box.config(state="readonly")
                else:
                    ent.config(state="normal")
                    unit_box.config(state="disabled")
                    heat_unit_var.set(HEAT_UNITS[0])

            hv_box.bind("<<ComboboxSelected>>", _update_hvac)
            # Add EV checkbox after HVAC row
            _update_hvac()
            var = tk.BooleanVar(value=True)
            ttk.Checkbutton(lf, text="Include EVSE", variable=var).grid(
                row=len(fields) + 1, column=0, columnspan=2
            )
            self.duplex_ev_vars.append(var)
            self.duplex_hvac_vars.append(hv_var)
            self.duplex_entries.append(entries)

            extra_frame = ttk.LabelFrame(lf, text="Extra Loads >1.5 kW")
            extra_frame.grid(
                row=len(fields) + 2, column=0, columnspan=3, pady=5, sticky="w"
            )
            self.duplex_extra_frames.append(extra_frame)
            rows: list[tuple[ttk.Entry, ttk.Entry]] = []

            def _add_extra_row_d(col_idx=col, frame=extra_frame, lst=rows):
                r = len(lst)
                l_ent = ttk.Entry(frame)
                l_ent.grid(row=r, column=0)
                k_ent = ttk.Entry(frame, width=6)
                k_ent.grid(row=r, column=1)
                lst.append((l_ent, k_ent))

            ttk.Button(extra_frame, text="Add", command=_add_extra_row_d).grid(
                row=0, column=2
            )
            _add_extra_row_d()
            self.duplex_extra_rows.append(rows)

        ttk.Button(frame, text="Calculate", command=self._calc_duplex).grid(
            row=1, column=0, columnspan=2, pady=5
        )

        ttk.Button(frame, text="Export PDF", command=self._export_duplex_pdf).grid(
            row=2, column=0, columnspan=2
        )

        self.duplex_result = tk.StringVar()
        ttk.Label(frame, textvariable=self.duplex_result).grid(
            row=3, column=0, columnspan=2
        )

    def _make_unit(self, entries: dict[str, ttk.Entry], idx: int) -> Dwelling:
        ac_kw = None
        if self.duplex_hvac_vars[idx].get() != "Heat Pump":
            ac_kw = pos_or_none(_float_from_entry(entries["ac"]), "ac_kw")
        heat_kw = pos_or_none(_float_from_entry(entries["heat"]), "heat_kw")
        if heat_kw is not None and self.duplex_heat_unit_vars[idx].get() == "tons":
            heat_kw *= TON_TO_KW
        wh_val = _float_from_entry(entries["wh"])
        if wh_val is not None and self.duplex_wh_unit_vars[idx].get() == "gal":
            wh_val = GALLON_TO_KW.get(int(wh_val))
        return Dwelling(
            floor_area_m2=float(entries["floor"].get()),
            heat_kw=heat_kw,
            ac_kw=ac_kw,
            range_kw=_float_from_entry(entries["range"]) or 12.0,
            has_range=self.duplex_range_vars[idx].get(),
            dryer_kw=pos_or_none(_float_from_entry(entries["dryer"]), "dryer_kw"),
            water_heater_kw=pos_or_none(wh_val, "water_heater_kw"),
            extra_loads=[
                (
                    l.get() or "Load",
                    pos_or_none(_float_from_entry(k), "extra_load") or 0.0,
                )
                for l, k in self.duplex_extra_rows[idx]
                if k.get().strip()
            ],
            has_ev=self.duplex_ev_vars[idx].get(),
            ev_amps=int(_float_from_entry(entries["ev"]) or 32),
        )

    def _calc_duplex(self) -> None:
        try:
            a = self._make_unit(self.duplex_entries[0], 0)
            b = self._make_unit(self.duplex_entries[1], 1)
            result = calculate_duplex_demand(a, b)
            self.duplex_last_result = result
            self.duplex_result.set(
                f"{result['amps']:.1f} A -> {result['suggested_breaker']} A"
            )
        except (ValueError, ValidationError) as err:
            messagebox.showerror("Error", str(err))

    def _export_duplex_pdf(self) -> None:
        try:
            if not hasattr(self, "duplex_last_result"):
                self._calc_duplex()
            result = self.duplex_last_result
            if result is None:
                return
            path = filedialog.asksaveasfilename(
                defaultextension=".pdf", filetypes=[("PDF", "*.pdf")]
            )
            if not path:
                return
            lines = [
                "Duplex Calculation",
                f"Total Watts: {result['watts']}",
                f"Total Amps: {result['amps']:.1f}",
                f"Suggested Breaker: {result['suggested_breaker']} A",
                "",
                "Details:",
            ]
            lines.append("Unit 1:")
            lines.extend(
                "  " + s
                for s in _describe_unit(
                    result["inputs"]["unit_a"], result["details"]["unit_a"]
                )
            )
            lines.append("Unit 2:")
            lines.extend(
                "  " + s
                for s in _describe_unit(
                    result["inputs"]["unit_b"], result["details"]["unit_b"]
                )
            )
            lines.append("Combined base:")
            for k, v in result["details"]["combined_base"].items():
                lines.append(f"  {k}: {v}")
            lines.append(f"Heat unit 1: {result['details']['heat_a']} W")
            lines.append(f"Heat unit 2: {result['details']['heat_b']} W")
            simple_pdf(lines, path)
        except (ValueError, ValidationError) as err:
            messagebox.showerror("Error", str(err))

    # Triplex Tab
    def _init_triplex_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Triplex")

        fields = [
            ("Floor Area (m²)", "floor"),
            ("Heating kW", "heat"),
            ("AC kW", "ac"),
            ("Range kW", "range"),
            ("Dryer kW", "dryer"),
            ("Water Heater kW", "wh"),
            ("EV Amps", "ev"),
        ]

        self.triplex_entries: list[dict[str, ttk.Entry]] = []
        self.triplex_ev_vars: list[tk.BooleanVar] = []
        self.triplex_hvac_vars: list[tk.StringVar] = []
        self.triplex_heat_unit_vars: list[tk.StringVar] = []
        self.triplex_range_vars: list[tk.BooleanVar] = []
        self.triplex_wh_unit_vars: list[tk.StringVar] = []
        self.triplex_extra_frames: list[ttk.LabelFrame] = []
        self.triplex_extra_rows: list[list[tuple[ttk.Entry, ttk.Entry]]] = []
        for col in range(3):
            lf = ttk.LabelFrame(frame, text=f"Unit {col + 1}")
            lf.grid(row=0, column=col, padx=5, pady=5, sticky="n")
            entries: dict[str, ttk.Entry] = {}
            for row, (label, key) in enumerate(fields):
                ttk.Label(lf, text=label).grid(row=row, column=0, sticky="w")
                if key == "ev":
                    entry = ttk.Combobox(lf, values=EV_AMPS)
                    entry.insert(0, "32")
                elif key == "dryer":
                    entry = ttk.Combobox(lf, values=DRYER_KW_OPTIONS)
                elif key == "wh":
                    entry = ttk.Combobox(lf)
                else:
                    entry = ttk.Entry(lf)
                entry.grid(row=row, column=1)
                entries[key] = entry
                if key == "range":
                    rng_var = tk.BooleanVar(value=True)
                    cb = ttk.Checkbutton(lf, text="Has Range", variable=rng_var)
                    cb.grid(row=row, column=2, sticky="w")

                    def _tr_toggle(e=None, ent=entry, var=rng_var):
                        if var.get():
                            ent.config(state="normal")
                        else:
                            ent.delete(0, tk.END)
                            ent.config(state="disabled")

                    cb.bind("<ButtonRelease-1>", _tr_toggle)
                    _tr_toggle()
                    self.triplex_range_vars.append(rng_var)
                if key == "wh":
                    wh_unit_var = tk.StringVar(value=WH_UNITS[0])
                    box = ttk.Combobox(
                        lf,
                        values=WH_UNITS,
                        width=5,
                        textvariable=wh_unit_var,
                        state="readonly",
                    )
                    box.grid(row=row, column=2)

                    def _update_wh(e=None, ent=entry):
                        if wh_unit_var.get() == "gal":
                            ent.config(values=WH_GALLON_SIZES)
                        else:
                            ent.config(values=())

                    box.bind("<<ComboboxSelected>>", _update_wh)
                    _update_wh()
                    self.triplex_wh_unit_vars.append(wh_unit_var)
            heat_unit_var = tk.StringVar(value=HEAT_UNITS[0])
            box = ttk.Combobox(
                lf,
                values=HEAT_UNITS,
                width=5,
                textvariable=heat_unit_var,
                state="readonly",
            )
            box.grid(row=1, column=2)
            self.triplex_heat_unit_vars.append(heat_unit_var)
            hv_var = tk.StringVar(value=HVAC_OPTIONS[1])
            ttk.Label(lf, text="HVAC Type").grid(row=len(fields), column=0, sticky="w")
            hv_box = ttk.Combobox(
                lf, values=HVAC_OPTIONS, textvariable=hv_var, state="readonly"
            )
            hv_box.grid(row=len(fields), column=1)

            def _update_hvac(e=None, ent=entries["ac"], var=hv_var, unit_box=box):
                if var.get() == "Heat Pump":
                    ent.delete(0, tk.END)
                    ent.config(state="disabled")
                    unit_box.config(state="readonly")
                else:
                    ent.config(state="normal")
                    unit_box.config(state="disabled")
                    heat_unit_var.set(HEAT_UNITS[0])

            hv_box.bind("<<ComboboxSelected>>", _update_hvac)
            _update_hvac()
            var = tk.BooleanVar(value=True)
            ttk.Checkbutton(lf, text="Include EVSE", variable=var).grid(
                row=len(fields) + 1, column=0, columnspan=2
            )
            self.triplex_ev_vars.append(var)
            self.triplex_hvac_vars.append(hv_var)
            self.triplex_entries.append(entries)

            extra_frame = ttk.LabelFrame(lf, text="Extra Loads >1.5 kW")
            extra_frame.grid(
                row=len(fields) + 2, column=0, columnspan=3, pady=5, sticky="w"
            )
            rows: list[tuple[ttk.Entry, ttk.Entry]] = []

            def _add_row(frame=extra_frame, lst=rows):
                r = len(lst)
                le = ttk.Entry(frame)
                le.grid(row=r, column=0)
                ke = ttk.Entry(frame, width=6)
                ke.grid(row=r, column=1)
                lst.append((le, ke))

            ttk.Button(extra_frame, text="Add", command=_add_row).grid(row=0, column=2)
            _add_row()
            self.triplex_extra_frames.append(extra_frame)
            self.triplex_extra_rows.append(rows)

        ttk.Button(frame, text="Calculate", command=self._calc_triplex).grid(
            row=1, column=0, columnspan=3, pady=5
        )

        ttk.Button(frame, text="Export PDF", command=self._export_triplex_pdf).grid(
            row=2, column=0, columnspan=3
        )

        self.triplex_result = tk.StringVar()
        ttk.Label(frame, textvariable=self.triplex_result).grid(
            row=3, column=0, columnspan=3
        )

    def _make_triplex_unit(self, entries: dict[str, ttk.Entry], idx: int) -> Dwelling:
        ac_kw = None
        if self.triplex_hvac_vars[idx].get() != "Heat Pump":
            ac_kw = pos_or_none(_float_from_entry(entries["ac"]), "ac_kw")
        heat_kw = pos_or_none(_float_from_entry(entries["heat"]), "heat_kw")
        if heat_kw is not None and self.triplex_heat_unit_vars[idx].get() == "tons":
            heat_kw *= TON_TO_KW
        wh_val = _float_from_entry(entries["wh"])
        if wh_val is not None and self.triplex_wh_unit_vars[idx].get() == "gal":
            wh_val = GALLON_TO_KW.get(int(wh_val))
        return Dwelling(
            floor_area_m2=float(entries["floor"].get()),
            heat_kw=heat_kw,
            ac_kw=ac_kw,
            range_kw=_float_from_entry(entries["range"]) or 12.0,
            has_range=self.triplex_range_vars[idx].get(),
            dryer_kw=pos_or_none(_float_from_entry(entries["dryer"]), "dryer_kw"),
            water_heater_kw=pos_or_none(wh_val, "water_heater_kw"),
            extra_loads=[
                (
                    l.get() or "Load",
                    pos_or_none(_float_from_entry(k), "extra_load") or 0.0,
                )
                for l, k in self.triplex_extra_rows[idx]
                if k.get().strip()
            ],
            has_ev=self.triplex_ev_vars[idx].get(),
            ev_amps=int(_float_from_entry(entries["ev"]) or 32),
        )

    def _calc_triplex(self) -> None:
        try:
            a = self._make_triplex_unit(self.triplex_entries[0], 0)
            b = self._make_triplex_unit(self.triplex_entries[1], 1)
            c = self._make_triplex_unit(self.triplex_entries[2], 2)
            result = calculate_triplex_demand(a, b, c)
            self.triplex_last_result = result
            self.triplex_result.set(
                f"{result['amps']:.1f} A -> {result['suggested_breaker']} A"
            )
        except (ValueError, ValidationError) as err:
            messagebox.showerror("Error", str(err))

    def _export_triplex_pdf(self) -> None:
        try:
            if not hasattr(self, "triplex_last_result"):
                self._calc_triplex()
            result = self.triplex_last_result
            if result is None:
                return
            path = filedialog.asksaveasfilename(
                defaultextension=".pdf", filetypes=[("PDF", "*.pdf")]
            )
            if not path:
                return
            lines = [
                "Triplex Calculation",
                f"Total Watts: {result['watts']}",
                f"Total Amps: {result['amps']:.1f}",
                f"Suggested Breaker: {result['suggested_breaker']} A",
                "",
                "Details:",
                "Unit 1:",
            ]
            lines.extend(
                "  " + s
                for s in _describe_unit(
                    result["inputs"]["unit_a"], result["details"]["unit_a"]
                )
            )
            lines.append("Unit 2:")
            lines.extend(
                "  " + s
                for s in _describe_unit(
                    result["inputs"]["unit_b"], result["details"]["unit_b"]
                )
            )
            lines.append("Unit 3:")
            lines.extend(
                "  " + s
                for s in _describe_unit(
                    result["inputs"]["unit_c"], result["details"]["unit_c"]
                )
            )
            lines.append("Combined base:")
            for k, v in result["details"]["combined_base"].items():
                lines.append(f"  {k}: {v}")
            lines.append(f"Total heat: {result['details']['total_heat']} W")
            simple_pdf(lines, path)
        except (ValueError, ValidationError) as err:
            messagebox.showerror("Error", str(err))

    # Apartment Tab
    def _init_apartment_tab(self, notebook: ttk.Notebook) -> None:
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Apartment")

        self.apartment_container = ttk.Frame(frame)
        self.apartment_container.grid(row=0, column=0, columnspan=4, sticky="w")

        self.apartment_frames: list[ttk.LabelFrame] = []
        self.apartment_entries: list[dict[str, ttk.Entry]] = []
        self.apartment_ev_vars: list[tk.BooleanVar] = []
        self.apartment_hvac_vars: list[tk.StringVar] = []
        self.apartment_heat_unit_vars: list[tk.StringVar] = []
        self.apartment_range_vars: list[tk.BooleanVar] = []
        self.apartment_wh_unit_vars: list[tk.StringVar] = []
        self.apartment_extra_frames: list[ttk.LabelFrame] = []
        self.apartment_extra_rows: list[list[tuple[ttk.Entry, ttk.Entry]]] = []

        fields = [
            ("Floor Area (m²)", "floor"),
            ("Heating kW", "heat"),
            ("AC kW", "ac"),
            ("Range kW", "range"),
            ("Dryer kW", "dryer"),
            ("Water Heater kW", "wh"),
            ("EV Amps", "ev"),
        ]

        def _add_unit() -> None:
            idx = len(self.apartment_entries)
            lf = ttk.LabelFrame(self.apartment_container, text=f"Unit {idx + 1}")
            lf.grid(row=idx // 5, column=idx % 5, padx=5, pady=5, sticky="n")
            self.apartment_frames.append(lf)
            entries: dict[str, ttk.Entry] = {}
            for row, (label, key) in enumerate(fields):
                ttk.Label(lf, text=label).grid(row=row, column=0, sticky="w")
                if key == "ev":
                    ent = ttk.Combobox(lf, values=EV_AMPS)
                    ent.insert(0, "32")
                elif key == "dryer":
                    ent = ttk.Combobox(lf, values=DRYER_KW_OPTIONS)
                elif key == "wh":
                    ent = ttk.Combobox(lf)
                else:
                    ent = ttk.Entry(lf)
                ent.grid(row=row, column=1)
                entries[key] = ent
                if key == "range":
                    rng_var = tk.BooleanVar(value=True)
                    cb = ttk.Checkbutton(lf, text="Has Range", variable=rng_var)
                    cb.grid(row=row, column=2, sticky="w")

                    def _toggle(ent=ent, var=rng_var):
                        if var.get():
                            ent.config(state="normal")
                        else:
                            ent.delete(0, tk.END)
                            ent.config(state="disabled")

                    cb.bind("<ButtonRelease-1>", lambda _e: _toggle())
                    _toggle()
                    self.apartment_range_vars.append(rng_var)
                if key == "wh":
                    wh_unit_var = tk.StringVar(value=WH_UNITS[0])
                    box = ttk.Combobox(
                        lf,
                        values=WH_UNITS,
                        width=5,
                        textvariable=wh_unit_var,
                        state="readonly",
                    )
                    box.grid(row=row, column=2)

                    def _update_wh(e=None, ent=ent):
                        if wh_unit_var.get() == "gal":
                            ent.config(values=WH_GALLON_SIZES)
                        else:
                            ent.config(values=())

                    box.bind("<<ComboboxSelected>>", _update_wh)
                    _update_wh()
                    self.apartment_wh_unit_vars.append(wh_unit_var)
            heat_unit_var = tk.StringVar(value=HEAT_UNITS[0])
            box = ttk.Combobox(
                lf,
                values=HEAT_UNITS,
                width=5,
                textvariable=heat_unit_var,
                state="readonly",
            )
            box.grid(row=1, column=2)
            self.apartment_heat_unit_vars.append(heat_unit_var)
            hv_var = tk.StringVar(value=HVAC_OPTIONS[1])
            ttk.Label(lf, text="HVAC Type").grid(row=len(fields), column=0, sticky="w")
            hv_box = ttk.Combobox(
                lf, values=HVAC_OPTIONS, textvariable=hv_var, state="readonly"
            )
            hv_box.grid(row=len(fields), column=1)

            def _update_hvac(e=None, ent=entries["ac"], var=hv_var, unit_box=box):
                if var.get() == "Heat Pump":
                    ent.delete(0, tk.END)
                    ent.config(state="disabled")
                    unit_box.config(state="readonly")
                else:
                    ent.config(state="normal")
                    unit_box.config(state="disabled")
                    heat_unit_var.set(HEAT_UNITS[0])

            hv_box.bind("<<ComboboxSelected>>", _update_hvac)
            _update_hvac()
            var = tk.BooleanVar(value=True)
            ttk.Checkbutton(lf, text="Include EVSE", variable=var).grid(
                row=len(fields) + 1, column=0, columnspan=2
            )
            self.apartment_ev_vars.append(var)
            self.apartment_hvac_vars.append(hv_var)
            self.apartment_entries.append(entries)
            extra_frame = ttk.LabelFrame(lf, text="Extra Loads >1.5 kW")
            extra_frame.grid(
                row=len(fields) + 2, column=0, columnspan=3, pady=5, sticky="w"
            )
            self.apartment_extra_frames.append(extra_frame)
            rows: list[tuple[ttk.Entry, ttk.Entry]] = []

            def _add_extra_row(frame=extra_frame, lst=rows):
                r = len(lst)
                le = ttk.Entry(frame)
                le.grid(row=r, column=0)
                ke = ttk.Entry(frame, width=6)
                ke.grid(row=r, column=1)
                lst.append((le, ke))

            ttk.Button(extra_frame, text="Add", command=_add_extra_row).grid(
                row=0, column=2
            )
            _add_extra_row()
            self.apartment_extra_rows.append(rows)
            self._update_apartment_grid()

        for _ in range(4):
            _add_unit()

        ttk.Button(frame, text="Add Unit", command=_add_unit).grid(
            row=1, column=0, pady=5
        )
        ttk.Button(frame, text="Remove Unit", command=self._remove_apartment_unit).grid(
            row=1, column=1, pady=5
        )
        ttk.Button(frame, text="Calculate", command=self._calc_apartment).grid(
            row=2, column=0, columnspan=2, pady=5
        )
        ttk.Button(frame, text="Export PDF", command=self._export_apartment_pdf).grid(
            row=3, column=0, columnspan=2
        )

        self.apartment_result = tk.StringVar()
        ttk.Label(frame, textvariable=self.apartment_result).grid(
            row=4, column=0, columnspan=2
        )

    def _update_apartment_grid(self) -> None:
        """Reposition apartment unit frames in rows of five."""
        for idx, frame in enumerate(self.apartment_frames):
            frame.grid_configure(row=idx // 5, column=idx % 5)

    def _remove_apartment_unit(self) -> None:
        if not self.apartment_frames:
            return
        lf = self.apartment_frames.pop()
        lf.destroy()
        self.apartment_entries.pop()
        self.apartment_ev_vars.pop()
        self.apartment_hvac_vars.pop()
        self.apartment_heat_unit_vars.pop()
        self.apartment_range_vars.pop()
        self.apartment_wh_unit_vars.pop()
        self.apartment_extra_rows.pop()
        self.apartment_extra_frames.pop()
        self._update_apartment_grid()

    def _make_apartment_unit(self, entries: dict[str, ttk.Entry], idx: int) -> Dwelling:
        ac_kw = None
        if self.apartment_hvac_vars[idx].get() != "Heat Pump":
            ac_kw = pos_or_none(_float_from_entry(entries["ac"]), "ac_kw")
        heat_kw = pos_or_none(_float_from_entry(entries["heat"]), "heat_kw")
        if heat_kw is not None and self.apartment_heat_unit_vars[idx].get() == "tons":
            heat_kw *= TON_TO_KW
        wh_val = _float_from_entry(entries["wh"])
        if wh_val is not None and self.apartment_wh_unit_vars[idx].get() == "gal":
            wh_val = GALLON_TO_KW.get(int(wh_val))
        return Dwelling(
            floor_area_m2=float(entries["floor"].get()),
            heat_kw=heat_kw,
            ac_kw=ac_kw,
            range_kw=_float_from_entry(entries["range"]) or 12.0,
            has_range=self.apartment_range_vars[idx].get(),
            dryer_kw=pos_or_none(_float_from_entry(entries["dryer"]), "dryer_kw"),
            water_heater_kw=pos_or_none(wh_val, "water_heater_kw"),
            extra_loads=[
                (
                    l.get() or "Load",
                    pos_or_none(_float_from_entry(k), "extra_load") or 0.0,
                )
                for l, k in self.apartment_extra_rows[idx]
                if k.get().strip()
            ],
            has_ev=self.apartment_ev_vars[idx].get(),
            ev_amps=int(_float_from_entry(entries["ev"]) or 32),
        )

    def _calc_apartment(self) -> None:
        try:
            units = [
                self._make_apartment_unit(e, i)
                for i, e in enumerate(self.apartment_entries)
            ]
            result = calculate_multi_demand(units)
            self.apartment_last_result = result
            self.apartment_result.set(
                f"{result['amps']:.1f} A -> {result['suggested_breaker']} A"
            )
        except (ValueError, ValidationError) as err:
            messagebox.showerror("Error", str(err))

    def _export_apartment_pdf(self) -> None:
        try:
            if not hasattr(self, "apartment_last_result"):
                self._calc_apartment()
            result = self.apartment_last_result
            if result is None:
                return
            path = filedialog.asksaveasfilename(
                defaultextension=".pdf", filetypes=[("PDF", "*.pdf")]
            )
            if not path:
                return
            lines = [
                "Apartment Calculation",
                f"Total Watts: {result['watts']}",
                f"Total Amps: {result['amps']:.1f}",
                f"Suggested Breaker: {result['suggested_breaker']} A",
                "",
                "Details:",
            ]
            for i in range(len(self.apartment_entries)):
                lines.append(f"Unit {i+1}:")
                lines.extend(
                    "  " + s
                    for s in _describe_unit(
                        result["inputs"][f"unit_{i+1}"],
                        result["details"][f"unit_{i+1}"],
                    )
                )
            lines.append("Combined base:")
            for k, v in result["details"]["combined_base"].items():
                lines.append(f"  {k}: {v}")
            lines.append(f"Total heat: {result['details']['total_heat']} W")
            simple_pdf(lines, path)
        except (ValueError, ValidationError) as err:
            messagebox.showerror("Error", str(err))


def main() -> None:
    app = ServiceApp()
    app.mainloop()


if __name__ == "__main__":
    main()

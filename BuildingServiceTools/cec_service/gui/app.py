"""Tkinter GUI application for service calculations."""
from __future__ import annotations

import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk, filedialog

# Allow running this file directly by adjusting sys.path for relative imports
if __package__ in {None, ""}:
    # When run directly, add the project root to sys.path so absolute imports work
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from cec_service.calculators.duplex import calculate_duplex_demand
    from cec_service.calculators.triplex import calculate_triplex_demand
    from cec_service.calculators.house import calculate_demand
    from cec_service.models import Dwelling
    from cec_service.utils.validation import ValidationError, pos_or_none
    from cec_service.utils.pdf import simple_pdf
else:
    from ..calculators.duplex import calculate_duplex_demand
    from ..calculators.triplex import calculate_triplex_demand
    from ..calculators.house import calculate_demand
    from ..models import Dwelling
    from ..utils.validation import ValidationError, pos_or_none
    from ..utils.pdf import simple_pdf


def _float_from_entry(entry: ttk.Entry) -> float | None:
    text = entry.get().strip()
    return float(text) if text else None


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
            entry = ttk.Entry(frame)
            entry.grid(row=row, column=1)
            self.house_entries[key] = entry

        self.house_ev_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame, text="Include EVSE", variable=self.house_ev_var).grid(
            row=len(labels), column=0, columnspan=2
        )

        ttk.Button(frame, text="Calculate", command=self._calc_house).grid(
            row=len(labels) + 1, column=0, columnspan=2, pady=5
        )

        ttk.Button(frame, text="Export PDF", command=self._export_house_pdf).grid(
            row=len(labels) + 2, column=0, columnspan=2
        )

        self.house_result = tk.StringVar()
        ttk.Label(frame, textvariable=self.house_result).grid(
            row=len(labels) + 3, column=0, columnspan=2
        )

    def _calc_house(self) -> None:
        try:
            dw = Dwelling(
                floor_area_m2=float(self.house_entries["floor"].get()),
                heat_kw=pos_or_none(
                    _float_from_entry(self.house_entries["heat"]), "heat_kw"
                ),
                ac_kw=pos_or_none(_float_from_entry(self.house_entries["ac"]), "ac_kw"),
                range_kw=_float_from_entry(self.house_entries["range"]) or 12.0,
                dryer_kw=pos_or_none(
                    _float_from_entry(self.house_entries["dryer"]), "dryer_kw"
                ),
                water_heater_kw=pos_or_none(
                    _float_from_entry(self.house_entries["wh"]), "water_heater_kw"
                ),
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
                "Steps:",
            ]
            lines.extend(result["steps"])
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
        for col in range(2):
            lf = ttk.LabelFrame(frame, text=f"Unit {col + 1}")
            lf.grid(row=0, column=col, padx=5, pady=5, sticky="n")
            entries: dict[str, ttk.Entry] = {}
            for row, (label, key) in enumerate(fields):
                ttk.Label(lf, text=label).grid(row=row, column=0, sticky="w")
                entry = ttk.Entry(lf)
                entry.grid(row=row, column=1)
                entries[key] = entry
            var = tk.BooleanVar(value=True)
            ttk.Checkbutton(lf, text="Include EVSE", variable=var).grid(
                row=len(fields), column=0, columnspan=2
            )
            self.duplex_ev_vars.append(var)
            self.duplex_entries.append(entries)

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
        return Dwelling(
            floor_area_m2=float(entries["floor"].get()),
            heat_kw=pos_or_none(_float_from_entry(entries["heat"]), "heat_kw"),
            ac_kw=pos_or_none(_float_from_entry(entries["ac"]), "ac_kw"),
            range_kw=_float_from_entry(entries["range"]) or 12.0,
            dryer_kw=pos_or_none(_float_from_entry(entries["dryer"]), "dryer_kw"),
            water_heater_kw=pos_or_none(
                _float_from_entry(entries["wh"]), "water_heater_kw"
            ),
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
                "Steps:",
            ]
            lines.extend(result["steps"])
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
        for col in range(3):
            lf = ttk.LabelFrame(frame, text=f"Unit {col + 1}")
            lf.grid(row=0, column=col, padx=5, pady=5, sticky="n")
            entries: dict[str, ttk.Entry] = {}
            for row, (label, key) in enumerate(fields):
                ttk.Label(lf, text=label).grid(row=row, column=0, sticky="w")
                entry = ttk.Entry(lf)
                entry.grid(row=row, column=1)
                entries[key] = entry
            var = tk.BooleanVar(value=True)
            ttk.Checkbutton(lf, text="Include EVSE", variable=var).grid(
                row=len(fields), column=0, columnspan=2
            )
            self.triplex_ev_vars.append(var)
            self.triplex_entries.append(entries)

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
        return Dwelling(
            floor_area_m2=float(entries["floor"].get()),
            heat_kw=pos_or_none(_float_from_entry(entries["heat"]), "heat_kw"),
            ac_kw=pos_or_none(_float_from_entry(entries["ac"]), "ac_kw"),
            range_kw=_float_from_entry(entries["range"]) or 12.0,
            dryer_kw=pos_or_none(_float_from_entry(entries["dryer"]), "dryer_kw"),
            water_heater_kw=pos_or_none(
                _float_from_entry(entries["wh"]), "water_heater_kw"
            ),
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
                "Steps:",
            ]
            lines.extend(result["steps"])
            simple_pdf(lines, path)
        except (ValueError, ValidationError) as err:
            messagebox.showerror("Error", str(err))


def main() -> None:
    app = ServiceApp()
    app.mainloop()


if __name__ == "__main__":
    main()

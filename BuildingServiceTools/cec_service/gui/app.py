"""Tkinter GUI application for service calculations."""
from __future__ import annotations

import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

# Allow running this file directly by adjusting sys.path for relative imports
if __package__ in {None, ""}:
    # When run directly, add the project root to sys.path so absolute imports work
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from cec_service.calculators.duplex import calculate_duplex_demand
    from cec_service.calculators.house import calculate_demand
    from cec_service.models import Dwelling
    from cec_service.utils.validation import ValidationError, pos_or_none
else:
    from ..calculators.duplex import calculate_duplex_demand
    from ..calculators.house import calculate_demand
    from ..models import Dwelling
    from ..utils.validation import ValidationError, pos_or_none


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

        self.house_ev_var = tk.BooleanVar()
        ttk.Checkbutton(frame, text="Include EVSE", variable=self.house_ev_var).grid(
            row=len(labels), column=0, columnspan=2
        )

        ttk.Button(frame, text="Calculate", command=self._calc_house).grid(
            row=len(labels) + 1, column=0, columnspan=2, pady=5
        )

        self.house_result = tk.StringVar()
        ttk.Label(frame, textvariable=self.house_result).grid(
            row=len(labels) + 2, column=0, columnspan=2
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
            self.house_result.set(
                f"{result['amps']:.1f} A -> {result['suggested_breaker']} A"
            )
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
        ]

        self.duplex_entries: list[dict[str, ttk.Entry]] = []
        for col in range(2):
            lf = ttk.LabelFrame(frame, text=f"Unit {col + 1}")
            lf.grid(row=0, column=col, padx=5, pady=5, sticky="n")
            entries: dict[str, ttk.Entry] = {}
            for row, (label, key) in enumerate(fields):
                ttk.Label(lf, text=label).grid(row=row, column=0, sticky="w")
                entry = ttk.Entry(lf)
                entry.grid(row=row, column=1)
                entries[key] = entry
            self.duplex_entries.append(entries)

        ttk.Button(frame, text="Calculate", command=self._calc_duplex).grid(
            row=1, column=0, columnspan=2, pady=5
        )

        self.duplex_result = tk.StringVar()
        ttk.Label(frame, textvariable=self.duplex_result).grid(
            row=2, column=0, columnspan=2
        )

    def _make_unit(self, entries: dict[str, ttk.Entry]) -> Dwelling:
        return Dwelling(
            floor_area_m2=float(entries["floor"].get()),
            heat_kw=pos_or_none(_float_from_entry(entries["heat"]), "heat_kw"),
            ac_kw=pos_or_none(_float_from_entry(entries["ac"]), "ac_kw"),
            range_kw=_float_from_entry(entries["range"]) or 12.0,
            dryer_kw=pos_or_none(_float_from_entry(entries["dryer"]), "dryer_kw"),
            water_heater_kw=pos_or_none(
                _float_from_entry(entries["wh"]), "water_heater_kw"
            ),
        )

    def _calc_duplex(self) -> None:
        try:
            a = self._make_unit(self.duplex_entries[0])
            b = self._make_unit(self.duplex_entries[1])
            result = calculate_duplex_demand(a, b)
            self.duplex_result.set(
                f"{result['amps']:.1f} A -> {result['suggested_breaker']} A"
            )
        except (ValueError, ValidationError) as err:
            messagebox.showerror("Error", str(err))


def main() -> None:
    app = ServiceApp()
    app.mainloop()


if __name__ == "__main__":
    main()

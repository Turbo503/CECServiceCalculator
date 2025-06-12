# CECServiceCalculator
Electrical Service Calculator

## Running the GUI

From the project root run:

```bash
python -m cec_service.gui.app
```

Running the `app.py` file directly can cause import errors because it relies on
package-relative imports. Invoking it as a module ensures Python sets up the
package correctly.

The GUI allows specifying heating loads in either **kW** or **tons** when the
HVAC type is set to *Heat Pump*. Residential heat pump sizes typically range
from 1–5 tons (approximately 3.5–17.5&nbsp;kW).

Dryer loads can be selected from common kW ratings, while water heater capacity
may now be entered in **kW** or by choosing a standard tank size in gallons.

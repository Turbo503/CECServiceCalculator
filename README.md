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

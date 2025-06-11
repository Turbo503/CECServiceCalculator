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

## Command Line Tool

A simple command line calculator is available as `service_calc.py`.
Example:

```bash
./service_calc.py 120 --heat 18000 --dryer 5000 --pdf result.pdf --show-rules
```

This will print each calculation step and write the same information to
`result.pdf`.

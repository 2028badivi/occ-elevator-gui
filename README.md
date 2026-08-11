# OCC elevator GUI

Open-loop Raspberry Pi controller and GUI for the four-floor OCC model
elevator. The current hardware uses a Cytron MD20A in PWM + DIR mode and has
no position sensors.

## Raspberry Pi 4B setup (Ubuntu 24.04)

```bash
sudo apt update
sudo apt install -y git python3-tk python3-venv python3-gpiozero python3-lgpio
git clone https://github.com/Omkar-Deshmukh284/occ-elevator-gui.git
cd occ-elevator-gui
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install guizero
.venv/bin/python elevator_gui.py
```

Pins and physical calibration values live in `config.py`. Confirm GPIO12 is
PWM, GPIO26 is DIR, and the Pi and MD20A share ground before enabling motor
power.

## Tests

```bash
python3 -m unittest discover -v
```

The suite covers every directed floor pair, pause/arrival stop behavior,
position integration, dead-zone mapping, GPIO direction/duty, and stopwatch
calibration fitting. Laptop runs intentionally fall back to simulation mode
when `gpiozero` is unavailable.

## Physical calibration

The nominal drive math is 27 RPM through a 72 mm pulley at 1:1, or about
101.8 mm/s at 100%. Actual speed must still be measured separately up and
down. See [PHYSICS.md](PHYSICS.md) and run:

```bash
python3 motion_calibration.py --help
```

Without sensors, software tests cannot guarantee the real car's final
position under every load. Use the GUI's manual floor calibration whenever
the physical car and estimator are not aligned.

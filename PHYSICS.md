# Elevator motion model

The rig has no position sensor. The application therefore estimates position
by integrating a calibrated model of the exact PWM command sent to the motor.
This can be repeatable, but it cannot correct slip, changing load, voltage,
temperature, or mechanical wear without an external reference.

## Confirmed geometry and drive values

| Quantity | Value |
|---|---:|
| Floor heights from shaft bottom | F1 0 / F2 324 / F3 648 / F4 972 mm |
| Car height | 254 mm |
| Pulley diameter | 72 mm |
| Pulley speed at 100% | 27 RPM |
| Gearbox ratio | 1:1 |
| PWM + DIR pins | GPIO12 + GPIO26 |
| PWM frequency | 100 Hz |

Pulley circumference and nominal maximum cable speed are:

```text
C = pi * 72 = 226.195 mm/rev
v_nominal = 27 / 60 * C = 101.788 mm/s
```

The speed slider and acceleration profile specify desired physical speed.
They do not directly specify PWM duty.

## Dead-zone + linear motor model

Each direction has independent calibration values because gravity and load
make up/down behavior different:

```text
v_full(direction) = 101.788 * SPEED_SCALE(direction)
v(duty) = 0                                           if duty <= deadzone
v(duty) = v_full * (duty - deadzone)/(100-deadzone)  otherwise
```

The controller uses the inverse model when producing PWM:

```text
duty = deadzone + desired_speed_fraction * (100 - deadzone)
```

This is the key difference from a simple 20% clamp. A clamp commands 20% duty
and incorrectly lets the estimator count it as 20% speed. The inverse model
may command duty above the dead zone while integrating only the fitted physical
speed. Hardware and estimator therefore use one consistent command.

The defaults in `config.py` leave both dead zones at zero and both full-speed
scales at one because those values must be measured on the actual rig.

## Position integration

For each GUI tick:

```text
delta_height = direction * estimated_speed(duty) * measured_elapsed_seconds
```

Real elapsed time comes from `time.monotonic()`. In hardware mode it is not
clamped: if the GUI stalls while the motor keeps turning, discarding elapsed
time would make the estimate fall behind. Simulation-only mode caps long
visual jumps at 0.1 seconds.

The motor is stopped in the same tick that the estimate enters the 0.1 mm
numerical arrival tolerance. The estimate is then anchored to the exact floor height.
During the 0.65 second demo/sequence pause, both direction and duty are zero.

## Stopwatch calibration

Choose one fixed PWM frequency and do not change it after calibration. Use a
long measured section away from the physical end stops. For each direction:

1. Start above the breakaway region, then time at least three distinct fixed
   duties such as 30%, 50%, 75%, and 100%.
2. Repeat each run and use the mean time.
3. Run the fitter with `DUTY:SECONDS` samples:

```bash
python motion_calibration.py --distance-mm 648 \
  --up 30:34.2 --up 50:19.8 --up 75:12.5 --up 100:9.8 \
  --down 30:30.1 --down 50:17.4 --down 75:11.0 --down 100:8.9
```

Copy the four printed values into `config.py`:

```text
UP_PWM_DEADZONE_PERCENT
UP_SPEED_SCALE
DOWN_PWM_DEADZONE_PERCENT
DOWN_SPEED_SCALE
```

Re-test one-floor, two-floor, and full-shaft moves after calibration. A
distance-proportional error points to a speed scale; a low-duty-only error
points to the dead-zone fit; a random error cannot be removed open-loop.

## Limits

Manual **Calibrate current position** remains the only safe reference reset
without a sensor. Timed pushing against a hard stop is not implemented because
the software cannot detect contact and could continue stalling the motor.

# Elevator Physics & Screen Math

All the math behind the simulation, in one place. The goal of all of this:
the GUI's car should match the real car in position AND timing, so the sim
can stand in for the IR sensors during testing.

## Real measurements these are built on

| Quantity | Value | Source |
|---|---|---|
| Pulley diameter | 74 mm | measured |
| Motor max speed (raw, BEFORE gearbox) | 27 RPM | whiteboard spec |
| Gearbox ratio | **TODO - unknown, set to 1.0** | `config.GEARBOX_RATIO` |
| Floor spacing (evenly spaced) | 254 mm | SolidWorks model |
| Floor heights (F1..F4) | 0 / 254 / 508 / 762 mm | SolidWorks model |
| Shaft margin below floor 1 | 18 mm | SolidWorks model |
| Shaft margin above floor 4 | 43 mm | SolidWorks model |
| Shaft interior width | 95 mm | SolidWorks model |

## 1. Pulley circumference - cable moved per revolution

```
C = pi x d = pi x 74mm = 232.5 mm/rev
```

One full pulley turn moves the car 232.5 mm.

## 2. Max car speed - the "maximum derivative of height"

RPM is revolutions per MINUTE, so divide by 60 for rev/sec, then multiply by
how far one revolution moves the car:

```
v_max = (MOTOR_RPM / GEARBOX_RATIO) / 60 x C
      = (27 / 1.0) / 60 x 232.5
      = 104.6 mm/s        <- placeholder until the real gear ratio is known
```

This is the hard cap from the whiteboard graph: the height curve Y(t) can
never have a slope steeper than v_max, no matter what the speed slider says.
A unit test (test_step_car_never_exceeds_real_max_speed) locks this in.

NOTE: the gear ratio matters a LOT here. e.g. a 20:1 reduction would make
v_max ~5.2 mm/s. Fill in `GEARBOX_RATIO` in config.py once known.

## 3. Per-tick motion - time-based, not frame-based

Every GUI tick measures the real elapsed time `dt` (~1/60 s) and moves the car:

```
delta_y = (speed% / 100) x ramp_fraction x v_max x dt
```

Because this multiplies by measured seconds instead of assuming a frame
rate, a lagging GUI doesn't slow the simulated car down - a trip takes the
same wall-clock time regardless of tick rate. dt is capped at 0.1 s so a
one-off freeze can't teleport the car.

Resulting trip times at 100% speed (with ramps, ratio 1.0):
- floor to floor (254 mm): ~5.2 s
- full run 1 -> 4 (762 mm): ~10 s

## 4. Accel/decel ramp

```
ramp_fraction = max(0.15, min(d_traveled / 80mm, d_remaining / 80mm, 1.0))
```

Speed scales up linearly over the first 80 mm of a move, cruises at 1.0,
scales back down over the last 80 mm approaching the target, floored at 15%
so the car never stalls short. Short hops where the ramps overlap form a
triangular profile that never reaches full cruise. The 80 mm distances and
15% floor are TUNING choices (feel), not derived from hardware - everything
else in this doc comes from real measurements.

## 5. Pulley rotation animation

```
theta = (car_height / C) x 2pi
```

When the car has traveled one circumference (232.5 mm), the on-screen wheel
has turned exactly once - so the drawn pulley spins in true sync with the
real one, visibly slowing through the ramps.

## 6. Screen mapping - one uniform mm -> pixel scale

Total drawn shaft span:

```
total = 18 + 762 + 43 = 823 mm
scale = 332 design-px / 823 mm = 0.40 px/mm
```

Every element on the canvas - floor positions, the 95 mm shaft width, the
80x100 mm car, the 74 mm pulley - is its real measurement times that same
scale, on BOTH axes. That's what keeps proportions honest: a floor gap
(254 mm -> 102 px) is genuinely ~2.7x the pulley diameter (74 mm -> 30 px)
on screen, same as in real life.

```
design_y(h) = SHAFT_BOTTOM_DESIGN_Y - (h + 18mm) x scale
```

(design-y increases downward like screen pixels; real height increases
upward - the flip happens only here, at draw time.)

## Where each piece lives

| Math | File |
|---|---|
| C, v_max | `elevator_state.py` (top constants) |
| per-tick motion, ramp | `elevator_state.py` (`step_car`, `effective_speed_percent`) |
| pulley angle, screen mapping | `gui.py` (`draw_simulation`, `mm_to_design_y`, `mm_len`) |
| raw inputs (diameter, RPM, ratio) | `config.py` |

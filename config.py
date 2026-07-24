# config.py
# This file is basically just a big list of settings/numbers for the project.
# They're all kept in one place so if something needs to change (like a pin
# number) it only needs to change here instead of being hunted down across
# all the other files. :)

# ============================================================================
# PINS - edit these to match actual wiring, then just run elevator_gui.py to
# test. everything further down this file is calibration/timing/safety
# settings that don't need to change just because the wiring changed.
# ============================================================================

# MD20A motor driver (Cytron, PWM + DIR mode) - one plain digital pin sets
# direction, one PWM pin sets speed (this replaced the old two-PWM
# Sign-Magnitude wiring)
# DIR pin: LOW = forward (up), HIGH = backward (down)
# PWM pin: duty cycle 0.0-1.0 sets speed, same regardless of direction
MOTOR_DIR_PIN = 26   # direction
MOTOR_PWM_PIN = 12   # speed (PWM)

# floor LEDs - one GPIO pin per floor, floor number -> pin number
FLOOR_LED_PINS = {1: 5, 2: 6, 3: 13, 4: 19}

# NOTE: there is no position sensor on the rig right now - no potentiometer,
# no MCP3008, no IR sensors. it's just: power supply -> MD20A -> motor -> Pi
# for control. that means the app runs fully open-loop: state.py's simulated
# car position (physics-matched to the real drive) is the ONLY estimate of
# where the car actually is - nothing here confirms that against reality.

# --- Elevator layout ---
# these are the preset settings for how many floors there are and where things start
START_FLOOR = 1       # the floor the elevator starts on when the app is launched
FLOOR_COUNT = 4        # how many floors this elevator has (4 for hospital and residential building)
DEFAULT_SPEED = 50     # default motor speed out of 100 (like a percentage) when the app opens

# --- Real drive physics ---
# these numbers tie the simulation to the real machine: the motor turns a
# pulley (through a gearbox), so the car's linear speed = pulley rotational
# speed x pulley circumference. the simulated car is capped at that same
# "maximum derivative of height", so a trip in the GUI takes the same time
# the real car would take.
PULLEY_DIAMETER_MM = 72
MOTOR_RPM_BEFORE_GEARBOX = 27  # the motor's raw speed cap (confirmed: this is PRE-gearbox)
GEARBOX_RATIO = 1.0  # confirmed: 1:1 - the pulley spins at the raw motor rpm, no reduction
MAX_PULLEY_RPM = MOTOR_RPM_BEFORE_GEARBOX / GEARBOX_RATIO

# --- Motor duty-to-real-speed calibration ---
# real DC motors (especially through a gearbox, driven by the MD20A) don't
# actually move at a speed that's linearly proportional to commanded PWM
# duty - there's a deadband at the low end (needs a minimum duty just to
# overcome static friction) AND the real top speed under load can fall short
# of the theoretical max at the high end (voltage drop, current limiting,
# gearbox drag), so BOTH ends can drift off a straight-line assumption, each
# in its own direction.
#
# rather than guess a single formula for that whole curve, this is a small
# table of (commanded fraction -> real duty fraction) points, built up from
# actual testing against the real rig: 70-80% commanded was confirmed
# accurate (kept as an identity mapping below). the 0.22 and 0.42 points were
# corrected from real overshoot measurements - commanding 22% overshot the
# target by 10% of a car length, and 42% overshot by 33% - by solving for
# the duty that would have made the real motor's speed actually match the
# commanded fraction (see the git history for the full derivation). the
# fixed-point math assumes the real motor's response is roughly locally
# linear near each tested value, so treat these as good estimates to refine
# further, not exact - if trips still don't match at these settings, redo
# the same math with the new measured gap and update the point here. the
# 1.0 point is still an untested guess (no real overshoot/undershoot data at
# that setting yet). anything between two points is interpolated in a
# straight line; commanded fractions past the table's first/last point just
# hold that end's value.
MOTOR_DUTY_CALIBRATION_POINTS = [
    (0.0, 0.0),
    (0.22, 0.284),  # corrected from a measured 10% overshoot at commanded 0.22
    (0.42, 0.445),  # corrected from a measured 33% overshoot at commanded 0.42
    (0.7, 0.7),     # confirmed accurate
    (0.8, 0.8),     # confirmed accurate
    (1.0, 0.85),    # still an untested guess
]


def effective_duty_fraction(commanded_fraction: float) -> float:
    # maps a commanded speed fraction (0.0-1.0, from the speed slider and the
    # accel/decel ramp) onto the real duty cycle actually sent to the motor,
    # by linearly interpolating MOTOR_DUTY_CALIBRATION_POINTS.
    #
    # used ONLY by hardware.py (the real PWM duty sent to the MD20A) - NOT
    # by elevator_state.py. the simulated car represents the INTENDED
    # behavior (commanded speed % = that % of max speed); this curve exists
    # purely to make the REAL motor match that intent despite not responding
    # linearly to duty. applying it to the simulation too would double-count
    # the correction (this was a real bug - see git history).
    if commanded_fraction <= 0:
        return 0.0
    points = MOTOR_DUTY_CALIBRATION_POINTS
    if commanded_fraction <= points[0][0]:
        return points[0][1]
    if commanded_fraction >= points[-1][0]:
        return points[-1][1]
    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        if x0 <= commanded_fraction <= x1:
            fraction_between = (commanded_fraction - x0) / (x1 - x0)
            return y0 + fraction_between * (y1 - y0)
    return points[-1][1]  # unreachable, just a safe fallback

# --- Safety ---
# this is a safety net in case something breaks, like a sensor dying or a wire
# coming loose. currently unused (there's no position sensor on the rig to
# confirm arrival against), kept here for when one gets added back.
MOTOR_STALL_TIMEOUT_SECONDS = 8.0  # seconds before giving up and calling it a stall

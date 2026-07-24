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

# --- Motor deadband compensation ---
# DC motors (especially driven through a gearbox) usually need a minimum
# duty cycle just to overcome static friction and actually start turning -
# below that "deadband," real speed does NOT scale linearly with commanded
# duty the way a naive (speed_percent / 100 = duty) model assumes. this
# matches what was seen on the real rig: matching the simulated car to the
# real one got LESS accurate at lower speed slider settings (76% was most
# accurate; lower settings drifted), which is exactly what an unmodeled
# deadband looks like.
#
# this value is a starting guess, not measured off the real motor - if trips
# still don't match reality at low speed settings, nudge it up (more of the
# low end gets pulled toward MOTOR_MIN_DUTY_FRACTION) or down (closer to the
# old straight-line assumption) and re-test.
MOTOR_MIN_DUTY_FRACTION = 0.3


def effective_duty_fraction(commanded_fraction: float) -> float:
    # maps a commanded speed fraction (0.0-1.0, from the speed slider and the
    # accel/decel ramp) onto the real duty cycle sent to the motor. any
    # positive commanded speed gets boosted up to at least
    # MOTOR_MIN_DUTY_FRACTION - enough real duty to actually overcome the
    # deadband and turn the motor - then scales up linearly from there to
    # full duty at a fully-commanded speed.
    #
    # used by BOTH hardware.py (the actual PWM duty sent to the MD20A) and
    # elevator_state.py (the simulated car's speed), so the simulation and
    # the real motor stay in sync instead of the simulation assuming a
    # straight line the real motor doesn't actually follow.
    if commanded_fraction <= 0:
        return 0.0
    return MOTOR_MIN_DUTY_FRACTION + commanded_fraction * (1 - MOTOR_MIN_DUTY_FRACTION)

# --- Safety ---
# this is a safety net in case something breaks, like a sensor dying or a wire
# coming loose. currently unused (there's no position sensor on the rig to
# confirm arrival against), kept here for when one gets added back.
MOTOR_STALL_TIMEOUT_SECONDS = 8.0  # seconds before giving up and calling it a stall

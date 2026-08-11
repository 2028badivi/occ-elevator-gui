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

# --- Open-loop calibration ---
# with no position sensor, the sim's car position is the only estimate of
# where the real car is, and it assumes motor speed is perfectly proportional
# to PWM duty. real motors aren't: load + friction slow the car going UP, and
# gravity assists it going DOWN, so the sim over-estimates position on up
# trips and under-estimates on down trips. these two scales let each
# direction's simulated speed be trimmed to match the real car - time a real
# full-shaft trip in each direction and set scale = (sim trip time) / (real
# trip time). 1.0 means "trust the raw physics" (no correction).
UP_SPEED_SCALE = 1.0
DOWN_SPEED_SCALE = 1.0

# real DC motors also have a DEAD ZONE: below some PWM duty the motor hums or
# stalls instead of turning, while the sim (speed proportional to duty) keeps
# gliding - that mismatch is worst at the end of a trip, where the decel ramp
# used to command as little as 15% OF THE SLIDER value (slider at 50% -> 7.5%
# duty) and the real car quietly stopped short of the floor. this is an
# ABSOLUTE duty floor: any nonzero move command is clamped up to at least
# this many percent, keeping the real motor in the range where speed actually
# tracks duty. raise it if the car still stalls short near floors; lower it
# if arrivals overshoot / feel too fast at the very end.
MIN_DUTY_PERCENT = 20

# --- Safety ---
# this is a safety net in case something breaks, like a sensor dying or a wire
# coming loose. currently unused (there's no position sensor on the rig to
# confirm arrival against), kept here for when one gets added back.
MOTOR_STALL_TIMEOUT_SECONDS = 8.0  # seconds before giving up and calling it a stall

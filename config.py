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
MOTOR_PWM_FREQUENCY_HZ = 100  # explicit gpiozero default; keep fixed while calibrating

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
FLOOR_HEIGHTS_MM = {1: 0, 2: 324, 3: 648, 4: 972}  # measured from shaft bottom
CAR_HEIGHT_MM = 254

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
# where the real car is. Load + friction slow the car going UP, while gravity
# changes its speed going DOWN. These two scales trim the calculated 101.8mm/s
# full-duty speed independently in each direction. Fit them from fixed-duty
# stopwatch runs with motion_calibration.py; 1.0 trusts the raw pulley math.
UP_SPEED_SCALE = 1.0
DOWN_SPEED_SCALE = 1.0

# PWM duty is not the same thing as motor speed. A loaded DC motor generally
# has a dead zone: duty below a direction-dependent threshold produces no
# useful motion. The motion model treats speed above that threshold as linear:
#
#   speed = full_speed * (duty - deadzone) / (100 - deadzone)
#
# The inverse mapping is used for motor commands, so asking for 10% of the
# measured full speed produces a duty just above the dead zone rather than a
# raw 10% command that may only hum. Leave these at 0 until measured; use
# motion_calibration.py with stopwatch data to fit them instead of guessing.
UP_PWM_DEADZONE_PERCENT = 0.0
DOWN_PWM_DEADZONE_PERCENT = 0.0

# --- Bottom homing ---
# floor 1 IS the physical bottom of the shaft - a hard mechanical stop. that
# makes it the one place the car's true position is knowable without any
# sensor: drive down far enough and the car is definitely resting at 0mm.
# So every leg that targets floor 1 deliberately overdrives its command by
# this many mm past the floor-1 coordinate. If the real car was running
# behind the estimate (the usual "stops just short of the bottom" error), the
# extra travel closes the gap and the car settles on the physical stop; the
# estimator then anchors itself to exactly 0mm on arrival. Any accumulated
# open-loop drift is wiped out every time the car visits floor 1 - which the
# 1<->4 demo loop does once per cycle. The overdrive happens inside the decel
# ramp (at the slow end-of-trip speed), so worst case is a couple of seconds
# of gentle pull against the stop / slack cable, not a slam.
# Set to 0 to disable homing entirely.
#
# IMPORTANT once the drive is well calibrated: keep this no larger than the
# real remaining "stops short of the bottom" gap. Any EXCESS overdrive pays
# that much cable out against the stop on every floor-1 visit, and the next
# upward leg spends the same distance winding the slack back in before the
# car actually rises - the estimator can't see slack, so every following
# floor lands that much low while the display still claims full height (and
# on the endless demo loop the error compounds every cycle). Undersized is
# safe (just corrects less per visit); oversized is not.
BOTTOM_HOMING_OVERDRIVE_MM = 30.0

# --- Safety ---
# this is a safety net in case something breaks, like a sensor dying or a wire
# coming loose. currently unused (there's no position sensor on the rig to
# confirm arrival against), kept here for when one gets added back.
MOTOR_STALL_TIMEOUT_SECONDS = 8.0  # seconds before giving up and calling it a stall

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

# MD20A motor driver (Cytron, Sign-Magnitude PWM1/PWM2 mode) - each PWM input
# goes to one of these GPIO pins
MOTOR_PWM1_FORWARD_PIN = 17   # PWM1 - drives the motor forward/up
MOTOR_PWM2_REVERSE_PIN = 18   # PWM2 - drives the motor backward/down

# potentiometer - read through the MCP3008 ADC, on this channel (0-7)
MCP3008_POT_CHANNEL = 0

# floor LEDs - one GPIO pin per floor, floor number -> pin number
FLOOR_LED_PINS = {1: 5, 2: 6, 3: 13, 4: 19}

# IR floor sensors - also read through the MCP3008, one channel per floor.
# DISABLED FOR NOW: kept commented out here AND in the matching block inside
# HardwareController.__init__ (hardware.py), so the elevator can be tested on
# just the pot for position feedback. uncomment BOTH blocks together once
# ready to bring the IR sensors into the test.
# IR_SENSOR_MCP3008_CHANNELS = {1: 1, 2: 2, 3: 3, 4: 4}

# MCP3008 <-> Pi SPI wiring - these are fixed by the Pi's hardware SPI0 bus,
# not something to change unless wiring to a different SPI interface entirely
# Pi MOSI (GPIO10, physical pin 19) -> MCP3008 DIN  (pin 11)
# Pi MISO (GPIO9,  physical pin 21) -> MCP3008 DOUT (pin 13)
# Pi SCLK (GPIO11, physical pin 23) -> MCP3008 CLK  (pin 12)
# Pi CE0  (GPIO8,  physical pin 24) -> MCP3008 CS   (pin 10)
# Pi 3.3V -> MCP3008 VDD (pin 16) and VREF (pin 15)
# Pi GND  -> MCP3008 AGND (pin 14) and DGND (pin 9)
#
# pot wiring: one outer leg -> Pi 3.3V, other outer leg -> Pi GND, middle
# wiper leg -> MCP3008 CH0 (pin 1) - or whichever channel is set above

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
PULLEY_DIAMETER_MM = 74
MOTOR_RPM_BEFORE_GEARBOX = 27  # the motor's raw speed cap (confirmed: this is PRE-gearbox)
GEARBOX_RATIO = 1.0  # TODO: the real gear ratio isn't known yet - the pulley
                     # spins at motor rpm / this ratio, so 1.0 behaves as
                     # direct drive until the actual ratio gets filled in
MAX_PULLEY_RPM = MOTOR_RPM_BEFORE_GEARBOX / GEARBOX_RATIO

# --- Position potentiometer calibration ---
# fraction-of-range thresholds (0.0-1.0 - gpiozero's MCP3008.value is already
# normalized to this range) mapping pot position to a floor. the code walks
# down the list and the first one that matches wins - so if the reading is
# 0.85 or higher, that's floor 4, and so on down to floor 1 (these numbers
# are just guesses for now and need to be tested/calibrated later)
potentiometer_THRESHOLDS = [
    (0.85, 4),
    (0.60, 3),
    (0.35, 2),
    (0.00, 1),
]

# --- IR sensor calibration ---
# each sensor module has its own onboard comparator and really just outputs a
# plain two-level HIGH/LOW signal, not a true analog range - but reading it
# through the ADC still means comparing against a threshold rather than
# treating it as a literal digital value. Long story short we need the ADC to
# handle the signals and give intermediate values rather than just plain two
# level signals
IR_DETECT_THRESHOLD = 0.35  # if the sensor reading is above this, it's considered triggered
# NOTE: this is basically a guess right now, still needs to be tested with
# the real sensors once they're wired and uncommented

# whether "detected" means the ADC reading is above or below IR_DETECT_THRESHOLD
# depends on the exact sensor module, and can't be known for sure until it's
# actually wired up and tested. Flip to False if it is
IR_SENSOR_ACTIVE_HIGH = True

# --- Safety ---
# Tyler's Recommendation
# this is a safety net in case something breaks, like a sensor dying or a wire
# coming loose. if the motor is told "go to floor 3" and it NEVER gets
# confirmation that it arrived within this many seconds, power gets cut
# instead of letting the motor spin forever (which could break something or overheat)
MOTOR_STALL_TIMEOUT_SECONDS = 8.0  # seconds before giving up and calling it a stall

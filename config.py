# config.py
# This file is basically just a big list of settings/numbers for the project.
# They're all kept in one place so if something needs to change (like a pin
# number) it only needs to change here instead of being hunted down across
# all the other files. :)

# --- Elevator layout ---
# these are the preset settings for how many floors there are and where things start
START_FLOOR = 1       # the floor the elevator starts on when the app is launched
FLOOR_COUNT = 4        # how many floors this elevator has (4 for hospital and residential building)
DEFAULT_SPEED = 50     # default motor speed out of 100 (like a percentage) when the app opens

# --- MD20A motor driver (Cytron, wired in PWM1/PWM2 -multi-directional(up/down) setup-) ---
# this is the motor driver board that actually spins the motor
# it needs two pins: one for going forward (up) and one for going backward (down)
# each pin gets a PWM signal, which is basically a fast on/off signal that controls speed
# (PWM1 = forward pin, PWM2 = reverse pin, this matches gpiozero's Motor class)
MOTOR_PWM1_FORWARD_PIN = 17   # GPIO pin number for forward/up
MOTOR_PWM2_REVERSE_PIN = 18   # GPIO pin number for backward/down

# --- MCP3008 ADC (SPI) ---
# both the potentiometer and the IR floor sensors are read through this one
# chip - the Pi's own GPIO pins can only read HIGH/LOW, so this chip is what
# actually does analog-to-digital conversion. it has 8 channels total, so
# there's room for the pot (1 channel) plus all 4 IR sensors with 3 spare.
#
# Pi MOSI (GPIO10, physical pin 19) -> MCP3008 DIN  (pin 11)
# Pi MISO (GPIO9,  physical pin 21) -> MCP3008 DOUT (pin 13)
# Pi SCLK (GPIO11, physical pin 23) -> MCP3008 CLK  (pin 12)
# Pi CE0  (GPIO8,  physical pin 24) -> MCP3008 CS   (pin 10)
# Pi 3.3V -> MCP3008 VDD (pin 16) and VREF (pin 15)
# Pi GND  -> MCP3008 AGND (pin 14) and DGND (pin 9)
# --- Position potentiometer ---
# pot wiring: one outer leg -> Pi 3.3V, other outer leg -> Pi GND, middle
# wiper leg -> MCP3008 CH0 (pin 1) - same 3.3V/GND rail the MCP3008 itself
# uses for VDD/VREF, so the pot's output range matches the ADC's input range
MCP3008_POT_CHANNEL = 0
# fraction-of-range thresholds (0.0-1.0 - gpiozero's MCP3008.value is already
# normalized to this range) mapping pot position to a floor. the code walks
# down the list and the first one that matches wins - so if the reading is
# 0.85 or higher, that's floor 4, and so on down to floor 1 (these numbers
# are just guesses for now and need to be tested/calibrated later)
#}
potentiometer_THRESHOLDS = [
    (0.85, 4),
    (0.60, 3),
    (0.35, 2),
    (0.00, 1),
]

# --- Floor position sensors (IR) ---
# also read through the same MCP3008. each sensor module has its own onboard
# comparator and really just outputs a plain two-level HIGH/LOW signal, not a
# true analog range - but reading it through the ADC still means comparing
# against a threshold rather than treating it as a literal digital value. 
#Long story short we need the ADC to handle the signals and give intermediate values rather than just plain two level signals
#
# DISABLED FOR NOW: the setup code for these sensors is commented out in
# HardwareController.__init__ (hardware.py) so the elevator can be tested
# using just the pot for position feedback. uncomment IR_SENSOR_MCP3008_CHANNELS !!!!!
# below AND the matching block in hardware.py once ready to bring the IR
# sensors into the test.
# IR_SENSOR_MCP3008_CHANNELS = {1: 1, 2: 2, 3: 3, 4: 4}

IR_DETECT_THRESHOLD = 0.35  # if the sensor reading is above this, it's considered triggered
# NOTE: this is basically a guess right now, still needs to be tested with
# the real sensors once they're wired and uncommented

# whether "detected" means the ADC reading is above or below IR_DETECT_THRESHOLD
# depends on the exact sensor module, and can't be known for sure until it's
# actually wired up and tested. Flip to False if it is 
IR_SENSOR_ACTIVE_HIGH = True

# little LED lights, one per floor, so the "active" floor is visible on the board
FLOOR_LED_PINS = {1: 5, 2: 6, 3: 13, 4: 19}

# --- Safety --- 
# Tyler's Recommendation
# this is a safety net in case something breaks, like a sensor dying or a wire
# coming loose. if the motor is told "go to floor 3" and it NEVER gets
# confirmation that it arrived within this many seconds, power gets cut
# instead of letting the motor spin forever (which could break something or overheat)
MOTOR_STALL_TIMEOUT_SECONDS = 8.0  # seconds before giving up and calling it a stall

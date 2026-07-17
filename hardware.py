# hardware.py
# This file is all the code that actually talks to the real physical parts:
# the motor, the LEDs, and the potentiometer + IR floor sensors (both of
# which are read through the same MCP3008 ADC chip over SPI).
#
# One important thing: if this code is NOT running on an actual Raspberry Pi
# (like when testing on a laptop), the import below will fail and
# GPIO_AVAILABLE will be False. When that happens everything in here just
# quietly does nothing instead of crashing, so the app still opens and the
# GUI is still visible even without the real hardware plugged in.

import config

try:
    # these libraries only actually work on a real Pi. no pin_factory is
    # specified anywhere below - gpiozero auto-detects the right backend for
    # whatever OS it's running on (lgpio on this Pi 4B + Ubuntu 24.04 setup;
    # RPi.GPIO doesn't work reliably on Ubuntu, so this is deliberately NOT
    # hardcoded to a specific backend the way an older PiGPIOFactory-based
    # version of this file used to be)
    from gpiozero import LED, MCP3008, Motor
    GPIO_AVAILABLE = True
except Exception:
    # if literally anything goes wrong importing these, just assume no hardware
    GPIO_AVAILABLE = False


class HardwareController:
    # This is basically the "brain" that owns all the actual hardware objects
    # (the motor, the sensors, the LEDs) and gives the rest of the app simple
    # functions to call instead of dealing with gpiozero directly everywhere.

    def __init__(self):
        self.is_gpio = GPIO_AVAILABLE  # flips to False below if setup fails for any reason
        self.motor = None
        self.pot = None
        self.ir_sensors = {}
        self.floor_leds = {}

        if self.is_gpio:
            try:
                # set up the motor - forward pin drives it up, backward pin drives it down
                self.motor = Motor(
                    forward=config.MOTOR_PWM1_FORWARD_PIN,
                    backward=config.MOTOR_PWM2_REVERSE_PIN,
                    pwm=True,
                )
                # one LED object per floor, so each can be turned on/off individually
                self.floor_leds = {
                    floor: LED(pin)
                    for floor, pin in config.FLOOR_LED_PINS.items()
                }
                # potentiometer position, read through the MCP3008 ADC
                self.pot = MCP3008(channel=config.MCP3008_POT_CHANNEL)

                # --- IR floor sensors: DISABLED FOR NOW ---
                #Williams recommendation
                # commented out so the elevator can be tested using just the
                # pot for position feedback. each sensor's own output is a
                # plain HIGH/LOW from an onboard comparator, so reading it
                # through the MCP3008 just means thresholding a two-level
                # signal rather than a true analog range, but it can still
                # share the same chip as the pot (channels 1-4 here, pot on
                # channel 0). uncomment this block (and
                # IR_SENSOR_MCP3008_CHANNELS in config.py) once ready to bring
                # the IR sensors into the test.
                # self.ir_sensors = {
                #     floor: MCP3008(channel=channel)
                #     for floor, channel in config.IR_SENSOR_MCP3008_CHANNELS.items()
                # }
            except Exception as exc:
                # if ANYTHING above fails (missing wiring, daemon not running,
                # wrong pin, whatever), the whole program shouldn't crash -
                # just print what happened and fall back to simulation-only mode
                print(f"[hardware] GPIO init failed, falling back to simulation-only mode: {exc}")
                self.is_gpio = False

    def read_potentiometer(self) -> dict:
        # reads the pot's position straight from the MCP3008 - gpiozero's
        # MCP3008.value is already normalized to a 0.0-1.0 fraction, so no
        # extra math is needed here like the old RC-timing approach required
        if self.is_gpio and self.pot:
            try:
                return {"fraction": float(self.pot.value)}
            except Exception as exc:
                print(f"[hardware] pot read failed: {exc}")
        # if there's no real hardware (or the read failed), just return zero
        # since the real position can't be known without the actual sensor
        return {"fraction": 0.0}

    def get_floor_from_potentiometer(self, fraction: float) -> int:
        # walks down the list of thresholds from config.py and returns the
        # first floor number whose threshold the reading is above or equal to
        for threshold, floor in config.potentiometer_THRESHOLDS:
            if fraction >= threshold:
                return floor
        return 1  # just in case nothing matched, default back to floor 1

    def _is_ir_sensor_triggered(self, sensor) -> bool:
        # each sensor is read as an analog value (0.0-1.0) through the
        # MCP3008. the sensor itself really only ever outputs a two-level
        # HIGH/LOW signal, but reading it through the ADC still means
        # comparing against a threshold rather than treating it as a literal
        # boolean - and whether "triggered" means a high or low reading
        # depends on the specific sensor module (see the IR_SENSOR_ACTIVE_HIGH
        # note in config.py), so this is the one place that polarity gets applied
        try:
            reading_is_high = float(sensor.value) >= config.IR_DETECT_THRESHOLD
        except Exception:
            return False
        return reading_is_high if config.IR_SENSOR_ACTIVE_HIGH else not reading_is_high

    def detect_floor_from_ir(self):
        # looks at all 4 IR sensors and figures out which one (if any) is
        # currently "seeing" the elevator car. returns None if nothing is
        # triggered (like if the car is between floors, or - right now - if
        # the IR sensors are commented out in __init__ and self.ir_sensors is
        # empty, which just makes this always fall through to the pot instead)
        #
        # if more than one sensor is somehow triggered at once (shouldn't
        # normally happen), this just goes with whichever floor number is
        # lowest, since something has to be picked
        if not self.is_gpio:
            return None
        triggered_floors = [
            floor for floor, sensor in self.ir_sensors.items() if self._is_ir_sensor_triggered(sensor)
        ]
        return min(triggered_floors) if triggered_floors else None

    def get_current_floor(self, pot_reading: dict = None) -> int:
        # This is THE function that everything should call when it needs to
        # know "where is the elevator right now." It tries the IR sensors
        # first since those are more accurate/direct, and only falls back to
        # the potentiometer reading if none of the IR sensors are triggered.
        #
        # IMPORTANT: every other part of the code (like deciding which way to
        # spin the motor) also calls this SAME function, instead of some
        # places checking IR and other places checking the pot separately.
        # Previously that split led to a bug where those two could disagree
        # with each other, which was confusing and hard to track down.
        #
        # pot_reading is optional: if the caller already did a
        # read_potentiometer() this frame (say, for the diagnostics display),
        # it can be handed in here to avoid triggering a second physical read
        if not self.is_gpio:
            return config.START_FLOOR
        ir_floor = self.detect_floor_from_ir()
        if ir_floor is not None:
            return ir_floor
        if pot_reading is None:
            pot_reading = self.read_potentiometer()
        return self.get_floor_from_potentiometer(pot_reading["fraction"])

    def update_floor_leds(self, active_floor: int) -> None:
        # turns on the LED for whichever floor is currently active, and turns
        # off all the other ones
        if not self.is_gpio:
            return
        for floor, led in self.floor_leds.items():
            led.value = floor == active_floor

    def floor_presence(self) -> dict:
        # returns a dictionary like {1: True, 2: False, 3: False, 4: False}
        # showing which floor sensors are currently triggered (more than one
        # can be true if the car is between floors and neither beam is fully
        # broken, or if there's a sensor glitch). comes back empty right now
        # since self.ir_sensors stays empty while the IR sensor setup in
        # __init__ is commented out
        return {floor: self._is_ir_sensor_triggered(sensor) for floor, sensor in self.ir_sensors.items()}

    def ir_raw_readings(self) -> dict:
        # same info as floor_presence, just kept as a separate name since this
        # is the one used specifically for the on-screen diagnostics readout
        return self.floor_presence()

    def move_toward(self, target_floor: int, speed: int) -> None:
        # tells the motor to spin toward whatever floor is targeted. speed
        # comes in as 0-100 (like a percent) since that's easier to think
        # about, but the motor library wants 0.0-1.0, so it gets converted here
        if not self.is_gpio or self.motor is None:
            return
        current = self.get_current_floor()
        duty = max(0.0, min(1.0, speed / 100.0))
        if target_floor > current:
            self.motor.forward(duty)
        elif target_floor < current:
            self.motor.backward(duty)
        else:
            # already there, so just stop instead of spinning uselessly
            self.stop()

    def stop(self) -> None:
        # cuts power to the motor completely, used for normal stops AND for
        # emergency stop / stall safety
        if self.is_gpio and self.motor is not None:
            self.motor.stop()

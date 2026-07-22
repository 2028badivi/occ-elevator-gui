# hardware.py
# This file is all the code that actually talks to the real physical parts:
# the motor and the floor LEDs. There is no position sensor on the rig right
# now (no potentiometer, no MCP3008, no IR sensors) - it's just a power
# supply, the MD20A motor driver, and the Pi. That means this file has no way
# to confirm where the car actually is; elevator_state.py's simulated
# position (physics-matched to the real drive) is the only estimate of that,
# and gui.py is responsible for telling this file which way to spin the motor.
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
    from gpiozero import LED, DigitalOutputDevice, PWMOutputDevice
    GPIO_AVAILABLE = True
except Exception:
    # if literally anything goes wrong importing these, just assume no hardware
    GPIO_AVAILABLE = False


class HardwareController:
    # This is basically the "brain" that owns all the actual hardware objects
    # (the motor, the floor LEDs) and gives the rest of the app simple
    # functions to call instead of dealing with gpiozero directly everywhere.

    def __init__(self):
        # is_gpio just means "gpiozero imported fine, this is a real Linux
        # box that can talk to GPIO at all" - it does NOT mean every piece of
        # hardware below successfully initialized. each one gets its own
        # try/except further down, specifically so a problem with ONE piece
        # can't silently disable a perfectly working one just because they
        # used to share one big try/except and one shared failure flag.
        self.is_gpio = GPIO_AVAILABLE
        self.motor_dir = None
        self.motor_pwm = None
        self.floor_leds = {}

        if not self.is_gpio:
            return

        # set up the motor - one digital pin for direction (LOW =
        # forward/up, HIGH = backward/down), one PWM pin for speed
        try:
            self.motor_dir = DigitalOutputDevice(config.MOTOR_DIR_PIN)
            self.motor_pwm = PWMOutputDevice(config.MOTOR_PWM_PIN)
        except Exception as exc:
            print(f"[hardware] motor init failed (check MOTOR_DIR_PIN/MOTOR_PWM_PIN wiring): {exc}")

        # one LED object per floor, so each can be turned on/off individually
        try:
            self.floor_leds = {
                floor: LED(pin)
                for floor, pin in config.FLOOR_LED_PINS.items()
            }
        except Exception as exc:
            print(f"[hardware] floor LED init failed: {exc}")

    def update_floor_leds(self, active_floor: int) -> None:
        # turns on the LED for whichever floor is currently active (based on
        # the simulated state, since there's no sensor to confirm this
        # against), and turns off all the other ones
        for floor, led in self.floor_leds.items():
            led.value = floor == active_floor

    def move_toward(self, direction: int, speed: int) -> None:
        # tells the motor which way to spin and how fast. direction comes
        # from ElevatorState.direction_to_target(): +1 = up, -1 = down, 0 =
        # already there. speed comes in as 0-100 (like a percent) since
        # that's easier to think about, but the motor library wants 0.0-1.0,
        # so it gets converted here.
        if self.motor_pwm is None or self.motor_dir is None:
            return
        if direction == 0:
            self.stop()
            return
        duty = max(0.0, min(1.0, speed / 100.0))
        if direction > 0:
            self.motor_dir.off()  # LOW = forward = up
        else:
            self.motor_dir.on()  # HIGH = backward = down
        self.motor_pwm.value = duty

    def stop(self) -> None:
        # cuts power to the motor completely - just zeroing the PWM duty is
        # enough, the DIR pin's state doesn't matter when there's no speed
        # driving it
        if self.motor_pwm is not None:
            self.motor_pwm.value = 0

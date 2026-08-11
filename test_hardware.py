import unittest
from unittest.mock import patch

import config
import hardware
from hardware import HardwareController


class FakeDirectionPin:
    def __init__(self, pin=None):
        self.pin = pin
        self.value = None

    def on(self):
        self.value = 1

    def off(self):
        self.value = 0


class FakePwmPin:
    def __init__(self, pin=None, frequency=None):
        self.pin = pin
        self.frequency = frequency
        self.value = None


class FakeLed:
    def __init__(self, pin):
        self.pin = pin
        self.value = False


class HardwareControllerTests(unittest.TestCase):
    def setUp(self):
        self.controller = HardwareController.__new__(HardwareController)
        self.controller.motor_dir = FakeDirectionPin()
        self.controller.motor_pwm = FakePwmPin()
        self.controller.floor_leds = {}

    def test_pi_controller_uses_configured_bcm_pins_and_100hz_pwm(self):
        with (
            patch.object(hardware, "GPIO_AVAILABLE", True),
            patch.object(hardware, "DigitalOutputDevice", FakeDirectionPin, create=True),
            patch.object(hardware, "PWMOutputDevice", FakePwmPin, create=True),
            patch.object(hardware, "LED", FakeLed, create=True),
        ):
            controller = HardwareController()
        self.assertEqual(controller.motor_dir.pin, config.MOTOR_DIR_PIN)
        self.assertEqual(controller.motor_pwm.pin, config.MOTOR_PWM_PIN)
        self.assertEqual(controller.motor_pwm.frequency, config.MOTOR_PWM_FREQUENCY_HZ)
        self.assertEqual(
            {floor: led.pin for floor, led in controller.floor_leds.items()},
            config.FLOOR_LED_PINS,
        )

    def test_up_uses_low_direction_and_requested_duty(self):
        self.controller.move_toward(1, 37.5)
        self.assertEqual(self.controller.motor_dir.value, 0)
        self.assertAlmostEqual(self.controller.motor_pwm.value, 0.375)

    def test_down_uses_high_direction_and_requested_duty(self):
        self.controller.move_toward(-1, 62.5)
        self.assertEqual(self.controller.motor_dir.value, 1)
        self.assertAlmostEqual(self.controller.motor_pwm.value, 0.625)

    def test_zero_direction_stops_pwm(self):
        self.controller.motor_pwm.value = 0.5
        self.controller.move_toward(0, 50)
        self.assertEqual(self.controller.motor_pwm.value, 0)

    def test_duty_is_clamped_to_valid_range(self):
        self.controller.move_toward(1, 150)
        self.assertEqual(self.controller.motor_pwm.value, 1.0)
        self.controller.move_toward(-1, -10)
        self.assertEqual(self.controller.motor_pwm.value, 0.0)


if __name__ == "__main__":
    unittest.main()

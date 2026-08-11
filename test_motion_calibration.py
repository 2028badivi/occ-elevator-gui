import unittest

from motion_calibration import fit_direction


class MotionCalibrationTests(unittest.TestCase):
    def test_recovers_deadzone_and_full_speed_from_stopwatch_samples(self):
        distance_mm = 648.0
        deadzone = 12.0
        full_speed = 82.0
        samples = []
        for duty in (25.0, 40.0, 60.0, 80.0, 100.0):
            speed = full_speed * (duty - deadzone) / (100.0 - deadzone)
            samples.append((duty, distance_mm / speed))
        result = fit_direction(samples, distance_mm, nominal_full_speed_mm_s=100.0)
        self.assertAlmostEqual(result.deadzone_percent, deadzone, places=6)
        self.assertAlmostEqual(result.full_speed_mm_s, full_speed, places=6)
        self.assertAlmostEqual(result.full_speed_scale, 0.82, places=6)
        self.assertAlmostEqual(result.rmse_mm_s, 0.0, places=6)

    def test_rejects_insufficient_samples(self):
        with self.assertRaises(ValueError):
            fit_direction([(50, 10)], distance_mm=648)

    def test_rejects_non_increasing_speed_data(self):
        with self.assertRaises(ValueError):
            fit_direction([(30, 5), (70, 10)], distance_mm=648)

    def test_rejects_zero_time_as_invalid_measurement(self):
        with self.assertRaises(ValueError):
            fit_direction([(30, 0), (70, 10)], distance_mm=648)


if __name__ == "__main__":
    unittest.main()

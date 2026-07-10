# test_elevator_state.py
# These are the unit tests - little mini-programs that check the
# ElevatorState class actually does what it's supposed to, without needing to
# open the whole GUI and click around by hand every time something changes.
# Python's built-in "unittest" library is used since it doesn't need anything
# extra installed.
#
# To run these: python -m unittest test_elevator_state
# "OK" at the bottom means everything passed; otherwise it reports exactly
# which test failed and why

import time
import unittest

import config
from elevator_state import ElevatorState, FLOOR_COORDS


class ElevatorStateTests(unittest.TestCase):
    # every method here that starts with "test_" gets run automatically by
    # unittest - that's just how the library knows what counts as a test

    def test_set_target_cancels_running_sequence(self):
        # if a sequence is running and a normal floor button gets pressed,
        # the sequence should just get cancelled completely
        state = ElevatorState()
        state.start_sequence([2, 4])
        state.set_target(3)
        self.assertEqual(state.target_floor, 3)
        self.assertFalse(state.sequence_mode)
        self.assertEqual(state.sequence_queue, [])

    def test_start_sequence_sorts_and_queues_remainder(self):
        # checking floors 4, 1, 3 (in that odd order) should still visit them
        # in the sensible order: 1, then 3, then 4
        state = ElevatorState()
        state.start_sequence([4, 1, 3])
        self.assertEqual(state.target_floor, 1)
        self.assertEqual(state.sequence_queue, [3, 4])
        self.assertTrue(state.sequence_mode)

    def test_start_sequence_ignores_empty_list(self):
        # if nothing was checked, starting a sequence shouldn't do anything weird
        state = ElevatorState()
        original_target = state.target_floor
        state.start_sequence([])
        self.assertEqual(state.target_floor, original_target)
        self.assertFalse(state.sequence_mode)

    def test_step_car_moves_toward_target_and_stops_within_tolerance(self):
        # basic sanity check: calling step_car over and over should
        # eventually get the car to the target floor and stop it there
        # (capped at 200 loops so a bug can't make this test hang forever)
        state = ElevatorState()
        state.target_floor = 4  # coords[4] = 80, which is above coords[1] = 320 (smaller y = higher up)
        for _ in range(200):
            state.step_car(speed_percent=50)
            if state.has_arrived():
                break
        self.assertTrue(state.has_arrived())
        self.assertAlmostEqual(state.car_y, FLOOR_COORDS[4], delta=1.0)

    def test_step_car_does_nothing_at_zero_speed(self):
        # if speed is 0, the car shouldn't move even a tiny bit
        state = ElevatorState()
        state.target_floor = 4
        start_y = state.car_y
        state.step_car(speed_percent=0)
        self.assertEqual(state.car_y, start_y)

    def test_on_arrival_advances_sequence_queue(self):
        # arriving at the first stop in a sequence should automatically make
        # the next stop the new target, with a brief pause before continuing
        # (so it doesn't zoom through instantly)
        state = ElevatorState()
        state.start_sequence([2, 3])
        state.car_y = FLOOR_COORDS[2]  # simulates the car sitting at floor 2
        advanced = state.on_arrival()
        self.assertTrue(advanced)
        self.assertEqual(state.current_floor, 2)
        self.assertEqual(state.target_floor, 3)
        self.assertEqual(state.sequence_queue, [])
        self.assertTrue(state.sequence_mode)
        self.assertTrue(state.is_paused())  # should be pausing at floor 2 before heading to floor 3

    def test_on_arrival_ends_sequence_when_queue_empty(self):
        # if this was the LAST floor in the sequence, sequence_mode should turn off
        state = ElevatorState()
        state.start_sequence([2])
        state.car_y = FLOOR_COORDS[2]
        state.on_arrival()
        self.assertFalse(state.sequence_mode)

    def test_on_arrival_returns_false_if_already_at_target(self):
        # calling on_arrival() when nothing actually changed shouldn't report
        # a new arrival - it should just return False
        state = ElevatorState()
        self.assertEqual(state.current_floor, state.target_floor)
        self.assertFalse(state.on_arrival())

    def test_nearest_floor_to_car(self):
        # sanity check that the "closest floor" math finds the right one
        state = ElevatorState()
        state.car_y = FLOOR_COORDS[3] + 5  # slightly off from floor 3's exact position
        self.assertEqual(state.nearest_floor_to_car(), 3)

    def test_cancel_stops_sequence_and_sets_target(self):
        # emergency stop behavior: cancel() should kill any running sequence
        # and just set a plain target floor instead
        state = ElevatorState()
        state.start_sequence([2, 4])
        state.cancel(1)
        self.assertEqual(state.target_floor, 1)
        self.assertFalse(state.sequence_mode)
        self.assertEqual(state.sequence_queue, [])

    def test_note_hardware_target_clears_when_floor_matches(self):
        # once the real sensors confirm the target was reached, the
        # stall-timer state should reset back to normal (no stall)
        state = ElevatorState()
        state.target_floor = 2
        state.note_hardware_target(1)  # simulates still being at floor 1, not arrived yet
        self.assertIsNotNone(state.hardware_target_started_at)  # the stopwatch should have started
        state.note_hardware_target(2)  # simulates reaching floor 2
        self.assertIsNone(state.hardware_target_started_at)  # the stopwatch should reset
        self.assertFalse(state.stalled)

    def test_note_hardware_target_flags_stall_after_timeout(self):
        # if too much time passes without reaching the target, this should
        # flag a stall so the motor gets shut off instead of running forever.
        # the start time is set manually to way in the past to simulate this
        # instead of actually waiting 8+ real seconds for the test to run
        state = ElevatorState()
        state.target_floor = 2
        state.hardware_target_started_at = time.monotonic() - (config.MOTOR_STALL_TIMEOUT_SECONDS + 1)
        stalled_now = state.note_hardware_target(1)  # still not at floor 2
        self.assertTrue(stalled_now)
        self.assertTrue(state.stalled)

    def test_set_target_clears_a_prior_stall_fault(self):
        # if a stall happened before, but a fresh floor button gets pressed,
        # the old fault should get wiped so it can be tried again
        state = ElevatorState()
        state.stalled = True
        state.hardware_target_started_at = time.monotonic()
        state.set_target(2)
        self.assertFalse(state.stalled)
        self.assertIsNone(state.hardware_target_started_at)


if __name__ == "__main__":
    # this also allows "python test_elevator_state.py" to be run directly,
    # instead of the python -m unittest command
    unittest.main()

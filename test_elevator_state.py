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

import math
import time
import unittest
from unittest.mock import patch

import config
from elevator_state import (
    ACCEL_DISTANCE_MM,
    ARRIVAL_TOLERANCE_MM,
    DECEL_DISTANCE_MM,
    MAX_CAR_SPEED_MM_PER_S,
    MIN_SPEED_FRACTION,
    ElevatorState,
    FLOOR_HEIGHTS_MM,
)


class ElevatorStateTests(unittest.TestCase):
    # every method here that starts with "test_" gets run automatically by
    # unittest - that's just how the library knows what counts as a test

    def test_confirmed_geometry_and_drive_math(self):
        self.assertEqual(FLOOR_HEIGHTS_MM, {1: 0, 2: 324, 3: 648, 4: 972})
        expected_max_speed = 27.0 / 60.0 * math.pi * 72.0
        self.assertAlmostEqual(MAX_CAR_SPEED_MM_PER_S, expected_max_speed)

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
        # checking floors 4, 1, 3 while already at floor 1 should skip the
        # current floor and visit the remaining stops in ascending order
        state = ElevatorState()
        state.start_sequence([4, 1, 3])
        self.assertEqual(state.target_floor, 3)
        self.assertEqual(state.sequence_queue, [4])
        self.assertTrue(state.sequence_mode)

    def test_start_sequence_with_only_current_floor_finishes_immediately(self):
        state = ElevatorState()
        state.start_sequence([1])
        self.assertFalse(state.sequence_mode)
        self.assertEqual(state.sequence_queue, [])
        self.assertTrue(state.has_arrived())

    def test_start_sequence_ignores_empty_list(self):
        # if nothing was checked, starting a sequence shouldn't do anything weird
        state = ElevatorState()
        original_target = state.target_floor
        state.start_sequence([])
        self.assertEqual(state.target_floor, original_target)
        self.assertFalse(state.sequence_mode)

    def test_step_car_moves_toward_target_and_stops_within_tolerance(self):
        # basic sanity check: calling step_car over and over should
        # eventually get the car to the target floor and stop it there.
        # each step simulates 0.1s of real time (dt=0.1); the generous loop
        # cap prevents a bug from hanging the test forever
        state = ElevatorState()
        state.target_floor = 4
        for _ in range(10000):
            state.step_car(speed_percent=50, dt=0.1)
            if state.has_arrived():
                break
        self.assertTrue(state.has_arrived())
        self.assertAlmostEqual(state.car_y, FLOOR_HEIGHTS_MM[4], delta=ARRIVAL_TOLERANCE_MM)

    def test_step_car_does_nothing_at_zero_speed(self):
        # if speed is 0, the car shouldn't move even a tiny bit
        state = ElevatorState()
        state.target_floor = 4
        start_y = state.car_y
        state.step_car(speed_percent=0, dt=0.1)
        self.assertEqual(state.car_y, start_y)

    def test_step_car_never_exceeds_real_max_speed(self):
        # THE core physics guarantee: the car's movement per unit time can
        # never exceed the real drive's capability (pulley circumference x
        # max RPM), no matter what speed is commanded. this is the "maximum
        # derivative of height" constraint - one full simulated second at
        # 100% speed, mid-cruise (no accel/decel ramp in effect), should
        # move the car exactly the real max speed and not a millimeter more
        state = ElevatorState()
        state.set_target(4)
        state.car_y = 400  # mid-shaft
        state._leg_start_y = 100  # far enough back that the accel ramp is done
        before = state.car_y
        state.step_car(speed_percent=100, dt=1.0)
        moved = abs(state.car_y - before)
        self.assertLessEqual(moved, MAX_CAR_SPEED_MM_PER_S + 1e-9)
        self.assertAlmostEqual(moved, MAX_CAR_SPEED_MM_PER_S, delta=1.0)

    def test_effective_speed_is_ramped_down_right_at_leg_start(self):
        # right at the start of a fresh move (distance_traveled == 0), the
        # ramp should hold speed down at the minimum floor, not let it jump
        # straight to full commanded speed
        state = ElevatorState()
        state.set_target(4)
        expected = round(100 * MIN_SPEED_FRACTION)
        self.assertEqual(state.effective_speed_percent(100), expected)

    def test_effective_speed_is_full_in_the_middle_of_a_long_move(self):
        # once past the accel distance and still outside the decel distance
        # from the target, the car should be at full commanded speed (the
        # "cruise" portion of the trip)
        state = ElevatorState()
        state.set_target(4)
        target_y = FLOOR_HEIGHTS_MM[4]
        # sit comfortably in the middle: far enough from both the start and
        # the 972mm target that neither ramp is in effect
        state.car_y = 400
        self.assertGreater(abs(state.car_y - state._leg_start_y), ACCEL_DISTANCE_MM)
        self.assertGreater(abs(target_y - state.car_y), DECEL_DISTANCE_MM)
        self.assertEqual(state.effective_speed_percent(100), 100)

    def test_effective_speed_ramps_down_near_the_target(self):
        # within DECEL_DISTANCE_MM of the target, speed should be reduced
        # below full but never all the way to zero
        state = ElevatorState()
        state.set_target(4)
        target_y = FLOOR_HEIGHTS_MM[4]
        state.car_y = target_y - (DECEL_DISTANCE_MM / 2)  # halfway into the decel zone, still approaching
        ramped = state.effective_speed_percent(100)
        self.assertLess(ramped, 100)
        self.assertGreaterEqual(ramped, round(100 * MIN_SPEED_FRACTION))

    def test_effective_speed_returns_zero_for_zero_input(self):
        # a commanded speed of 0 (motor stopped) should stay 0, not get
        # bumped up by the minimum-speed floor
        state = ElevatorState()
        state.set_target(4)
        self.assertEqual(state.effective_speed_percent(0), 0)

    def test_deadzone_mapping_raises_duty_without_falsely_raising_estimated_speed(self):
        with (
            patch.object(config, "UP_PWM_DEADZONE_PERCENT", 20.0),
            patch.object(config, "UP_SPEED_SCALE", 0.8),
        ):
            duty = ElevatorState.pwm_duty_for_speed(direction=1, desired_speed_percent=50.0)
            self.assertAlmostEqual(duty, 60.0)
            estimated = ElevatorState.estimated_speed_mm_s(direction=1, duty_percent=duty)
            self.assertAlmostEqual(estimated, MAX_CAR_SPEED_MM_PER_S * 0.8 * 0.5)

    def test_duty_at_or_below_deadzone_estimates_zero_motion(self):
        with patch.object(config, "DOWN_PWM_DEADZONE_PERCENT", 12.0):
            self.assertEqual(ElevatorState.estimated_speed_mm_s(-1, 12.0), 0.0)
            self.assertEqual(ElevatorState.estimated_speed_mm_s(-1, 5.0), 0.0)

    def test_motion_command_is_zero_during_sequence_pause(self):
        state = ElevatorState()
        state.target_floor = 2
        state.car_y = FLOOR_HEIGHTS_MM[2]
        state.on_arrival()
        state.target_floor = 3
        state.resume_at = time.monotonic() + 10.0
        self.assertEqual(state.motion_command(50), (0, 0.0))

    def test_all_floor_pairs_reach_and_anchor_to_exact_height(self):
        for start_floor in FLOOR_HEIGHTS_MM:
            for end_floor in FLOOR_HEIGHTS_MM:
                if start_floor == end_floor:
                    continue
                with self.subTest(start=start_floor, end=end_floor):
                    state = ElevatorState()
                    state.calibrate_to_floor(start_floor)
                    state.set_target(end_floor)
                    for _ in range(20000):
                        direction, duty = state.motion_command(50)
                        state.advance_from_command(direction, duty, dt=0.02)
                        if state.has_arrived():
                            break
                    self.assertTrue(state.has_arrived())
                    self.assertTrue(state.on_arrival())
                    self.assertEqual(state.current_floor, end_floor)
                    self.assertEqual(state.car_y, FLOOR_HEIGHTS_MM[end_floor])

    def test_step_car_still_reaches_target_despite_ramping(self):
        # the ramp shouldn't prevent the car from ever actually arriving -
        # confirms the MIN_SPEED_FRACTION floor keeps it making progress
        state = ElevatorState()
        state.set_target(4)
        for _ in range(10000):
            state.step_car(speed_percent=100, dt=0.1)
            if state.has_arrived():
                break
        self.assertTrue(state.has_arrived())

    def test_calibrate_to_floor_sets_position_without_moving(self):
        # simulates telling the software "the car is actually at floor 4" on
        # launch, when it otherwise assumed floor 1. should land exactly on
        # that floor's height and NOT think it needs to move anywhere.
        state = ElevatorState()
        state.start_sequence([2, 3])  # anything running should get cancelled
        state.calibrate_to_floor(4)
        self.assertEqual(state.car_y, FLOOR_HEIGHTS_MM[4])
        self.assertEqual(state.current_floor, 4)
        self.assertEqual(state.target_floor, 4)
        self.assertFalse(state.sequence_mode)
        self.assertEqual(state.sequence_queue, [])
        self.assertTrue(state.has_arrived())
        self.assertEqual(state.direction_to_target(), 0)

    def test_on_arrival_advances_sequence_queue(self):
        # arriving at the first stop in a sequence should automatically make
        # the next stop the new target, with a brief pause before continuing
        # (so it doesn't zoom through instantly)
        state = ElevatorState()
        state.start_sequence([2, 3])
        state.car_y = FLOOR_HEIGHTS_MM[2]  # simulates the car sitting at floor 2
        advanced = state.on_arrival()
        self.assertTrue(advanced)
        self.assertEqual(state.current_floor, 2)
        self.assertEqual(state.target_floor, 3)
        self.assertEqual(state.sequence_queue, [])
        self.assertTrue(state.sequence_mode)
        self.assertTrue(state.is_paused())  # should be pausing at floor 2 before heading to floor 3

    def test_on_arrival_resets_leg_start_for_next_stop(self):
        # each stop in a sequence should get its own fresh accel ramp,
        # starting from wherever the car actually is when that leg begins
        state = ElevatorState()
        state.start_sequence([2, 3])
        state.car_y = FLOOR_HEIGHTS_MM[2]
        state.on_arrival()
        self.assertEqual(state._leg_start_y, FLOOR_HEIGHTS_MM[2])

    def test_on_arrival_ends_sequence_when_queue_empty(self):
        # if this was the LAST floor in the sequence, sequence_mode should turn off
        state = ElevatorState()
        state.start_sequence([2])
        state.car_y = FLOOR_HEIGHTS_MM[2]
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
        state.car_y = FLOOR_HEIGHTS_MM[3] + 5  # slightly off from floor 3's exact position
        self.assertEqual(state.nearest_floor_to_car(), 3)

    def test_cancel_stops_sequence_and_sets_target(self):
        # emergency stop behavior: cancel() should kill any running sequence,
        # set a plain target floor, and snap car_y to that floor's exact
        # height so the stop actually sticks (see the comment in cancel()
        # about the jerking bug this prevents)
        state = ElevatorState()
        state.start_sequence([2, 4])
        state.cancel(1)
        self.assertEqual(state.target_floor, 1)
        self.assertEqual(state.car_y, FLOOR_HEIGHTS_MM[1])
        self.assertEqual(state.current_floor, 1)
        self.assertTrue(state.has_arrived())
        self.assertEqual(state.direction_to_target(), 0)
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

    def _run_until_arrived(self, state, speed=50, dt=0.02, ticks=40000):
        # drives the motion_command/advance_from_command loop the same way
        # glide_step() does, until the current leg reports arrival
        for _ in range(ticks):
            direction, duty = state.motion_command(speed)
            state.advance_from_command(direction, duty, dt=dt)
            if state.has_arrived():
                return
        self.fail("car never arrived within the tick budget")

    def test_homing_leg_overdrives_below_floor1_then_anchors_to_zero(self):
        # a leg into floor 1 must keep the motor commanded PAST the floor-1
        # coordinate by the configured overdrive (so the real car actually
        # settles on the physical shaft bottom), then anchor the estimate to
        # exactly 0mm on arrival
        state = ElevatorState()
        state.calibrate_to_floor(2)
        state.set_target(1)
        lowest_commanded = state.car_y
        for _ in range(40000):
            direction, duty = state.motion_command(50)
            state.advance_from_command(direction, duty, dt=0.02)
            lowest_commanded = min(lowest_commanded, state.car_y)
            if state.has_arrived():
                break
        self.assertTrue(state.has_arrived())
        expected_overdrive_point = FLOOR_HEIGHTS_MM[1] - config.BOTTOM_HOMING_OVERDRIVE_MM
        self.assertAlmostEqual(lowest_commanded, expected_overdrive_point, delta=ARRIVAL_TOLERANCE_MM)
        self.assertTrue(state.on_arrival())
        self.assertEqual(state.car_y, FLOOR_HEIGHTS_MM[1])
        self.assertEqual(state.current_floor, 1)
        # settled: reads as arrived at floor 1 and commands no further motion
        self.assertTrue(state.has_arrived())
        self.assertEqual(state.motion_command(50), (0, 0.0))

    def test_pressing_floor1_while_anchored_at_floor1_is_a_noop(self):
        # a parked car can't drift, so re-selecting floor 1 while already
        # anchored there must NOT re-run the homing leg - each pointless
        # overdrive would physically pay out slack cable against the stop
        # (button spam used to inject ~30mm of slack per press)
        state = ElevatorState()  # starts at floor 1, anchored at 0mm
        state.set_target(1)
        self.assertTrue(state.has_arrived())
        self.assertEqual(state.motion_command(50), (0, 0.0))

    def test_floor1_command_still_homes_when_not_anchored(self):
        # the no-op guard must only apply when the car is truly anchored at
        # 0mm - if the estimate says floor 1 but the height is off (e.g.
        # after an e-stop nearby), a floor-1 command still runs a homing leg
        state = ElevatorState()
        state.current_floor = 1
        state.car_y = 5.0  # believed near floor 1 but not anchored
        state.set_target(1)
        self.assertFalse(state.has_arrived())
        self.assertEqual(state.direction_to_target(), -1)

    def test_interrupting_a_homing_leg_clamps_the_estimate_to_the_shaft_bottom(self):
        # pressing another floor mid-overdrive must not carry the physically
        # impossible negative estimate into the new leg - that would
        # over-command the trip by up to the overdrive (driving the real car
        # past the top floor into the clearance)
        state = ElevatorState()
        state.calibrate_to_floor(2)
        state.set_target(1)
        for _ in range(40000):
            direction, duty = state.motion_command(50)
            state.advance_from_command(direction, duty, dt=0.02)
            if state.car_y < -5.0:
                break
        self.assertLess(state.car_y, 0)  # mid-overdrive, below the floor-1 coordinate
        state.set_target(4)  # interrupt the homing leg
        self.assertEqual(state.car_y, FLOOR_HEIGHTS_MM[1])  # clamped back to the shaft bottom
        self.assertEqual(state._leg_start_y, FLOOR_HEIGHTS_MM[1])

    def test_sequence_starting_at_current_floor_mid_leg_does_not_deadlock(self):
        # a sequence whose FIRST stop equals current_floor, started while a
        # leg is in flight (e.g. during the demo's run up from floor 1), must
        # still advance its queue when the car arrives back - the same-floor
        # early return in on_arrival used to leave it stuck forever
        state = ElevatorState()
        state.start_demo()  # current stays 1, heading up to the top
        state.car_y = 100.0  # mid-flight
        state.start_sequence([1, 3])
        self.assertEqual(state.target_floor, 1)
        self.assertEqual(state.sequence_queue, [3])
        self._run_until_arrived(state)
        self.assertTrue(state.on_arrival())  # queue must advance despite current == target
        self.assertEqual(state.car_y, FLOOR_HEIGHTS_MM[1])
        self.assertEqual(state.target_floor, 3)
        self.assertEqual(state.sequence_queue, [])
        self.assertTrue(state.sequence_mode)

    def test_demo_bounce_at_bottom_is_a_homing_leg(self):
        # the demo loop's leg back down to floor 1 must home into the shaft
        # bottom, so drift gets wiped once per demo cycle
        state = ElevatorState()
        state.start_demo()  # at floor 1 -> heads to the top first
        state.car_y = FLOOR_HEIGHTS_MM[config.FLOOR_COUNT]
        self.assertTrue(state.on_arrival())  # bounce: retargets floor 1
        self.assertEqual(state.target_floor, 1)
        state.resume_at = None  # skip the end-of-travel pause for the test
        self._run_until_arrived(state)
        self.assertLess(state.car_y, FLOOR_HEIGHTS_MM[1])  # parked at the overdrive point
        self.assertTrue(state.on_arrival())
        self.assertEqual(state.car_y, FLOOR_HEIGHTS_MM[1])  # anchored back to the true 0
        self.assertEqual(state.target_floor, config.FLOOR_COUNT)  # bounced back up

    def test_zero_overdrive_disables_homing(self):
        with patch.object(config, "BOTTOM_HOMING_OVERDRIVE_MM", 0.0):
            state = ElevatorState()
            state.calibrate_to_floor(2)
            state.set_target(1)
            self._run_until_arrived(state)
            # never commanded below the plain floor-1 coordinate
            self.assertGreaterEqual(state.car_y, FLOOR_HEIGHTS_MM[1] - ARRIVAL_TOLERANCE_MM)

    def test_emergency_stop_cancels_a_homing_leg(self):
        # e-stop during a homing run must not leave the homing flag armed -
        # nothing should keep (or resume) driving into the bottom afterwards
        state = ElevatorState()
        state.calibrate_to_floor(2)
        state.set_target(1)
        state.car_y = 10.0  # mid-homing, above the floor but heading down
        state.cancel(state.nearest_floor_to_car())
        self.assertTrue(state.has_arrived())
        self.assertEqual(state.motion_command(50), (0, 0.0))

    def test_demo_pause_does_not_accumulate_simulated_motion(self):
        state = ElevatorState()
        state.start_demo()
        state.car_y = FLOOR_HEIGHTS_MM[4]
        self.assertTrue(state.on_arrival())
        self.assertTrue(state.is_paused())
        paused_height = state.car_y
        for _ in range(100):
            direction, duty = state.motion_command(50)
            state.advance_from_command(direction, duty, dt=0.016)
        self.assertEqual((direction, duty), (0, 0.0))
        self.assertEqual(state.car_y, paused_height)
        state.resume_at = time.monotonic() - 1.0
        direction, duty = state.motion_command(50)
        self.assertEqual(direction, -1)
        self.assertGreater(duty, 0.0)


if __name__ == "__main__":
    # this also allows "python test_elevator_state.py" to be run directly,
    # instead of the python -m unittest command
    unittest.main()

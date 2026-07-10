# elevator_state.py
# This file has all the "logic" for how the elevator simulation behaves -
# stuff like which floor is being targeted, how the car glides between
# floors, and how a sequence of floors gets run one at a time.
#
# On purpose, this file does NOT import guizero (the GUI library) or gpiozero
# (the hardware library). That means all this logic can be tested by itself
# without needing an actual screen or an actual Raspberry Pi, which makes
# testing a lot easier (see test_elevator_state.py).

import time

import config

# these are basically just pixel coordinates for where each floor is drawn on
# screen. floor 1 is near the bottom (big y number) and floor 4 is near the
# top (small y number)
FLOOR_COORDS = {1: 320, 2: 240, 3: 160, 4: 80}

CAR_STEP_PIXELS_PER_TICK_AT_FULL_SPEED = 6.0  # how many pixels the car moves per frame at 100% speed
CAR_MIN_STEP_PIXELS = 0.5  # even at low speed there should still be SOME movement each frame
ARRIVAL_TOLERANCE_PIXELS = 1.0  # close enough to the target counts as "arrived"
SEQUENCE_STOP_PAUSE_SECONDS = 0.65  # how long to wait at each stop before moving to the next one in a sequence


class ElevatorState:
    # This class just keeps track of everything about where the elevator is
    # and what it's trying to do. Think of it like the "save file" for the
    # simulation - all the important variables live here instead of being
    # scattered around as separate global variables like the first draft had.

    def __init__(self):
        self.target_floor = config.START_FLOOR  # the floor currently being targeted
        self.current_floor = config.START_FLOOR  # the floor actually reached so far
        self.car_y = FLOOR_COORDS[config.START_FLOOR]  # pixel position of the car on screen
        self.sequence_queue = []  # floors left to visit if a sequence is running
        self.sequence_mode = False  # True if a sequence is currently running
        self.resume_at = None  # a timestamp for "don't move again until this time" (None = not paused)
        self.hardware_target_started_at = None  # used for stall detection, see note_hardware_target below
        self.stalled = False  # True if the motor appears stuck / not making progress

    def is_paused(self) -> bool:
        # True during a brief pause (like waiting at a floor during a
        # sequence before continuing to the next stop)
        return self.resume_at is not None and time.monotonic() < self.resume_at

    def _clear_fault(self) -> None:
        # resets the stall-detection state, called whenever a fresh command
        # starts (like a new button press) so old faults don't stick around forever
        self.hardware_target_started_at = None
        self.stalled = False

    def set_target(self, floor: int) -> None:
        # called when a floor is manually picked (like pressing a floor
        # button). cancels whatever sequence might have been running, since a
        # manual button press should always take priority!!!
        self.sequence_mode = False
        self.sequence_queue = []
        self.target_floor = floor
        self._clear_fault()

    def start_sequence(self, floors: list) -> None:
        # kicks off a "visit all these floors in order" sequence. the list
        # gets sorted first so the elevator goes in a sensible order (like
        # floor 1 then 3 then 4) instead of whatever order the checkboxes
        # happened to be clicked in
        if not floors:
            return  # nothing was picked, so there's nothing to do
        ordered = sorted(floors)
        self.target_floor = ordered[0]  # go to the first (lowest) floor first
        self.sequence_queue = ordered[1:]  # save the rest for later
        self.sequence_mode = True
        self._clear_fault()

    def cancel(self, floor: int) -> None:
        # used by the emergency stop button - stops any sequence and just
        # treats wherever the car currently is as the new target
        self.sequence_mode = False
        self.sequence_queue = []
        self.target_floor = floor
        self._clear_fault()

    def nearest_floor_to_car(self) -> int:
        # figures out which floor is physically closest to where the car
        # currently is on screen. used by emergency stop to decide what
        # counts as the "current" floor after stopping mid-shaft
        return min(FLOOR_COORDS, key=lambda floor: abs(self.car_y - FLOOR_COORDS[floor]))

    def has_arrived(self) -> bool:
        # checks if the car is close enough to the target floor's position to
        # count as "arrived" (pixel-perfect accuracy isn't needed, within a
        # pixel or so is plenty good)
        return abs(self.car_y - FLOOR_COORDS[self.target_floor]) <= ARRIVAL_TOLERANCE_PIXELS

    def step_car(self, speed_percent: int) -> None:
        # runs once per animation frame and nudges the car's position a
        # little bit closer to the target floor. speed_percent controls how
        # big a step is taken each time (bigger speed = bigger steps = looks
        # like it's moving faster).
        if self.is_paused() or self.has_arrived() or speed_percent <= 0:
            return  # nothing to do if paused, already there, or stopped
        target_y = FLOOR_COORDS[self.target_floor]
        step = max(CAR_MIN_STEP_PIXELS, (speed_percent / 100.0) * CAR_STEP_PIXELS_PER_TICK_AT_FULL_SPEED)
        if self.car_y < target_y:
            # target is below (bigger y = lower on screen), so move down
            self.car_y += min(step, target_y - self.car_y)
        else:
            # target is above, so move up
            self.car_y -= min(step, self.car_y - target_y)

    def on_arrival(self) -> bool:
        # call this once has_arrived() says True. it updates current_floor
        # and, if a sequence is running, grabs the next floor off the queue
        # and starts a brief pause before continuing (so the elevator doesn't
        # just zoom through every stop instantly, which would look odd).
        #
        # returns True only the FIRST time a NEW floor is detected as reached,
        # so the caller knows something changed and the display should update.
        if self.current_floor == self.target_floor:
            return False  # already known to be here, nothing new happened
        self.current_floor = self.target_floor
        if self.sequence_mode:
            if self.sequence_queue:
                # more stops left, so grab the next one and pause briefly first
                self.target_floor = self.sequence_queue.pop(0)
                self.resume_at = time.monotonic() + SEQUENCE_STOP_PAUSE_SECONDS
            else:
                # that was the last stop, sequence is done
                self.sequence_mode = False
        return True

    def note_hardware_target(self, hardware_current_floor: int) -> bool:
        # this is the safety check for the REAL motor (not the simulated
        # one). every frame, while real hardware is hooked up, it checks: has
        # the actual sensor feedback confirmed the target floor was reached
        # yet? if not, a stopwatch starts (or keeps running). if too much time
        # passes (see MOTOR_STALL_TIMEOUT_SECONDS in config.py) without ever
        # reaching the target, something is probably wrong (a broken sensor,
        # the motor not actually moving, a wire that fell off, etc), so it
        # gets flagged as "stalled" so the caller can cut power instead of
        # letting the motor run forever, which could be dangerous or break something.
        #
        # returns True only the exact moment a NEW stall is detected (so the
        # caller can react right then), not on every frame after that.
        if hardware_current_floor == self.target_floor:
            # target reached - reset everything, no stall
            self._clear_fault()
            return False
        if self.hardware_target_started_at is None:
            # first frame trying to reach this target, start the stopwatch
            self.hardware_target_started_at = time.monotonic()
            return False
        if not self.stalled and (
            time.monotonic() - self.hardware_target_started_at > config.MOTOR_STALL_TIMEOUT_SECONDS
        ):
            # too much time has passed with no arrival - likely a real problem
            self.stalled = True
            return True
        return False

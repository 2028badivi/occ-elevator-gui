# elevator_state.py
# This file has all the "logic" for how the elevator simulation behaves -
# stuff like which floor is being targeted, how the car glides between
# floors, and how a sequence of floors gets run one at a time.
#
# On purpose, this file does NOT import guizero (the GUI library) or gpiozero
# (the hardware library). That means all this logic can be tested by itself
# without needing an actual screen or an actual Raspberry Pi, which makes
# testing a lot easier (see test_elevator_state.py).

import math
import time

import config

# real measured heights (in millimeters, from the SolidWorks model of the
# actual rig), NOT arbitrary pixel values - floor 1 is the ground reference
# (0mm) and each floor above it is 254mm higher, matching the real shaft's
# equal floor-to-floor spacing. this lets the simulated car's position stand
# in as a trustworthy proxy for the real car's position (e.g. for testing
# without the IR sensors wired up), since it's now based on the real rig's
# actual dimensions instead of made-up numbers picked to look OK on screen.
# gui.py is responsible for mapping these real-world mm values onto actual
# screen pixels for drawing - this file only ever deals in mm.
FLOOR_HEIGHTS_MM = {1: 0, 2: 254, 3: 508, 4: 762}

# the car's real maximum linear speed, derived from the actual drive
# hardware: the pulley moves (pi x diameter) mm of cable per revolution, and
# the shaft tops out at MAX_PULLEY_RPM revolutions per minute. with the real
# 74mm pulley and the 27 RPM cap that comes out to ~104.6 mm/s. this is the
# "maximum derivative of height" - step_car() can never move the car faster
# than this no matter what the speed slider says, so a simulated trip takes
# the same wall-clock time the real car would.
PULLEY_CIRCUMFERENCE_MM = math.pi * config.PULLEY_DIAMETER_MM
MAX_CAR_SPEED_MM_PER_S = (config.MAX_PULLEY_RPM / 60.0) * PULLEY_CIRCUMFERENCE_MM

ARRIVAL_TOLERANCE_MM = 3.0  # close enough to the target counts as "arrived"
SEQUENCE_STOP_PAUSE_SECONDS = 0.65  # how long to wait at each stop before moving to the next one in a sequence

# instead of running at one constant speed and stopping abruptly, the car
# ramps up smoothly over the first ACCEL_DISTANCE_MM of a move, cruises at
# full commanded speed if the move is long enough, then ramps back down over
# the last DECEL_DISTANCE_MM as it nears the target. for a short hop (like
# adjacent floors) where the two ramps overlap, it naturally forms a smaller
# triangular speed profile instead of ever reaching full cruise speed.
# (these two are tuning values - adjust to taste against the real rig)
ACCEL_DISTANCE_MM = 80.0
DECEL_DISTANCE_MM = 80.0
MIN_SPEED_FRACTION = 0.15  # never ramp all the way down to a dead stop mid-move


class ElevatorState:
    # This class just keeps track of everything about where the elevator is
    # and what it's trying to do. Think of it like the "save file" for the
    # simulation - all the important variables live here instead of being
    # scattered around as separate global variables like the first draft had.

    def __init__(self):
        self.target_floor = config.START_FLOOR  # the floor currently being targeted
        self.current_floor = config.START_FLOOR  # the floor actually reached so far
        self.car_y = FLOOR_HEIGHTS_MM[config.START_FLOOR]  # car's height in mm, measured up from floor 1
        self.sequence_queue = []  # floors left to visit if a sequence is running
        self.sequence_mode = False  # True if a sequence is currently running
        self.resume_at = None  # a timestamp for "don't move again until this time" (None = not paused)
        self.hardware_target_started_at = None  # used for stall detection, see note_hardware_target below
        self.stalled = False  # True if the motor appears stuck / not making progress
        self._leg_start_y = self.car_y  # where the current move began, for the accel/decel ramp

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
        self._leg_start_y = self.car_y  # a fresh move starts here, for the accel ramp
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
        self._leg_start_y = self.car_y
        self._clear_fault()

    def calibrate_to_floor(self, floor: int) -> None:
        # tells the state "the car is actually sitting at this floor right
        # now." needed because there's no position sensor on the rig - every
        # time the app launches it otherwise assumes the car starts at
        # config.START_FLOOR, even if the real car is sitting somewhere else
        # (e.g. floor 4). sets car_y, current_floor, AND target_floor all to
        # this floor, so nothing tries to move until a new button is pressed.
        self.sequence_mode = False
        self.sequence_queue = []
        self.car_y = FLOOR_HEIGHTS_MM[floor]
        self.current_floor = floor
        self.target_floor = floor
        self._leg_start_y = self.car_y
        self._clear_fault()

    def cancel(self, floor: int) -> None:
        # used by the emergency stop button - stops any sequence and treats
        # the nearest floor as the new target. car_y gets snapped to that
        # floor's exact height (not just left wherever it happened to be)
        # so has_arrived() is immediately true and direction_to_target()
        # returns 0 - otherwise, if the car wasn't within ARRIVAL_TOLERANCE_MM
        # of that floor already, the very next glide_step tick would see
        # "not arrived yet" and immediately re-command the motor, undoing
        # the stop (this is what was causing the jerking after pressing it)
        self.sequence_mode = False
        self.sequence_queue = []
        self.target_floor = floor
        self.car_y = FLOOR_HEIGHTS_MM[floor]
        self._leg_start_y = self.car_y
        self._clear_fault()

    def nearest_floor_to_car(self) -> int:
        # figures out which floor is physically closest to where the car
        # actually is right now. used by emergency stop to decide what counts
        # as the "current" floor after stopping mid-shaft
        return min(FLOOR_HEIGHTS_MM, key=lambda floor: abs(self.car_y - FLOOR_HEIGHTS_MM[floor]))

    def direction_to_target(self) -> int:
        # which way the real motor should spin to reach the target: +1 (up),
        # -1 (down), or 0 if already there. this is the ONLY thing hardware.py
        # is told about position - there's no sensor on the rig to check this
        # against, so the simulated car_y here is the sole source of truth.
        if self.has_arrived():
            return 0
        target_y = FLOOR_HEIGHTS_MM[self.target_floor]
        return 1 if target_y > self.car_y else -1

    def has_arrived(self) -> bool:
        # checks if the car is close enough to the target floor's position to
        # count as "arrived" (millimeter-perfect accuracy isn't needed, being
        # within a few mm is plenty good)
        return abs(self.car_y - FLOOR_HEIGHTS_MM[self.target_floor]) <= ARRIVAL_TOLERANCE_MM

    def effective_speed_percent(self, speed_percent: int) -> int:
        # applies the accel/decel ramp on top of whatever speed was
        # commanded (e.g. from the speed slider), based on how far the car
        # has traveled since the current move started and how far it still
        # has left to go. exposed as its own method (not just folded into
        # step_car) so the real motor's commanded speed can be ramped the
        # same way the simulated car is - see hardware.move_toward() callers
        # in gui.py.
        if speed_percent <= 0:
            return 0
        target_y = FLOOR_HEIGHTS_MM[self.target_floor]
        distance_traveled = abs(self.car_y - self._leg_start_y)
        distance_remaining = abs(target_y - self.car_y)
        accel_fraction = min(1.0, distance_traveled / ACCEL_DISTANCE_MM)
        decel_fraction = min(1.0, distance_remaining / DECEL_DISTANCE_MM)
        ramp_fraction = max(MIN_SPEED_FRACTION, min(accel_fraction, decel_fraction))
        return round(speed_percent * ramp_fraction)

    def step_car(self, speed_percent: int, dt: float = 1.0 / 60.0) -> None:
        # advances the car by however far it could really travel in dt
        # seconds: (speed fraction) x (real max speed) x (elapsed time).
        # dt is the actual wall-clock time since the previous step, passed in
        # by the caller (gui.py measures it each tick) - that way the car
        # moves at true real-world speed regardless of whether the GUI is
        # ticking at a smooth 60fps or chugging, and the physical speed cap
        # (MAX_CAR_SPEED_MM_PER_S) is genuinely a mm-per-SECOND limit rather
        # than a per-frame amount that would drift with frame rate.
        if self.is_paused() or self.has_arrived() or speed_percent <= 0 or dt <= 0:
            return  # nothing to do if paused, already there, or stopped
        target_y = FLOOR_HEIGHTS_MM[self.target_floor]
        ramped_speed_percent = self.effective_speed_percent(speed_percent)
        step = (ramped_speed_percent / 100.0) * MAX_CAR_SPEED_MM_PER_S * dt
        if self.car_y < target_y:
            # target is higher up (bigger mm value = physically higher), so move up
            self.car_y += min(step, target_y - self.car_y)
        else:
            # target is lower, so move down
            self.car_y -= min(step, self.car_y - target_y)

    def trip_progress(self):
        # how far through the current move the car is, as a 0.0-1.0 fraction
        # (None when there's no move in progress) - used by the GUI to show a
        # live "Trip 63%" readout
        total = abs(FLOOR_HEIGHTS_MM[self.target_floor] - self._leg_start_y)
        if total <= 0 or self.has_arrived():
            return None
        return min(1.0, abs(self.car_y - self._leg_start_y) / total)

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
                self._leg_start_y = self.car_y  # next stop is a fresh move, ramp from here
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

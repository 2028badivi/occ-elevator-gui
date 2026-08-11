"""Fit the open-loop motor model from stopwatch measurements.

Example, timing a 648mm center-shaft section at three fixed duties:

    python motion_calibration.py --distance-mm 648 \
        --up 30:34.2 --up 50:19.8 --up 75:12.5 \
        --down 30:30.1 --down 50:17.4 --down 75:11.0

Each sample is DUTY_PERCENT:SECONDS. The output maps directly to config.py.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import math
from typing import Iterable

from elevator_state import MAX_CAR_SPEED_MM_PER_S


@dataclass(frozen=True)
class CalibrationResult:
    deadzone_percent: float
    full_speed_scale: float
    full_speed_mm_s: float
    rmse_mm_s: float


def fit_direction(
    samples: Iterable[tuple[float, float]],
    distance_mm: float,
    nominal_full_speed_mm_s: float = MAX_CAR_SPEED_MM_PER_S,
) -> CalibrationResult:
    """Fits v = slope*duty + intercept and converts it to app parameters."""
    if distance_mm <= 0:
        raise ValueError("distance_mm must be positive")
    if nominal_full_speed_mm_s <= 0:
        raise ValueError("nominal_full_speed_mm_s must be positive")
    measurements = [(float(duty), float(seconds)) for duty, seconds in samples]
    if len(measurements) < 2:
        raise ValueError("at least two stopwatch samples are required per direction")
    if any(not 0 < duty <= 100 or seconds <= 0 for duty, seconds in measurements):
        raise ValueError("duties must be in (0, 100] and times must be positive")
    points = [(duty, distance_mm / seconds) for duty, seconds in measurements]

    mean_x = sum(duty for duty, _ in points) / len(points)
    mean_y = sum(speed for _, speed in points) / len(points)
    variance_x = sum((duty - mean_x) ** 2 for duty, _ in points)
    if variance_x == 0:
        raise ValueError("use at least two different duty percentages")
    slope = sum((duty - mean_x) * (speed - mean_y) for duty, speed in points) / variance_x
    if slope <= 0:
        raise ValueError("measured speed must increase with PWM duty")
    intercept = mean_y - slope * mean_x

    fitted_deadzone = -intercept / slope
    deadzone = max(0.0, min(99.0, fitted_deadzone))
    full_speed = slope * 100.0 + intercept
    if full_speed <= 0 or not math.isfinite(full_speed):
        raise ValueError("measurements produced an invalid full-speed estimate")
    residuals = [speed - (slope * duty + intercept) for duty, speed in points]
    rmse = math.sqrt(sum(value * value for value in residuals) / len(residuals))
    return CalibrationResult(
        deadzone_percent=deadzone,
        full_speed_scale=full_speed / nominal_full_speed_mm_s,
        full_speed_mm_s=full_speed,
        rmse_mm_s=rmse,
    )


def _parse_sample(value: str) -> tuple[float, float]:
    try:
        duty, seconds = value.split(":", 1)
        return float(duty), float(seconds)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected DUTY_PERCENT:SECONDS") from exc


def _print_result(name: str, result: CalibrationResult) -> None:
    prefix = name.upper()
    print(f"{prefix}_PWM_DEADZONE_PERCENT = {result.deadzone_percent:.3f}")
    print(f"{prefix}_SPEED_SCALE = {result.full_speed_scale:.6f}")
    print(
        f"# fitted {name} full speed: {result.full_speed_mm_s:.2f} mm/s; "
        f"RMSE: {result.rmse_mm_s:.2f} mm/s"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distance-mm", type=float, required=True)
    parser.add_argument("--up", action="append", type=_parse_sample, default=[])
    parser.add_argument("--down", action="append", type=_parse_sample, default=[])
    args = parser.parse_args()
    if not args.up and not args.down:
        parser.error("provide at least one direction using --up or --down")
    if args.up:
        _print_result("up", fit_direction(args.up, args.distance_mm))
    if args.down:
        _print_result("down", fit_direction(args.down, args.distance_mm))


if __name__ == "__main__":
    main()

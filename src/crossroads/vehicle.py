from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class VehicleState(Enum):
    APPROACHING = auto()
    CROSSING = auto()
    EXITED = auto()


@dataclass
class Vehicle:
    arm: str
    crossing_start: float
    crossing_end: float
    target_velocity: float
    max_velocity: float
    acceleration: float
    deceleration: float
    position: float = 0.0
    velocity: float = 0.0
    state: VehicleState = field(default=VehicleState.APPROACHING, init=False)

    def __post_init__(self) -> None:
        if self.crossing_start < 0 or self.crossing_end < 0:
            raise ValueError("crossing bounds must be non-negative")
        if self.crossing_start >= self.crossing_end:
            raise ValueError("crossing_start must be smaller than crossing_end")
        if self.max_velocity < 0 or self.acceleration <= 0 or self.deceleration <= 0:
            raise ValueError("velocity and rates must be positive")
        if self.target_velocity < 0:
            raise ValueError("target_velocity must be non-negative")
        self.target_velocity = min(self.target_velocity, self.max_velocity)
        self._update_state()

    def advance_tick(self) -> None:
        if self.state == VehicleState.EXITED:
            return

        if self.velocity < self.target_velocity:
            self.velocity = min(self.velocity + self.acceleration, self.target_velocity)
        elif self.velocity > self.target_velocity:
            self.velocity = max(self.velocity - self.deceleration, self.target_velocity)

        self.velocity = min(self.velocity, self.max_velocity)
        self.position = min(self.position + self.velocity, self.crossing_end)
        self._update_state()

    def _update_state(self) -> None:
        if self.position >= self.crossing_end:
            self.state = VehicleState.EXITED
        elif self.position >= self.crossing_start:
            self.state = VehicleState.CROSSING
        else:
            self.state = VehicleState.APPROACHING


def crossing_bounds_for_arm(
    *,
    arm: str,
    window_width: int,
    window_height: int,
    road_width: int,
) -> tuple[float, float]:
    cx = window_width // 2
    cy = window_height // 2
    half_road = road_width // 2

    if arm == "N":
        return (float(cy - half_road), float(cy + half_road))
    if arm == "S":
        return (
            float((window_height - 1) - (cy + half_road)),
            float((window_height - 1) - (cy - half_road)),
        )
    if arm == "E":
        return (
            float((window_width - 1) - (cx + half_road)),
            float((window_width - 1) - (cx - half_road)),
        )
    if arm == "W":
        return (float(cx - half_road), float(cx + half_road))
    raise ValueError(f"Unknown arm: {arm!r}")


def world_position_for_distance(
    *,
    arm: str,
    distance: float,
    window_width: int,
    window_height: int,
) -> tuple[float, float]:
    cx = window_width // 2
    cy = window_height // 2
    clamped = max(0.0, distance)

    if arm == "N":
        return (float(cx), min(clamped, float(window_height - 1)))
    if arm == "S":
        return (float(cx), max(0.0, float(window_height - 1) - clamped))
    if arm == "E":
        return (max(0.0, float(window_width - 1) - clamped), float(cy))
    if arm == "W":
        return (min(clamped, float(window_width - 1)), float(cy))
    raise ValueError(f"Unknown arm: {arm!r}")

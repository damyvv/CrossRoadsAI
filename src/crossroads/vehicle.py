from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from math import sqrt


class VehicleState(Enum):
    APPROACHING = auto()
    STOPPED = auto()
    CROSSING = auto()
    EXITED = auto()
    DISCARD = auto()


@dataclass(frozen=True)
class VehicleThresholds:
    crossing: float
    exited: float
    discard: float


@dataclass
class Vehicle:
    arm: str
    crossing_distance: float
    exit_distance: float
    discard_distance: float
    target_velocity: float
    max_velocity: float
    acceleration: float
    deceleration: float
    position: float = 0.0
    velocity: float = 0.0
    state: VehicleState = field(default=VehicleState.APPROACHING, init=False)
    wait_ticks: int = field(default=0, init=False)
    _cruise_velocity: float = field(default=0.0, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.crossing_distance < 0 or self.exit_distance < 0 or self.discard_distance < 0:
            raise ValueError("distance thresholds must be non-negative")
        if not (self.crossing_distance < self.exit_distance < self.discard_distance):
            raise ValueError("distance thresholds must satisfy crossing < exited < discard")
        if self.max_velocity < 0 or self.acceleration <= 0 or self.deceleration <= 0:
            raise ValueError("velocity and rates must be positive")
        if self.target_velocity < 0:
            raise ValueError("target_velocity must be non-negative")
        self.target_velocity = min(self.target_velocity, self.max_velocity)
        self._cruise_velocity = self.target_velocity
        self._update_state(can_enter_intersection=True, blocked_by_leader=False)

    def advance_tick(
        self,
        *,
        can_enter_intersection: bool = True,
        max_position: float | None = None,
    ) -> None:
        if self.state == VehicleState.DISCARD:
            return

        blocked_by_signal = not can_enter_intersection and self.position <= self.crossing_distance
        self.target_velocity = self._cruise_velocity
        if blocked_by_signal:
            distance_to_stop_line = max(self.crossing_distance - self.position, 0.0)
            max_safe_velocity = sqrt(2 * self.deceleration * distance_to_stop_line)
            self.target_velocity = min(self.target_velocity, max_safe_velocity)
        if max_position is not None:
            distance_to_leader = max(max_position - self.position, 0.0)
            max_safe_velocity = sqrt(2 * self.deceleration * distance_to_leader)
            self.target_velocity = min(self.target_velocity, max_safe_velocity)

        if self.velocity < self.target_velocity:
            self.velocity = min(self.velocity + self.acceleration, self.target_velocity)
        elif self.velocity > self.target_velocity:
            self.velocity = max(self.velocity - self.deceleration, self.target_velocity)

        self.velocity = min(self.velocity, self.max_velocity)
        upper_bound = self.discard_distance
        if blocked_by_signal:
            upper_bound = min(upper_bound, self.crossing_distance)
        if max_position is not None:
            upper_bound = min(upper_bound, max_position)
        if upper_bound < self.position:
            upper_bound = self.position

        self.position = min(self.position + self.velocity, upper_bound)
        blocked_by_leader = max_position is not None and self.position >= max_position
        self._update_state(
            can_enter_intersection=can_enter_intersection,
            blocked_by_leader=blocked_by_leader,
        )
        if self.state == VehicleState.STOPPED:
            self.wait_ticks += 1

    def _update_state(self, *, can_enter_intersection: bool, blocked_by_leader: bool) -> None:
        if self.position >= self.discard_distance:
            self.state = VehicleState.DISCARD
        elif self.position >= self.exit_distance:
            self.state = VehicleState.EXITED
        elif self.velocity == 0 and (
            (not can_enter_intersection and self.position <= self.crossing_distance)
            or (blocked_by_leader and self.position < self.crossing_distance)
        ):
            self.state = VehicleState.STOPPED
        elif self.position >= self.crossing_distance:
            self.state = VehicleState.CROSSING
        else:
            self.state = VehicleState.APPROACHING


def state_thresholds_for_arm(
    *,
    arm: str,
    window_width: int,
    window_height: int,
    stop_line_distance: int,
    vehicle_length: int,
) -> VehicleThresholds:
    if stop_line_distance < 0:
        raise ValueError("stop_line_distance must be non-negative")
    if vehicle_length <= 0:
        raise ValueError("vehicle_length must be positive")

    cx = window_width // 2
    cy = window_height // 2
    discard_ns = float(window_height) + vehicle_length / 2
    discard_ew = float(window_width) + vehicle_length / 2

    if arm == "N":
        return VehicleThresholds(
            crossing=float(cy - stop_line_distance),
            exited=float(cy + stop_line_distance),
            discard=discard_ns,
        )
    if arm == "S":
        return VehicleThresholds(
            crossing=float((window_height - 1) - (cy + stop_line_distance)),
            exited=float((window_height - 1) - (cy - stop_line_distance)),
            discard=discard_ns,
        )
    if arm == "E":
        return VehicleThresholds(
            crossing=float((window_width - 1) - (cx + stop_line_distance)),
            exited=float((window_width - 1) - (cx - stop_line_distance)),
            discard=discard_ew,
        )
    if arm == "W":
        return VehicleThresholds(
            crossing=float(cx - stop_line_distance),
            exited=float(cx + stop_line_distance),
            discard=discard_ew,
        )
    raise ValueError(f"Unknown arm: {arm!r}")


def lane_center_world_position(
    *,
    arm: str,
    distance: float,
    window_width: int,
    window_height: int,
    road_width: int,
) -> tuple[float, float]:
    cx = window_width // 2
    cy = window_height // 2
    lane_offset = road_width / 4

    if arm == "N":
        return (float(cx) - lane_offset, distance)
    if arm == "S":
        return (float(cx) + lane_offset, float(window_height - 1) - distance)
    if arm == "E":
        return (float(window_width - 1) - distance, float(cy) - lane_offset)
    if arm == "W":
        return (distance, float(cy) + lane_offset)
    raise ValueError(f"Unknown arm: {arm!r}")


def spawn_distance_for_length(vehicle_length: int) -> float:
    if vehicle_length <= 0:
        raise ValueError("vehicle_length must be positive")
    return -(vehicle_length / 2) - 1.0

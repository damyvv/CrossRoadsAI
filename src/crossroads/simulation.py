from __future__ import annotations

from dataclasses import dataclass, field
from math import atan2, hypot, isfinite
from random import Random
from typing import Mapping, Sequence

from crossroads.lane_paths import LanePath
from crossroads.metrics import MetricsTracker
from crossroads.traffic_generator import TrafficGenerator
from crossroads.traffic_light import LightState, TrafficLightController
from crossroads.vehicle import Vehicle, VehicleState, spawn_distance_for_length, state_thresholds_for_arm


@dataclass(frozen=True)
class VehicleFlowConfig:
    top_speed: float
    acceleration: float
    deceleration: float
    length: int
    queue_gap: int
    stop_distance_before_line: float


@dataclass(frozen=True)
class TrafficSpawnConfig:
    lambda_per_second: float
    ticks_per_second: int
    seed: int | None
    lambda_per_second_by_arm: Mapping[str, float] | None = None
    inbound_lanes_by_arm: Mapping[str, Sequence["InboundLaneSpawnConfig"]] | None = None


@dataclass(frozen=True)
class InboundLaneSpawnConfig:
    movements: tuple[str, ...]
    movement_probabilities: Mapping[str, float] | None = None


@dataclass(frozen=True)
class VehicleSnapshot:
    arm: str
    position: float
    state: VehicleState
    wait_ticks: int
    lane_index: int = 0
    committed_movement: str = "straight"
    world_position: tuple[float, float] | None = None
    world_heading_radians: float | None = None


@dataclass(frozen=True)
class SimulationState:
    light_states: dict[str, LightState]
    vehicles: tuple[VehicleSnapshot, ...]
    lane_light_states: dict[tuple[str, int], LightState] = field(default_factory=dict)
    lane_counts_by_arm: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class _LanePathRuntime:
    lane_path: LanePath
    path_length: float
    target_post_exit_distance: float
    cumulative_segment_lengths: tuple[float, ...]


_INBOUND_DIRECTION_BY_ARM = {
    "N": (0.0, 1.0),
    "S": (0.0, -1.0),
    "E": (-1.0, 0.0),
    "W": (1.0, 0.0),
}
_OUTBOUND_DIRECTION_BY_ARM = {
    "N": (0.0, -1.0),
    "S": (0.0, 1.0),
    "E": (1.0, 0.0),
    "W": (-1.0, 0.0),
}


def _path_length(*, points: tuple[tuple[float, float], ...]) -> float:
    return sum(hypot(end[0] - start[0], end[1] - start[1]) for start, end in zip(points, points[1:]))


def _cumulative_segment_lengths(
    *,
    points: tuple[tuple[float, float], ...],
) -> tuple[float, ...]:
    cumulative: list[float] = []
    total = 0.0
    for start, end in zip(points, points[1:]):
        total += hypot(end[0] - start[0], end[1] - start[1])
        cumulative.append(total)
    return tuple(cumulative)


def _polyline_pose_at_distance(
    *,
    lane_path_runtime: _LanePathRuntime,
    distance: float,
) -> tuple[tuple[float, float], float]:
    points = lane_path_runtime.lane_path.points
    if len(points) < 2:
        raise ValueError("lane path must contain at least two points")
    cumulative_segment_lengths = lane_path_runtime.cumulative_segment_lengths
    total_length = lane_path_runtime.path_length
    if total_length <= 0:
        raise ValueError("lane path must have positive length")

    clamped_distance = min(max(distance, 0.0), total_length)
    if clamped_distance == 0.0:
        first_start, first_end = points[0], points[1]
        return points[0], atan2(first_end[1] - first_start[1], first_end[0] - first_start[0])
    if clamped_distance == total_length:
        last_start, last_end = points[-2], points[-1]
        return points[-1], atan2(last_end[1] - last_start[1], last_end[0] - last_start[0])

    target_length = clamped_distance
    for index, cumulative_length in enumerate(cumulative_segment_lengths):
        if cumulative_length >= target_length:
            previous_cumulative = (
                0.0 if index == 0 else cumulative_segment_lengths[index - 1]
            )
            length = cumulative_length - previous_cumulative
            start = points[index]
            end = points[index + 1]
            if length == 0:
                heading = atan2(end[1] - start[1], end[0] - start[0])
                return end, heading
            local_fraction = (target_length - previous_cumulative) / length
            heading = atan2(end[1] - start[1], end[0] - start[0])
            return (
                (
                    start[0] + ((end[0] - start[0]) * local_fraction),
                    start[1] + ((end[1] - start[1]) * local_fraction),
                ),
                heading,
            )
    last_start, last_end = points[-2], points[-1]
    return points[-1], atan2(last_end[1] - last_start[1], last_end[0] - last_start[0])


def _world_pose_on_lane_path(
    *,
    vehicle: Vehicle,
    lane_path_runtime: _LanePathRuntime,
) -> tuple[tuple[float, float], float]:
    lane_path = lane_path_runtime.lane_path
    path_start = lane_path.points[0]
    path_end = lane_path.points[-1]
    if vehicle.position <= vehicle.crossing_distance:
        inbound_dx, inbound_dy = _INBOUND_DIRECTION_BY_ARM[vehicle.arm]
        offset = vehicle.position - vehicle.crossing_distance
        return (
            (path_start[0] + (inbound_dx * offset), path_start[1] + (inbound_dy * offset)),
            atan2(inbound_dy, inbound_dx),
        )

    if vehicle.position <= vehicle.exit_distance:
        return _polyline_pose_at_distance(
            lane_path_runtime=lane_path_runtime,
            distance=vehicle.position - vehicle.crossing_distance,
        )

    outbound_dx, outbound_dy = _OUTBOUND_DIRECTION_BY_ARM[lane_path.target_arm]
    overflow = vehicle.position - vehicle.exit_distance
    return (
        (path_end[0] + (outbound_dx * overflow), path_end[1] + (outbound_dy * overflow)),
        atan2(outbound_dy, outbound_dx),
    )


def _lane_light_states_by_inbound_lane(
    *,
    arm_names: tuple[str, ...],
    lanes_by_arm: Mapping[str, tuple["_LaneSpawnRuntimeConfig", ...]],
    controller: TrafficLightController,
) -> dict[tuple[str, int], LightState]:
    return {
        (arm, lane_index): controller.state(arm)
        for arm in arm_names
        for lane_index in range(len(lanes_by_arm[arm]))
    }


def _entry_occupied_by_arm(
    *,
    arm_names: tuple[str, ...],
    vehicles: list[Vehicle],
    entry_distance: float,
    clearance_distance: float,
) -> dict[str, bool]:
    if clearance_distance < 0:
        raise ValueError("clearance_distance must be non-negative")
    blocked_distance = entry_distance + clearance_distance
    return {
        arm: any(vehicle.arm == arm and vehicle.position <= blocked_distance for vehicle in vehicles)
        for arm in arm_names
    }


def _entry_occupied_by_lane(
    *,
    lanes_by_arm: Mapping[str, tuple["_LaneSpawnRuntimeConfig", ...]],
    vehicles: list[Vehicle],
    entry_distance: float,
    clearance_distance: float,
) -> dict[tuple[str, int], bool]:
    if clearance_distance < 0:
        raise ValueError("clearance_distance must be non-negative")
    blocked_distance = entry_distance + clearance_distance
    return {
        (arm, lane_index): any(
            vehicle.arm == arm
            and vehicle.lane_index == lane_index
            and vehicle.position <= blocked_distance
            for vehicle in vehicles
        )
        for arm, lanes in lanes_by_arm.items()
        for lane_index in range(len(lanes))
    }


def _advance_vehicles(
    *,
    vehicles: list[Vehicle],
    arm_names: tuple[str, ...],
    controller: TrafficLightController,
    lane_light_states: Mapping[tuple[str, int], LightState] | None = None,
    min_following_distance: float,
    stop_margin_to_line: float,
    crossing_distance_by_arm: dict[str, float],
) -> None:
    if stop_margin_to_line < 0:
        raise ValueError("stop_margin_to_line must be non-negative")
    for arm in arm_names:
        arm_lane_indices = sorted({vehicle.lane_index for vehicle in vehicles if vehicle.arm == arm})
        if not arm_lane_indices:
            continue
        for lane_index in arm_lane_indices:
            lane_state = (
                controller.state(arm)
                if lane_light_states is None
                else lane_light_states.get((arm, lane_index), LightState.RED)
            )
            can_enter_intersection = lane_state == LightState.GREEN
            arm_lane_vehicles = sorted(
                (
                    vehicle
                    for vehicle in vehicles
                    if vehicle.arm == arm and vehicle.lane_index == lane_index
                ),
                key=lambda vehicle: vehicle.position,
                reverse=True,
            )
            for index, vehicle in enumerate(arm_lane_vehicles):
                max_position = None
                if index > 0:
                    max_position = arm_lane_vehicles[index - 1].position - min_following_distance
                vehicle.advance_tick(
                    can_enter_intersection=can_enter_intersection,
                    max_position=max_position,
                    signal_stop_position=crossing_distance_by_arm[arm] - stop_margin_to_line,
                )


@dataclass(frozen=True)
class _LaneSpawnRuntimeConfig:
    movements: tuple[str, ...]
    cumulative_probabilities: tuple[float, ...] | None


def _default_inbound_lanes_by_arm(
    *, arm_names: Sequence[str]
) -> dict[str, tuple[InboundLaneSpawnConfig, ...]]:
    return {
        arm: (InboundLaneSpawnConfig(movements=("straight",)),)
        for arm in arm_names
    }


def _validate_and_normalize_inbound_lanes_by_arm(
    *,
    arm_names: tuple[str, ...],
    inbound_lanes_by_arm: Mapping[str, Sequence[InboundLaneSpawnConfig]] | None,
) -> dict[str, tuple[_LaneSpawnRuntimeConfig, ...]]:
    source = (
        _default_inbound_lanes_by_arm(arm_names=arm_names)
        if inbound_lanes_by_arm is None
        else dict(inbound_lanes_by_arm)
    )
    missing_arms = sorted(set(arm_names) - set(source))
    if missing_arms:
        raise ValueError(f"missing inbound lane definitions for arms: {missing_arms!r}")
    unknown_arms = sorted(set(source) - set(arm_names))
    if unknown_arms:
        raise ValueError(f"unknown arm in inbound lane definitions: {unknown_arms!r}")

    normalized: dict[str, tuple[_LaneSpawnRuntimeConfig, ...]] = {}
    for arm in arm_names:
        lane_configs = tuple(source[arm])
        if not lane_configs:
            raise ValueError(f"inbound lane definitions for arm {arm!r} must not be empty")
        parsed_lanes: list[_LaneSpawnRuntimeConfig] = []
        for lane_index, lane_config in enumerate(lane_configs):
            if not isinstance(lane_config, InboundLaneSpawnConfig):
                raise ValueError(
                    f"inbound lane definition for arm {arm!r} at index {lane_index} must be InboundLaneSpawnConfig"
                )
            movements = lane_config.movements
            if not movements:
                raise ValueError(f"inbound lane movements for arm {arm!r} at index {lane_index} must not be empty")
            if len(set(movements)) != len(movements):
                raise ValueError(
                    f"duplicate movements in inbound lane for arm {arm!r} at index {lane_index}"
                )
            for movement in movements:
                if movement not in {"left", "straight", "right"}:
                    raise ValueError(
                        f"invalid movement in inbound lane for arm {arm!r} at index {lane_index}: {movement}"
                    )

            movement_probabilities = lane_config.movement_probabilities
            if len(movements) > 1 and movement_probabilities is None:
                raise ValueError(
                    f"shared lane movements for arm {arm!r} at index {lane_index} require explicit movement_probabilities"
                )

            cumulative_probabilities: tuple[float, ...] | None = None
            if movement_probabilities is not None:
                expected = set(movements)
                actual = set(movement_probabilities)
                if expected != actual:
                    raise ValueError(
                        f"movement_probabilities keys must exactly match movements for arm {arm!r} lane {lane_index}"
                    )
                total = 0.0
                cumulative: list[float] = []
                for movement in movements:
                    probability = movement_probabilities[movement]
                    if isinstance(probability, bool) or not isinstance(probability, (int, float)):
                        raise ValueError(
                            f"movement_probabilities[{movement!r}] must be a non-negative finite number"
                        )
                    parsed_probability = float(probability)
                    if not isfinite(parsed_probability) or parsed_probability < 0.0:
                        raise ValueError(
                            f"movement_probabilities[{movement!r}] must be a non-negative finite number"
                        )
                    total += parsed_probability
                    cumulative.append(total)
                if abs(total - 1.0) > 1e-9:
                    raise ValueError("movement_probabilities must sum to 1.0")
                cumulative_probabilities = tuple(cumulative)

            parsed_lanes.append(
                _LaneSpawnRuntimeConfig(
                    movements=movements,
                    cumulative_probabilities=cumulative_probabilities,
                )
            )
        normalized[arm] = tuple(parsed_lanes)
    return normalized


def _sample_committed_movement(*, lane: _LaneSpawnRuntimeConfig, rng: Random) -> str:
    if len(lane.movements) == 1:
        return lane.movements[0]
    assert lane.cumulative_probabilities is not None
    sample = rng.random()
    for movement, threshold in zip(lane.movements, lane.cumulative_probabilities):
        if sample <= threshold:
            return movement
    return lane.movements[-1]


class IntersectionSimulation:
    def __init__(
        self,
        *,
        arm_names: Sequence[str],
        window_width: int,
        window_height: int,
        stop_line_distance: int | Mapping[str, int],
        vehicle_flow: VehicleFlowConfig,
        spawn: TrafficSpawnConfig,
        controller: TrafficLightController,
        lane_paths_by_lane_movement: Mapping[tuple[str, int, str], LanePath] | None = None,
    ) -> None:
        self._arm_names = tuple(arm_names)
        if not self._arm_names:
            raise ValueError("arm_names must not be empty")
        if controller is None:
            raise ValueError("controller must be provided")

        self._vehicle_flow = vehicle_flow
        self._controller = controller
        self._thresholds_by_arm = {
            arm_name: state_thresholds_for_arm(
                arm=arm_name,
                window_width=window_width,
                window_height=window_height,
                stop_line_distance=(stop_line_distance[arm_name] if isinstance(stop_line_distance, Mapping) else stop_line_distance),
                vehicle_length=vehicle_flow.length,
            )
            for arm_name in self._arm_names
        }
        self._spawn_distance = spawn_distance_for_length(vehicle_flow.length)
        self._traffic_generator = TrafficGenerator(
            arm_names=self._arm_names,
            lambda_per_second=spawn.lambda_per_second,
            lambda_per_second_by_arm=spawn.lambda_per_second_by_arm,
            ticks_per_second=spawn.ticks_per_second,
            seed=spawn.seed,
        )
        self._inbound_lanes_by_arm = _validate_and_normalize_inbound_lanes_by_arm(
            arm_names=self._arm_names,
            inbound_lanes_by_arm=spawn.inbound_lanes_by_arm,
        )
        self._spawn_random = Random(spawn.seed)
        for key, lane_path in (lane_paths_by_lane_movement or {}).items():
            source_arm, _, _ = key
            if source_arm not in self._thresholds_by_arm:
                raise ValueError(f"lane path key has unknown source arm: {source_arm!r}")
            if lane_path.target_arm not in self._thresholds_by_arm:
                raise ValueError(f"lane path has unknown target arm: {lane_path.target_arm!r}")
        self._lane_path_runtime_by_lane_movement = {
            key: _LanePathRuntime(
                lane_path=lane_path,
                path_length=_path_length(points=lane_path.points),
                target_post_exit_distance=(
                    self._thresholds_by_arm[lane_path.target_arm].discard
                    - self._thresholds_by_arm[lane_path.target_arm].crossing
                ),
                cumulative_segment_lengths=_cumulative_segment_lengths(points=lane_path.points),
            )
            for key, lane_path in (lane_paths_by_lane_movement or {}).items()
        }
        for key, runtime in self._lane_path_runtime_by_lane_movement.items():
            if runtime.path_length <= 0:
                raise ValueError(f"lane path {key!r} must have positive path length")
            if runtime.target_post_exit_distance <= 0:
                raise ValueError(
                    f"lane path {key!r} has non-positive target post-exit distance"
                )
        self._vehicles: list[Vehicle] = []
        self._metrics = MetricsTracker()
        self._spawn_new_vehicles()

    def state(self) -> SimulationState:
        lane_light_states = _lane_light_states_by_inbound_lane(
            arm_names=self._arm_names,
            lanes_by_arm=self._inbound_lanes_by_arm,
            controller=self._controller,
        )
        return SimulationState(
            light_states={arm: self._controller.state(arm) for arm in self._arm_names},
            lane_light_states=lane_light_states,
            lane_counts_by_arm={
                arm: len(self._inbound_lanes_by_arm[arm]) for arm in self._arm_names
            },
            vehicles=tuple(self._vehicle_snapshot(vehicle) for vehicle in self._vehicles),
        )

    def _vehicle_snapshot(self, vehicle: Vehicle) -> VehicleSnapshot:
        lane_path_runtime = self._lane_path_runtime_by_lane_movement.get(
            (vehicle.arm, vehicle.lane_index, vehicle.committed_movement)
        )
        if lane_path_runtime is None:
            return VehicleSnapshot(
                arm=vehicle.arm,
                lane_index=vehicle.lane_index,
                committed_movement=vehicle.committed_movement,
                position=vehicle.position,
                state=vehicle.state,
                wait_ticks=vehicle.wait_ticks,
            )

        world_position, world_heading_radians = _world_pose_on_lane_path(
            vehicle=vehicle,
            lane_path_runtime=lane_path_runtime,
        )
        return VehicleSnapshot(
            arm=vehicle.arm,
            lane_index=vehicle.lane_index,
            committed_movement=vehicle.committed_movement,
            position=vehicle.position,
            state=vehicle.state,
            wait_ticks=vehicle.wait_ticks,
            world_position=world_position,
            world_heading_radians=world_heading_radians,
        )

    def average_wait_time(self) -> float:
        """Return the average wait time in ticks for exited vehicles."""
        return self._metrics.average_wait_time()

    def advance_tick(self) -> None:
        lane_light_states = _lane_light_states_by_inbound_lane(
            arm_names=self._arm_names,
            lanes_by_arm=self._inbound_lanes_by_arm,
            controller=self._controller,
        )
        # Track previous states to detect transitions to EXITED
        previous_states = {id(vehicle): vehicle.state for vehicle in self._vehicles}

        _advance_vehicles(
            vehicles=self._vehicles,
            arm_names=self._arm_names,
            controller=self._controller,
            lane_light_states=lane_light_states,
            min_following_distance=float(self._vehicle_flow.length + self._vehicle_flow.queue_gap),
            stop_margin_to_line=(float(self._vehicle_flow.length) / 2)
            + self._vehicle_flow.stop_distance_before_line,
            crossing_distance_by_arm={
                arm: threshold.crossing for arm, threshold in self._thresholds_by_arm.items()
            },
        )

        # Record wait times for vehicles that just exited
        for vehicle in self._vehicles:
            prev_state = previous_states.get(id(vehicle))
            if prev_state != VehicleState.EXITED and vehicle.state == VehicleState.EXITED:
                self._metrics.record_wait_time(vehicle.wait_ticks)

        self._vehicles = [vehicle for vehicle in self._vehicles if vehicle.state != VehicleState.DISCARD]
        self._controller.advance_tick()
        self._spawn_new_vehicles()

    def _spawn_new_vehicles(self) -> None:
        occupied_entries_by_lane = _entry_occupied_by_lane(
            lanes_by_arm=self._inbound_lanes_by_arm,
            vehicles=self._vehicles,
            entry_distance=self._spawn_distance,
            clearance_distance=float(self._vehicle_flow.length),
        )
        occupied_entries_by_arm = {
            arm: all(
                occupied_entries_by_lane[(arm, lane_index)]
                for lane_index in range(len(self._inbound_lanes_by_arm[arm]))
            )
            for arm in self._arm_names
        }
        for spawn_arm in self._traffic_generator.advance_tick(
            entry_occupied_by_arm=occupied_entries_by_arm
        ):
            lane_index = self._spawn_random.randrange(len(self._inbound_lanes_by_arm[spawn_arm]))
            if occupied_entries_by_lane[(spawn_arm, lane_index)]:
                continue
            lane = self._inbound_lanes_by_arm[spawn_arm][lane_index]
            committed_movement = _sample_committed_movement(lane=lane, rng=self._spawn_random)
            thresholds = self._thresholds_by_arm[spawn_arm]
            lane_path_runtime = self._lane_path_runtime_by_lane_movement.get(
                (spawn_arm, lane_index, committed_movement)
            )
            if lane_path_runtime is None:
                exit_distance = thresholds.exited
                discard_distance = thresholds.discard
            else:
                exit_distance = thresholds.crossing + lane_path_runtime.path_length
                discard_distance = exit_distance + lane_path_runtime.target_post_exit_distance
            self._vehicles.append(
                Vehicle(
                    arm=spawn_arm,
                    lane_index=lane_index,
                    committed_movement=committed_movement,
                    crossing_distance=thresholds.crossing,
                    exit_distance=exit_distance,
                    discard_distance=discard_distance,
                    target_velocity=self._vehicle_flow.top_speed,
                    max_velocity=self._vehicle_flow.top_speed,
                    acceleration=self._vehicle_flow.acceleration,
                    deceleration=self._vehicle_flow.deceleration,
                    position=self._spawn_distance,
                )
            )

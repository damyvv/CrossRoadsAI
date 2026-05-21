from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from random import Random
from typing import Mapping, Sequence

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


@dataclass(frozen=True)
class SimulationState:
    light_states: dict[str, LightState]
    vehicles: tuple[VehicleSnapshot, ...]


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
        can_enter_intersection = controller.state(arm) == LightState.GREEN
        for lane_index in arm_lane_indices:
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
        stop_line_distance: int,
        vehicle_flow: VehicleFlowConfig,
        spawn: TrafficSpawnConfig,
        controller: TrafficLightController,
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
                stop_line_distance=stop_line_distance,
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
        self._vehicles: list[Vehicle] = []
        self._metrics = MetricsTracker()
        self._spawn_new_vehicles()

    def state(self) -> SimulationState:
        return SimulationState(
            light_states={arm: self._controller.state(arm) for arm in self._arm_names},
            vehicles=tuple(
                VehicleSnapshot(
                    arm=vehicle.arm,
                    lane_index=vehicle.lane_index,
                    committed_movement=vehicle.committed_movement,
                    position=vehicle.position,
                    state=vehicle.state,
                    wait_ticks=vehicle.wait_ticks,
                )
                for vehicle in self._vehicles
            ),
        )

    def average_wait_time(self) -> float:
        """Return the average wait time in ticks for exited vehicles."""
        return self._metrics.average_wait_time()

    def advance_tick(self) -> None:
        # Track previous states to detect transitions to EXITED
        previous_states = {id(vehicle): vehicle.state for vehicle in self._vehicles}

        _advance_vehicles(
            vehicles=self._vehicles,
            arm_names=self._arm_names,
            controller=self._controller,
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
            self._vehicles.append(
                Vehicle(
                    arm=spawn_arm,
                    lane_index=lane_index,
                    committed_movement=committed_movement,
                    crossing_distance=thresholds.crossing,
                    exit_distance=thresholds.exited,
                    discard_distance=thresholds.discard,
                    target_velocity=self._vehicle_flow.top_speed,
                    max_velocity=self._vehicle_flow.top_speed,
                    acceleration=self._vehicle_flow.acceleration,
                    deceleration=self._vehicle_flow.deceleration,
                    position=self._spawn_distance,
                )
            )

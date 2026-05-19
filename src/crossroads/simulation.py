from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from crossroads.metrics import MetricsTracker
from crossroads.traffic_generator import TrafficGenerator
from crossroads.traffic_light import LightState, TrafficLightController
from crossroads.traffic_phasing import ArmPhase
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


@dataclass(frozen=True)
class VehicleSnapshot:
    arm: str
    position: float
    state: VehicleState
    wait_ticks: int


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
        arm_vehicles = sorted(
            (vehicle for vehicle in vehicles if vehicle.arm == arm),
            key=lambda vehicle: vehicle.position,
            reverse=True,
        )
        can_enter_intersection = controller.state(arm) == LightState.GREEN
        for index, vehicle in enumerate(arm_vehicles):
            max_position = None
            if index > 0:
                max_position = arm_vehicles[index - 1].position - min_following_distance
            vehicle.advance_tick(
                can_enter_intersection=can_enter_intersection,
                max_position=max_position,
                signal_stop_position=crossing_distance_by_arm[arm] - stop_margin_to_line,
            )


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
        phases: Sequence[ArmPhase] | None = None,
        green_ticks: int | None = None,
        yellow_ticks: int | None = None,
        controller: TrafficLightController | None = None,
    ) -> None:
        self._arm_names = tuple(arm_names)
        if not self._arm_names:
            raise ValueError("arm_names must not be empty")

        self._vehicle_flow = vehicle_flow
        
        # Validate that controller and legacy parameters are mutually exclusive
        has_controller = controller is not None
        has_legacy_params = any(x is not None for x in [phases, green_ticks, yellow_ticks])
        
        if has_controller and has_legacy_params:
            raise ValueError(
                "Cannot provide both 'controller' and any of 'phases', 'green_ticks', or 'yellow_ticks'. "
                "Either pass an injected controller, or pass the legacy parameters to construct one."
            )
        
        if controller is not None:
            self._controller = controller
        else:
            if phases is None or green_ticks is None or yellow_ticks is None:
                raise ValueError(
                    "Either controller must be provided, or all of phases, green_ticks, and yellow_ticks must be provided"
                )
            self._controller = TrafficLightController(
                arm_names=list(self._arm_names),
                phases=list(phases),
                green_ticks=green_ticks,
                yellow_ticks=yellow_ticks,
            )
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
            ticks_per_second=spawn.ticks_per_second,
            seed=spawn.seed,
        )
        self._vehicles: list[Vehicle] = []
        self._metrics = MetricsTracker()
        self._spawn_new_vehicles()

    def state(self) -> SimulationState:
        return SimulationState(
            light_states={arm: self._controller.state(arm) for arm in self._arm_names},
            vehicles=tuple(
                VehicleSnapshot(
                    arm=vehicle.arm,
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
        occupied_entries = _entry_occupied_by_arm(
            arm_names=self._arm_names,
            vehicles=self._vehicles,
            entry_distance=self._spawn_distance,
            clearance_distance=float(self._vehicle_flow.length),
        )
        for spawn_arm in self._traffic_generator.advance_tick(entry_occupied_by_arm=occupied_entries):
            thresholds = self._thresholds_by_arm[spawn_arm]
            self._vehicles.append(
                Vehicle(
                    arm=spawn_arm,
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

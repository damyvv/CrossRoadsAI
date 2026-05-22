from math import hypot

from crossroads.config import (
    GREEN_DURATION_TICKS,
    SIMULATION_TICKS_PER_SECOND,
    STOP_LINE_DISTANCE,
    VEHICLE_ACCELERATION,
    VEHICLE_DECELERATION,
    VEHICLE_LENGTH,
    VEHICLE_QUEUE_GAP,
    VEHICLE_STOP_DISTANCE_BEFORE_LINE,
    VEHICLE_TOP_SPEED,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    YELLOW_DURATION_TICKS,
)
from crossroads.intersection import build_intersection_geometry
from crossroads.lane_paths import precompute_lane_paths
from crossroads.simulation import (
    InboundLaneSpawnConfig,
    IntersectionSimulation,
    TrafficSpawnConfig,
    VehicleFlowConfig,
)
from crossroads.traffic_light import LightState, TrafficLightController
from crossroads.traffic_phasing import ArmPhase, default_four_way_phases
from crossroads.vehicle import Vehicle, state_thresholds_for_arm


def _build_simulation(
    *,
    seed: int | None,
    spawn_rate: float,
    spawn_rate_by_arm: dict[str, float] | None = None,
    green_ticks: int = GREEN_DURATION_TICKS,
    yellow_ticks: int = YELLOW_DURATION_TICKS,
) -> IntersectionSimulation:
    controller = TrafficLightController(
        arm_names=["N", "E", "S", "W"],
        phases=default_four_way_phases(),
        green_ticks=green_ticks,
        yellow_ticks=yellow_ticks,
    )
    return IntersectionSimulation(
        arm_names=("N", "E", "S", "W"),
        controller=controller,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        stop_line_distance=STOP_LINE_DISTANCE,
        vehicle_flow=VehicleFlowConfig(
            top_speed=VEHICLE_TOP_SPEED,
            acceleration=VEHICLE_ACCELERATION,
            deceleration=VEHICLE_DECELERATION,
            length=VEHICLE_LENGTH,
            queue_gap=VEHICLE_QUEUE_GAP,
            stop_distance_before_line=VEHICLE_STOP_DISTANCE_BEFORE_LINE,
        ),
        spawn=TrafficSpawnConfig(
            lambda_per_second=spawn_rate,
            lambda_per_second_by_arm=spawn_rate_by_arm,
            ticks_per_second=SIMULATION_TICKS_PER_SECOND,
            seed=seed,
        ),
    )


def _state_signature(simulation: IntersectionSimulation) -> tuple:
    state = simulation.state()
    return (
        tuple((arm, state.light_states[arm]) for arm in ("N", "E", "S", "W")),
        tuple(
            (vehicle.arm, round(vehicle.position, 3), vehicle.state, vehicle.wait_ticks)
            for vehicle in state.vehicles
        ),
    )


def _point_on_polyline_at_fraction(
    points: tuple[tuple[float, float], ...], fraction: float
) -> tuple[float, float]:
    if len(points) == 1:
        return points[0]
    clamped = min(max(fraction, 0.0), 1.0)
    segment_lengths = [
        hypot(end[0] - start[0], end[1] - start[1])
        for start, end in zip(points, points[1:])
    ]
    total_length = sum(segment_lengths)
    if total_length == 0:
        return points[-1]

    target_length = total_length * clamped
    traversed = 0.0
    for index, length in enumerate(segment_lengths):
        if traversed + length >= target_length:
            if length == 0:
                return points[index + 1]
            local = (target_length - traversed) / length
            start = points[index]
            end = points[index + 1]
            return (
                start[0] + ((end[0] - start[0]) * local),
                start[1] + ((end[1] - start[1]) * local),
            )
        traversed += length
    return points[-1]


def test_state_exposes_light_states_and_vehicle_snapshots():
    simulation = _build_simulation(seed=3, spawn_rate=0.0)

    state = simulation.state()

    assert set(state.light_states) == {"N", "E", "S", "W"}
    assert state.light_states["N"] == LightState.GREEN
    assert state.light_states["S"] == LightState.GREEN
    assert state.light_states["E"] == LightState.RED
    assert state.light_states["W"] == LightState.RED
    assert state.vehicles == ()


def test_state_uses_precomputed_turn_path_world_position_during_crossing():
    lane_width = 12
    inbound_lanes = {
        "N": (InboundLaneSpawnConfig(movements=("left",)),),
        "E": (InboundLaneSpawnConfig(movements=("straight",)),),
        "S": (InboundLaneSpawnConfig(movements=("straight",)),),
        "W": (InboundLaneSpawnConfig(movements=("straight",)),),
    }
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=4,
        road_width_by_arm={"N": 48, "E": 48, "S": 48, "W": 48},
        inbound_lane_count_by_arm={arm: 1 for arm in ("N", "E", "S", "W")},
        lane_width=lane_width,
        outbound_lane_count_by_arm={arm: 1 for arm in ("N", "E", "S", "W")},
        stop_line_distance=STOP_LINE_DISTANCE,
    )
    lane_paths = precompute_lane_paths(
        geometry=geometry,
        inbound_lanes_by_arm=inbound_lanes,
        outbound_lane_count_by_arm={arm: 1 for arm in ("N", "E", "S", "W")},
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        lane_width=lane_width,
    )

    controller = TrafficLightController(
        arm_names=["N", "E", "S", "W"],
        phases=default_four_way_phases(),
        green_ticks=GREEN_DURATION_TICKS,
        yellow_ticks=YELLOW_DURATION_TICKS,
    )
    simulation = IntersectionSimulation(
        arm_names=("N", "E", "S", "W"),
        controller=controller,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        stop_line_distance=STOP_LINE_DISTANCE,
        vehicle_flow=VehicleFlowConfig(
            top_speed=VEHICLE_TOP_SPEED,
            acceleration=VEHICLE_ACCELERATION,
            deceleration=VEHICLE_DECELERATION,
            length=VEHICLE_LENGTH,
            queue_gap=VEHICLE_QUEUE_GAP,
            stop_distance_before_line=VEHICLE_STOP_DISTANCE_BEFORE_LINE,
        ),
        spawn=TrafficSpawnConfig(
            lambda_per_second=0.0,
            ticks_per_second=SIMULATION_TICKS_PER_SECOND,
            seed=42,
            inbound_lanes_by_arm=inbound_lanes,
        ),
        lane_paths_by_lane_movement=lane_paths,
    )

    thresholds = state_thresholds_for_arm(
        arm="N",
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        stop_line_distance=STOP_LINE_DISTANCE,
        vehicle_length=VEHICLE_LENGTH,
    )
    progress = 0.5
    simulation._vehicles.append(
        Vehicle(
            arm="N",
            lane_index=0,
            committed_movement="left",
            crossing_distance=thresholds.crossing,
            exit_distance=thresholds.exited,
            discard_distance=thresholds.discard,
            target_velocity=0.0,
            max_velocity=VEHICLE_TOP_SPEED,
            acceleration=VEHICLE_ACCELERATION,
            deceleration=VEHICLE_DECELERATION,
            position=thresholds.crossing + ((thresholds.exited - thresholds.crossing) * progress),
        )
    )

    state = simulation.state()
    expected_world_position = _point_on_polyline_at_fraction(
        lane_paths[("N", 0, "left")].points,
        progress,
    )
    snapshot = state.vehicles[0]
    assert snapshot.world_position is not None
    assert snapshot.world_position == expected_world_position


def test_turn_path_traversal_preserves_lane_queue_ordering():
    lane_width = 12
    inbound_lanes = {
        "N": (InboundLaneSpawnConfig(movements=("left",)),),
        "E": (InboundLaneSpawnConfig(movements=("straight",)),),
        "S": (InboundLaneSpawnConfig(movements=("straight",)),),
        "W": (InboundLaneSpawnConfig(movements=("straight",)),),
    }
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=4,
        road_width_by_arm={"N": 48, "E": 48, "S": 48, "W": 48},
        inbound_lane_count_by_arm={arm: 1 for arm in ("N", "E", "S", "W")},
        lane_width=lane_width,
        outbound_lane_count_by_arm={arm: 1 for arm in ("N", "E", "S", "W")},
        stop_line_distance=STOP_LINE_DISTANCE,
    )
    lane_paths = precompute_lane_paths(
        geometry=geometry,
        inbound_lanes_by_arm=inbound_lanes,
        outbound_lane_count_by_arm={arm: 1 for arm in ("N", "E", "S", "W")},
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        lane_width=lane_width,
    )
    controller = TrafficLightController(
        arm_names=["N", "E", "S", "W"],
        phases=default_four_way_phases(),
        green_ticks=GREEN_DURATION_TICKS,
        yellow_ticks=YELLOW_DURATION_TICKS,
    )
    simulation = IntersectionSimulation(
        arm_names=("N", "E", "S", "W"),
        controller=controller,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        stop_line_distance=STOP_LINE_DISTANCE,
        vehicle_flow=VehicleFlowConfig(
            top_speed=VEHICLE_TOP_SPEED,
            acceleration=VEHICLE_ACCELERATION,
            deceleration=VEHICLE_DECELERATION,
            length=VEHICLE_LENGTH,
            queue_gap=VEHICLE_QUEUE_GAP,
            stop_distance_before_line=VEHICLE_STOP_DISTANCE_BEFORE_LINE,
        ),
        spawn=TrafficSpawnConfig(
            lambda_per_second=0.0,
            ticks_per_second=SIMULATION_TICKS_PER_SECOND,
            seed=7,
            inbound_lanes_by_arm=inbound_lanes,
        ),
        lane_paths_by_lane_movement=lane_paths,
    )
    thresholds = state_thresholds_for_arm(
        arm="N",
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        stop_line_distance=STOP_LINE_DISTANCE,
        vehicle_length=VEHICLE_LENGTH,
    )
    leader = Vehicle(
        arm="N",
        lane_index=0,
        committed_movement="left",
        crossing_distance=thresholds.crossing,
        exit_distance=thresholds.exited,
        discard_distance=thresholds.discard,
        target_velocity=VEHICLE_TOP_SPEED,
        max_velocity=VEHICLE_TOP_SPEED,
        acceleration=VEHICLE_ACCELERATION,
        deceleration=VEHICLE_DECELERATION,
        position=thresholds.crossing - 20.0,
    )
    follower = Vehicle(
        arm="N",
        lane_index=0,
        committed_movement="left",
        crossing_distance=thresholds.crossing,
        exit_distance=thresholds.exited,
        discard_distance=thresholds.discard,
        target_velocity=VEHICLE_TOP_SPEED,
        max_velocity=VEHICLE_TOP_SPEED,
        acceleration=VEHICLE_ACCELERATION,
        deceleration=VEHICLE_DECELERATION,
        position=thresholds.crossing - 60.0,
    )
    simulation._vehicles.extend([leader, follower])

    for _ in range(120):
        simulation.advance_tick()
        state = simulation.state()
        lane_vehicles = [vehicle for vehicle in state.vehicles if vehicle.arm == "N"]
        if len(lane_vehicles) != 2:
            break
        lane_vehicles = sorted(lane_vehicles, key=lambda vehicle: vehicle.position, reverse=True)
        assert lane_vehicles[1].position <= lane_vehicles[0].position - (
            VEHICLE_LENGTH + VEHICLE_QUEUE_GAP
        )
        assert lane_vehicles[0].world_position is not None
        assert lane_vehicles[1].world_position is not None


def test_same_seed_produces_identical_simulation_sequence():
    first = _build_simulation(seed=11, spawn_rate=4.0)
    second = _build_simulation(seed=11, spawn_rate=4.0)

    for _ in range(120):
        assert _state_signature(first) == _state_signature(second)
        first.advance_tick()
        second.advance_tick()


def test_same_seed_produces_identical_simulation_sequence_with_per_arm_spawn_rates():
    spawn_rate_by_arm = {"N": 7.0, "E": 0.5, "S": 3.0, "W": 1.0}
    first = _build_simulation(seed=11, spawn_rate=2.0, spawn_rate_by_arm=spawn_rate_by_arm)
    second = _build_simulation(seed=11, spawn_rate=2.0, spawn_rate_by_arm=spawn_rate_by_arm)

    for _ in range(120):
        assert _state_signature(first) == _state_signature(second)
        first.advance_tick()
        second.advance_tick()


def test_advance_tick_performs_phase_handoff_after_green_and_yellow():
    simulation = _build_simulation(seed=3, spawn_rate=0.0, green_ticks=3, yellow_ticks=2)

    for _ in range(3):
        simulation.advance_tick()
    state_after_green = simulation.state()

    assert state_after_green.light_states["N"] == LightState.YELLOW
    assert state_after_green.light_states["S"] == LightState.YELLOW
    assert state_after_green.light_states["E"] == LightState.RED
    assert state_after_green.light_states["W"] == LightState.RED

    for _ in range(2):
        simulation.advance_tick()
    state_after_handoff = simulation.state()

    assert state_after_handoff.light_states["N"] == LightState.RED
    assert state_after_handoff.light_states["S"] == LightState.RED
    assert state_after_handoff.light_states["E"] == LightState.GREEN
    assert state_after_handoff.light_states["W"] == LightState.GREEN


def _build_single_arm_simulation_for_spawn_tests(
    *,
    seed: int | None,
    spawn_rate: float,
    inbound_lanes: dict[str, tuple[InboundLaneSpawnConfig, ...]],
) -> IntersectionSimulation:
    controller = TrafficLightController(
        arm_names=["N"],
        phases=[ArmPhase(arms=("N",), name="N")],
        green_ticks=GREEN_DURATION_TICKS,
        yellow_ticks=YELLOW_DURATION_TICKS,
    )
    return IntersectionSimulation(
        arm_names=("N",),
        controller=controller,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        stop_line_distance=STOP_LINE_DISTANCE,
        vehicle_flow=VehicleFlowConfig(
            top_speed=VEHICLE_TOP_SPEED,
            acceleration=VEHICLE_ACCELERATION,
            deceleration=VEHICLE_DECELERATION,
            length=VEHICLE_LENGTH,
            queue_gap=VEHICLE_QUEUE_GAP,
            stop_distance_before_line=VEHICLE_STOP_DISTANCE_BEFORE_LINE,
        ),
        spawn=TrafficSpawnConfig(
            lambda_per_second=spawn_rate,
            ticks_per_second=SIMULATION_TICKS_PER_SECOND,
            seed=seed,
            inbound_lanes_by_arm=inbound_lanes,
        ),
    )


def test_shared_lane_probabilities_drive_committed_movement_deterministically():
    lane_config = {
        "N": (
            InboundLaneSpawnConfig(
                movements=("left", "right"),
                movement_probabilities={"left": 1.0, "right": 0.0},
            ),
        )
    }
    first = _build_single_arm_simulation_for_spawn_tests(
        seed=13,
        spawn_rate=600.0,
        inbound_lanes=lane_config,
    )
    second = _build_single_arm_simulation_for_spawn_tests(
        seed=13,
        spawn_rate=600.0,
        inbound_lanes=lane_config,
    )

    for _ in range(40):
        first_state = first.state()
        second_state = second.state()
        assert tuple(
            (
                vehicle.arm,
                vehicle.lane_index,
                vehicle.committed_movement,
                round(vehicle.position, 3),
                vehicle.state,
            )
            for vehicle in first_state.vehicles
        ) == tuple(
            (
                vehicle.arm,
                vehicle.lane_index,
                vehicle.committed_movement,
                round(vehicle.position, 3),
                vehicle.state,
            )
            for vehicle in second_state.vehicles
        )
        assert all(vehicle.committed_movement == "left" for vehicle in first_state.vehicles)
        first.advance_tick()
        second.advance_tick()


def test_spawn_does_not_switch_to_other_lane_when_selected_lane_entry_is_blocked():
    lane_config = {
        "N": (
            InboundLaneSpawnConfig(movements=("straight",)),
            InboundLaneSpawnConfig(movements=("left",)),
        )
    }
    simulation = _build_single_arm_simulation_for_spawn_tests(
        seed=1,
        spawn_rate=600.0,
        inbound_lanes=lane_config,
    )

    initial_state = simulation.state()
    assert len(initial_state.vehicles) == 1
    assert initial_state.vehicles[0].lane_index == 0

    simulation.advance_tick()
    state_after_blocked_spawn_attempt = simulation.state()

    assert len(state_after_blocked_spawn_attempt.vehicles) == 1
    assert all(vehicle.lane_index == 0 for vehicle in state_after_blocked_spawn_attempt.vehicles)


def test_state_exposes_per_lane_light_states_for_each_inbound_lane():
    simulation = _build_single_arm_simulation_for_spawn_tests(
        seed=3,
        spawn_rate=0.0,
        inbound_lanes={
            "N": (
                InboundLaneSpawnConfig(movements=("straight",)),
                InboundLaneSpawnConfig(movements=("left",)),
            )
        },
    )

    state = simulation.state()

    assert state.lane_counts_by_arm == {"N": 2}
    assert state.lane_light_states == {("N", 0): LightState.GREEN, ("N", 1): LightState.GREEN}

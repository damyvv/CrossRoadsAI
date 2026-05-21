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
from crossroads.simulation import (
    InboundLaneSpawnConfig,
    IntersectionSimulation,
    TrafficSpawnConfig,
    VehicleFlowConfig,
)
from crossroads.traffic_light import LightState, TrafficLightController
from crossroads.traffic_phasing import ArmPhase, default_four_way_phases


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


def test_state_exposes_light_states_and_vehicle_snapshots():
    simulation = _build_simulation(seed=3, spawn_rate=0.0)

    state = simulation.state()

    assert set(state.light_states) == {"N", "E", "S", "W"}
    assert state.light_states["N"] == LightState.GREEN
    assert state.light_states["S"] == LightState.GREEN
    assert state.light_states["E"] == LightState.RED
    assert state.light_states["W"] == LightState.RED
    assert state.vehicles == ()


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

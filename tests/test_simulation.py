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
from crossroads.simulation import IntersectionSimulation, TrafficSpawnConfig, VehicleFlowConfig
from crossroads.traffic_light import LightState
from crossroads.traffic_phasing import default_four_way_phases


def _build_simulation(
    *,
    seed: int | None,
    spawn_rate: float,
    green_ticks: int = GREEN_DURATION_TICKS,
    yellow_ticks: int = YELLOW_DURATION_TICKS,
) -> IntersectionSimulation:
    return IntersectionSimulation(
        arm_names=("N", "E", "S", "W"),
        phases=default_four_way_phases(),
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        stop_line_distance=STOP_LINE_DISTANCE,
        green_ticks=green_ticks,
        yellow_ticks=yellow_ticks,
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

"""
Headless simulation tests that verify deterministic behavior without a display.
"""
# Inlined config constants (previously in crossroads.config)
GREEN_DURATION_TICKS = 150
SIMULATION_TICKS_PER_SECOND = 60
STOP_LINE_DISTANCE = 70
VEHICLE_ACCELERATION = 0.20
VEHICLE_DECELERATION = 0.30
VEHICLE_LENGTH = 24
VEHICLE_QUEUE_GAP = 8
VEHICLE_STOP_DISTANCE_BEFORE_LINE = 10.0
VEHICLE_TOP_SPEED = 4.0
WINDOW_HEIGHT = 720
WINDOW_WIDTH = 960
YELLOW_DURATION_TICKS = 60
from crossroads.simulation import IntersectionSimulation, TrafficSpawnConfig, VehicleFlowConfig
from crossroads.traffic_light import LightState, TrafficLightController
from crossroads.traffic_phasing import default_four_way_phases


def _build_simulation_with_injected_controller(
    *,
    controller: TrafficLightController,
    seed: int | None,
    spawn_rate: float,
) -> IntersectionSimulation:
    """Build simulation with an explicitly injected controller."""
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
            ticks_per_second=SIMULATION_TICKS_PER_SECOND,
            seed=seed,
        ),
    )


def test_controller_dependency_injection():
    """Verify that light controller can be injected into simulation."""
    controller = TrafficLightController(
        arm_names=["N", "E", "S", "W"],
        phases=default_four_way_phases(),
        green_ticks=GREEN_DURATION_TICKS,
        yellow_ticks=YELLOW_DURATION_TICKS,
    )
    
    simulation = _build_simulation_with_injected_controller(
        controller=controller,
        seed=42,
        spawn_rate=0.0,
    )
    
    state = simulation.state()
    assert state.light_states["N"] == LightState.GREEN
    assert state.light_states["S"] == LightState.GREEN
    assert state.light_states["E"] == LightState.RED
    assert state.light_states["W"] == LightState.RED


def test_headless_simulation_snapshot_determinism():
    """Verify that simulation produces deterministic snapshots with fixed seed."""
    controller1 = TrafficLightController(
        arm_names=["N", "E", "S", "W"],
        phases=default_four_way_phases(),
        green_ticks=GREEN_DURATION_TICKS,
        yellow_ticks=YELLOW_DURATION_TICKS,
    )
    controller2 = TrafficLightController(
        arm_names=["N", "E", "S", "W"],
        phases=default_four_way_phases(),
        green_ticks=GREEN_DURATION_TICKS,
        yellow_ticks=YELLOW_DURATION_TICKS,
    )

    sim1 = _build_simulation_with_injected_controller(
        controller=controller1,
        seed=123,
        spawn_rate=2.5,
    )
    sim2 = _build_simulation_with_injected_controller(
        controller=controller2,
        seed=123,
        spawn_rate=2.5,
    )

    # Run both simulations for 60 ticks
    tick_count = 60
    for _ in range(tick_count):
        state1 = sim1.state()
        state2 = sim2.state()

        # Verify light states match
        assert state1.light_states == state2.light_states

        # Verify vehicle count matches
        assert len(state1.vehicles) == len(state2.vehicles)

        # Verify vehicle positions and states match (within floating point tolerance)
        for v1, v2 in zip(state1.vehicles, state2.vehicles):
            assert v1.arm == v2.arm
            assert abs(v1.position - v2.position) < 0.01
            assert v1.state == v2.state
            assert v1.wait_ticks == v2.wait_ticks
        
        sim1.advance_tick()
        sim2.advance_tick()


def test_headless_simulation_metrics_available():
    """Verify metrics are produced from actual simulated traffic activity."""
    controller = TrafficLightController(
        arm_names=["N", "E", "S", "W"],
        phases=default_four_way_phases(),
        green_ticks=8,
        yellow_ticks=2,
    )

    simulation = _build_simulation_with_injected_controller(
        controller=controller,
        seed=999,
        spawn_rate=6.0,
    )

    observed_vehicle = False
    for _ in range(220):
        if simulation.state().vehicles:
            observed_vehicle = True
        simulation.advance_tick()

    avg_wait = simulation.average_wait_time()
    assert observed_vehicle, "Expected at least one spawned vehicle during the run"
    assert isinstance(avg_wait, (int, float))
    assert avg_wait > 0

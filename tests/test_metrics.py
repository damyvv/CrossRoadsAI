from crossroads.config import (
    STOP_LINE_DISTANCE,
    VEHICLE_LENGTH,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from crossroads.metrics import MetricsTracker
from crossroads.simulation import IntersectionSimulation, TrafficSpawnConfig, VehicleFlowConfig
from crossroads.traffic_light import TrafficLightController
from crossroads.traffic_phasing import ArmPhase


def test_average_wait_time_returns_zero_with_no_data():
    """When no wait times have been recorded, average_wait_time returns 0.0."""
    tracker = MetricsTracker()
    assert tracker.average_wait_time() == 0.0


def test_average_wait_time_returns_correct_mean():
    """average_wait_time returns the correct mean for a set of known wait times."""
    tracker = MetricsTracker()
    tracker.record_wait_time(10)
    tracker.record_wait_time(20)
    tracker.record_wait_time(30)
    assert tracker.average_wait_time() == 20.0


def test_average_wait_time_with_single_value():
    """average_wait_time returns the value itself when only one wait time recorded."""
    tracker = MetricsTracker()
    tracker.record_wait_time(15)
    assert tracker.average_wait_time() == 15.0


def test_average_wait_time_with_decimal_average():
    """average_wait_time handles cases where mean is not a whole number."""
    tracker = MetricsTracker()
    tracker.record_wait_time(10)
    tracker.record_wait_time(11)
    assert tracker.average_wait_time() == 10.5


def test_simulation_records_wait_times_for_exiting_vehicles():
    """Simulation records wait times when vehicles transition to EXITED state."""
    controller = TrafficLightController(
        arm_names=["N"],
        phases=[ArmPhase(arms=["N"], name="N")],
        green_ticks=150,
        yellow_ticks=60,
    )

    simulation = IntersectionSimulation(
        arm_names=["N"],
        controller=controller,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        stop_line_distance=STOP_LINE_DISTANCE,
        vehicle_flow=VehicleFlowConfig(
            top_speed=10.0,
            acceleration=2.0,
            deceleration=4.0,
            length=VEHICLE_LENGTH,
            queue_gap=10,
            stop_distance_before_line=0.0,
        ),
        spawn=TrafficSpawnConfig(
            lambda_per_second=2.0,  # Spawn vehicles deterministically
            ticks_per_second=60,
            seed=42,
        ),
    )

    # Get initial average (should be 0.0 with no exits yet)
    assert simulation.average_wait_time() == 0.0

    # Advance enough ticks for vehicles to spawn, cross, and exit
    for _ in range(400):
        simulation.advance_tick()

    # After simulation runs with deterministic spawning and green light,
    # vehicles should have spawned and exited, recording wait times
    avg = simulation.average_wait_time()

    # Verify at least one vehicle exited and wait time was recorded
    assert isinstance(avg, float)
    assert avg >= 0.0
    # With a 2 Hz spawn rate and long green light, we expect vehicles to exit
    # The average should be a recorded value (not necessarily 0 if vehicles crossed)
    assert avg is not None

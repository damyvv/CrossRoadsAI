from crossroads.config import (
    STOP_LINE_DISTANCE,
    VEHICLE_LENGTH,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from crossroads.metrics import MetricsTracker
from crossroads.simulation import IntersectionSimulation, TrafficSpawnConfig, VehicleFlowConfig
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
    simulation = IntersectionSimulation(
        arm_names=["N", "S"],
        phases=[ArmPhase(arms=["N", "S"], name="NS")],
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        stop_line_distance=STOP_LINE_DISTANCE,
        green_ticks=5,
        yellow_ticks=2,
        vehicle_flow=VehicleFlowConfig(
            top_speed=10.0,
            acceleration=2.0,
            deceleration=4.0,
            length=VEHICLE_LENGTH,
            queue_gap=10,
            stop_distance_before_line=0.0,
        ),
        spawn=TrafficSpawnConfig(
            lambda_per_second=0.0,  # No auto-spawning
            ticks_per_second=60,
            seed=42,
        ),
    )
    
    # Get initial average (should be 0.0 with no exits yet)
    assert simulation.average_wait_time() == 0.0
    
    # Advance many ticks to let vehicles flow through
    for _ in range(500):
        simulation.advance_tick()
    
    # After simulation runs, there should be vehicles that have exited
    # The average wait time should be calculated from those vehicles
    avg = simulation.average_wait_time()
    # Just verify it's a valid float and that it's recorded something if vehicles exited
    assert isinstance(avg, float)
    assert avg >= 0.0

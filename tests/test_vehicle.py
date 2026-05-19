from crossroads.config import ROAD_WIDTH, WINDOW_HEIGHT, WINDOW_WIDTH
from crossroads.vehicle import Vehicle, VehicleState, crossing_bounds_for_arm


def test_vehicle_accelerates_toward_top_speed():
    vehicle = Vehicle(
        arm="N",
        crossing_start=100.0,
        crossing_end=200.0,
        target_velocity=3.0,
        max_velocity=3.0,
        acceleration=1.0,
        deceleration=2.0,
    )

    assert vehicle.state == VehicleState.APPROACHING
    assert vehicle.velocity == 0.0

    vehicle.advance_tick()
    assert vehicle.velocity == 1.0

    vehicle.advance_tick()
    assert vehicle.velocity == 2.0

    vehicle.advance_tick()
    assert vehicle.velocity == 3.0


def test_vehicle_does_not_overshoot_exit_boundary():
    vehicle = Vehicle(
        arm="N",
        crossing_start=5.0,
        crossing_end=10.0,
        target_velocity=4.0,
        max_velocity=4.0,
        acceleration=4.0,
        deceleration=2.0,
        position=8.5,
    )

    vehicle.advance_tick()

    assert vehicle.position == 10.0
    assert vehicle.state == VehicleState.EXITED


def test_vehicle_state_transitions_approaching_to_crossing_to_exited():
    vehicle = Vehicle(
        arm="N",
        crossing_start=5.0,
        crossing_end=9.0,
        target_velocity=2.0,
        max_velocity=2.0,
        acceleration=2.0,
        deceleration=2.0,
    )

    assert vehicle.state == VehicleState.APPROACHING

    vehicle.advance_tick()  # pos 2
    assert vehicle.state == VehicleState.APPROACHING

    vehicle.advance_tick()  # pos 4
    assert vehicle.state == VehicleState.APPROACHING

    vehicle.advance_tick()  # pos 6
    assert vehicle.state == VehicleState.CROSSING

    vehicle.advance_tick()  # pos 8
    assert vehicle.state == VehicleState.CROSSING

    vehicle.advance_tick()  # pos clamped to 9
    assert vehicle.position == 9.0
    assert vehicle.state == VehicleState.EXITED


def test_crossing_bounds_align_with_intersection_box():
    cx = WINDOW_WIDTH // 2
    cy = WINDOW_HEIGHT // 2
    half_road = ROAD_WIDTH // 2

    north_start, north_end = crossing_bounds_for_arm(
        arm="N",
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        road_width=ROAD_WIDTH,
    )
    west_start, west_end = crossing_bounds_for_arm(
        arm="W",
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        road_width=ROAD_WIDTH,
    )

    assert (north_start, north_end) == (float(cy - half_road), float(cy + half_road))
    assert (west_start, west_end) == (float(cx - half_road), float(cx + half_road))

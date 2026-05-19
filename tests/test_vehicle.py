from crossroads.config import (
    ROAD_WIDTH,
    STOP_LINE_DISTANCE,
    VEHICLE_LENGTH,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from crossroads.vehicle import (
    Vehicle,
    VehicleState,
    lane_center_world_position,
    spawn_distance_for_length,
    state_thresholds_for_arm,
)


def test_vehicle_accelerates_linearly_to_top_speed():
    vehicle = Vehicle(
        arm="N",
        crossing_distance=100.0,
        exit_distance=200.0,
        discard_distance=400.0,
        target_velocity=3.0,
        max_velocity=3.0,
        acceleration=1.0,
        deceleration=2.0,
        position=0.0,
    )

    vehicle.advance_tick()
    assert vehicle.velocity == 1.0
    vehicle.advance_tick()
    assert vehicle.velocity == 2.0
    vehicle.advance_tick()
    assert vehicle.velocity == 3.0
    vehicle.advance_tick()
    assert vehicle.velocity == 3.0


def test_lane_centerline_uses_right_hand_inbound_lane_offset():
    cx = WINDOW_WIDTH // 2
    cy = WINDOW_HEIGHT // 2
    lane_offset = ROAD_WIDTH / 4

    n_pos = lane_center_world_position(
        arm="N",
        distance=0.0,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        road_width=ROAD_WIDTH,
    )
    e_pos = lane_center_world_position(
        arm="E",
        distance=0.0,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        road_width=ROAD_WIDTH,
    )
    s_pos = lane_center_world_position(
        arm="S",
        distance=0.0,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        road_width=ROAD_WIDTH,
    )
    w_pos = lane_center_world_position(
        arm="W",
        distance=0.0,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        road_width=ROAD_WIDTH,
    )

    assert n_pos == (cx - lane_offset, 0.0)
    assert e_pos == (WINDOW_WIDTH - 1.0, cy - lane_offset)
    assert s_pos == (cx + lane_offset, WINDOW_HEIGHT - 1.0)
    assert w_pos == (0.0, cy + lane_offset)


def test_vehicle_state_boundaries_follow_approaching_crossing_exited_discard():
    thresholds = state_thresholds_for_arm(
        arm="N",
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        stop_line_distance=STOP_LINE_DISTANCE,
        vehicle_length=VEHICLE_LENGTH,
    )
    vehicle = Vehicle(
        arm="N",
        crossing_distance=thresholds.crossing,
        exit_distance=thresholds.exited,
        discard_distance=thresholds.discard,
        target_velocity=0.0,
        max_velocity=4.0,
        acceleration=1.0,
        deceleration=1.0,
        position=thresholds.crossing - 0.1,
    )
    assert vehicle.state == VehicleState.APPROACHING

    vehicle.position = thresholds.crossing
    vehicle.advance_tick()
    assert vehicle.state == VehicleState.CROSSING

    vehicle.position = thresholds.exited
    vehicle.advance_tick()
    assert vehicle.state == VehicleState.EXITED

    vehicle.position = thresholds.discard
    vehicle.advance_tick()
    assert vehicle.state == VehicleState.DISCARD


def test_vehicle_position_clamps_at_discard_boundary_without_overshoot():
    thresholds = state_thresholds_for_arm(
        arm="W",
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        stop_line_distance=STOP_LINE_DISTANCE,
        vehicle_length=VEHICLE_LENGTH,
    )
    vehicle = Vehicle(
        arm="W",
        crossing_distance=thresholds.crossing,
        exit_distance=thresholds.exited,
        discard_distance=thresholds.discard,
        target_velocity=10.0,
        max_velocity=10.0,
        acceleration=10.0,
        deceleration=1.0,
        position=thresholds.discard - 0.5,
    )

    vehicle.advance_tick()

    assert vehicle.position == thresholds.discard
    assert vehicle.state == VehicleState.DISCARD


def test_spawn_distance_places_vehicle_fully_outside_entry_side():
    assert spawn_distance_for_length(VEHICLE_LENGTH) < -(VEHICLE_LENGTH / 2)

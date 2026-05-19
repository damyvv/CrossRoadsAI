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


def test_vehicle_decelerates_to_stop_line_on_red_without_passing():
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
        target_velocity=4.0,
        max_velocity=4.0,
        acceleration=0.2,
        deceleration=0.3,
        position=thresholds.crossing - 60.0,
    )

    for _ in range(200):
        vehicle.advance_tick(can_enter_intersection=False)
        if vehicle.state == VehicleState.STOPPED:
            break

    assert vehicle.state == VehicleState.STOPPED
    assert vehicle.position <= thresholds.crossing
    assert thresholds.crossing - vehicle.position <= VEHICLE_LENGTH


def test_vehicle_transitions_stopped_to_crossing_when_light_turns_green():
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
        target_velocity=4.0,
        max_velocity=4.0,
        acceleration=0.2,
        deceleration=0.3,
        position=thresholds.crossing - 60.0,
    )

    for _ in range(200):
        vehicle.advance_tick(can_enter_intersection=False)
        if vehicle.state == VehicleState.STOPPED:
            break
    assert vehicle.state == VehicleState.STOPPED

    vehicle.advance_tick(can_enter_intersection=True)

    assert vehicle.state == VehicleState.CROSSING


def test_vehicle_wait_ticks_accumulate_while_stopped():
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
        target_velocity=4.0,
        max_velocity=4.0,
        acceleration=0.2,
        deceleration=0.3,
        position=thresholds.crossing - 60.0,
    )

    for _ in range(200):
        vehicle.advance_tick(can_enter_intersection=False)
        if vehicle.state == VehicleState.STOPPED:
            break

    start_wait_ticks = vehicle.wait_ticks
    for _ in range(12):
        vehicle.advance_tick(can_enter_intersection=False)

    assert vehicle.state == VehicleState.STOPPED
    assert vehicle.wait_ticks - start_wait_ticks == 12


def test_vehicles_queue_with_gap_and_depart_without_collision():
    thresholds = state_thresholds_for_arm(
        arm="N",
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        stop_line_distance=STOP_LINE_DISTANCE,
        vehicle_length=VEHICLE_LENGTH,
    )
    leader = Vehicle(
        arm="N",
        crossing_distance=thresholds.crossing,
        exit_distance=thresholds.exited,
        discard_distance=thresholds.discard,
        target_velocity=4.0,
        max_velocity=4.0,
        acceleration=0.2,
        deceleration=0.3,
        position=thresholds.crossing - 60.0,
    )
    follower = Vehicle(
        arm="N",
        crossing_distance=thresholds.crossing,
        exit_distance=thresholds.exited,
        discard_distance=thresholds.discard,
        target_velocity=4.0,
        max_velocity=4.0,
        acceleration=0.2,
        deceleration=0.3,
        position=thresholds.crossing - 100.0,
    )

    for _ in range(180):
        leader.advance_tick(can_enter_intersection=False)
        follower.advance_tick(
            can_enter_intersection=False,
            max_position=leader.position - VEHICLE_LENGTH,
        )
        assert follower.position <= leader.position - VEHICLE_LENGTH

    assert leader.state == VehicleState.STOPPED
    assert follower.state == VehicleState.STOPPED

    leader_crossed = False
    follower_crossed = False
    for _ in range(120):
        leader.advance_tick(can_enter_intersection=True)
        follower.advance_tick(
            can_enter_intersection=True,
            max_position=leader.position - VEHICLE_LENGTH,
        )
        assert follower.position <= leader.position - VEHICLE_LENGTH
        leader_crossed = leader_crossed or leader.state == VehicleState.CROSSING
        follower_crossed = follower_crossed or follower.state == VehicleState.CROSSING

    assert leader_crossed
    assert follower_crossed

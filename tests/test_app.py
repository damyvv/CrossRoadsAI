from crossroads.app import _advance_vehicles, _entry_occupied_by_arm
from crossroads.config import (
    GREEN_DURATION_TICKS,
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
from crossroads.traffic_light import LightState, TrafficLightController
from crossroads.traffic_phasing import default_four_way_phases
from crossroads.vehicle import Vehicle, VehicleState, spawn_distance_for_length, state_thresholds_for_arm


def _vehicle_on_arm(*, arm: str, position: float) -> Vehicle:
    thresholds = state_thresholds_for_arm(
        arm=arm,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        stop_line_distance=STOP_LINE_DISTANCE,
        vehicle_length=VEHICLE_LENGTH,
    )
    return Vehicle(
        arm=arm,
        crossing_distance=thresholds.crossing,
        exit_distance=thresholds.exited,
        discard_distance=thresholds.discard,
        target_velocity=VEHICLE_TOP_SPEED,
        max_velocity=VEHICLE_TOP_SPEED,
        acceleration=VEHICLE_ACCELERATION,
        deceleration=VEHICLE_DECELERATION,
        position=position,
    )


def test_entry_stays_blocked_until_vehicle_clears_spawn_zone():
    spawn_distance = spawn_distance_for_length(VEHICLE_LENGTH)
    almost_clear = _vehicle_on_arm(
        arm="N",
        position=spawn_distance + VEHICLE_LENGTH - 0.1,
    )
    clear = _vehicle_on_arm(
        arm="N",
        position=spawn_distance + VEHICLE_LENGTH + 0.1,
    )

    occupied_before_clear = _entry_occupied_by_arm(
        arm_names=("N",),
        vehicles=[almost_clear],
        entry_distance=spawn_distance,
        clearance_distance=float(VEHICLE_LENGTH),
    )
    occupied_after_clear = _entry_occupied_by_arm(
        arm_names=("N",),
        vehicles=[clear],
        entry_distance=spawn_distance,
        clearance_distance=float(VEHICLE_LENGTH),
    )

    assert occupied_before_clear["N"] is True
    assert occupied_after_clear["N"] is False


def test_advance_vehicles_queues_on_red_and_releases_on_green():
    leader = _vehicle_on_arm(arm="E", position=80.0)
    follower = _vehicle_on_arm(arm="E", position=40.0)
    controller = TrafficLightController(
        arm_names=["N", "E", "S", "W"],
        phases=list(default_four_way_phases()),
        green_ticks=GREEN_DURATION_TICKS,
        yellow_ticks=YELLOW_DURATION_TICKS,
    )
    vehicles = [leader, follower]

    for _ in range(160):
        _advance_vehicles(
            vehicles=vehicles,
            arm_names=("N", "E", "S", "W"),
            controller=controller,
            min_following_distance=float(VEHICLE_LENGTH + VEHICLE_QUEUE_GAP),
            stop_margin_to_line=float(VEHICLE_LENGTH) / 2 + VEHICLE_STOP_DISTANCE_BEFORE_LINE,
            crossing_distance_by_arm={"N": 0.0, "E": leader.crossing_distance, "S": 0.0, "W": 0.0},
        )
        assert follower.position <= leader.position - (VEHICLE_LENGTH + VEHICLE_QUEUE_GAP)

    assert leader.wait_ticks > 0
    assert follower.wait_ticks > 0

    for _ in range(GREEN_DURATION_TICKS + YELLOW_DURATION_TICKS):
        controller.advance_tick()
    assert controller.state("E") == LightState.GREEN

    moved_before = follower.position
    for _ in range(10):
        _advance_vehicles(
            vehicles=vehicles,
            arm_names=("N", "E", "S", "W"),
            controller=controller,
            min_following_distance=float(VEHICLE_LENGTH + VEHICLE_QUEUE_GAP),
            stop_margin_to_line=float(VEHICLE_LENGTH) / 2 + VEHICLE_STOP_DISTANCE_BEFORE_LINE,
            crossing_distance_by_arm={"N": 0.0, "E": leader.crossing_distance, "S": 0.0, "W": 0.0},
        )
        assert follower.position <= leader.position - (VEHICLE_LENGTH + VEHICLE_QUEUE_GAP)

    assert follower.position > moved_before


def test_advance_vehicles_respects_configurable_stop_distance_before_line():
    vehicle = _vehicle_on_arm(arm="E", position=200.0)
    controller = TrafficLightController(
        arm_names=["N", "E", "S", "W"],
        phases=list(default_four_way_phases()),
        green_ticks=GREEN_DURATION_TICKS,
        yellow_ticks=YELLOW_DURATION_TICKS,
    )
    extra_stop_distance = 15.0
    stop_margin = (VEHICLE_LENGTH / 2) + extra_stop_distance

    for _ in range(200):
        _advance_vehicles(
            vehicles=[vehicle],
            arm_names=("N", "E", "S", "W"),
            controller=controller,
            min_following_distance=float(VEHICLE_LENGTH + VEHICLE_QUEUE_GAP),
            stop_margin_to_line=stop_margin,
            crossing_distance_by_arm={"N": 0.0, "E": vehicle.crossing_distance, "S": 0.0, "W": 0.0},
        )
        if vehicle.state == VehicleState.STOPPED:
            break

    assert vehicle.position <= vehicle.crossing_distance - stop_margin

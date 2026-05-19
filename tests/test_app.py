from crossroads.app import _entry_occupied_by_arm
from crossroads.config import (
    STOP_LINE_DISTANCE,
    VEHICLE_ACCELERATION,
    VEHICLE_DECELERATION,
    VEHICLE_LENGTH,
    VEHICLE_TOP_SPEED,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from crossroads.vehicle import Vehicle, spawn_distance_for_length, state_thresholds_for_arm


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

import math

import pytest

from crossroads.intersection import build_intersection_geometry
from crossroads.lane_paths import precompute_lane_paths


class _Lane:
    def __init__(self, *movements: str) -> None:
        self.movements = movements


def test_precompute_lane_paths_covers_each_allowed_lane_movement():
    geometry = build_intersection_geometry(
        window_width=960,
        window_height=720,
        arm_count=4,
        road_width_by_arm={"N": 72, "E": 48, "S": 60, "W": 48},
        inbound_lane_count_by_arm={"N": 2, "E": 1, "S": 1, "W": 1},
        lane_width=12,
        outbound_lane_count_by_arm={"N": 2, "E": 2, "S": 2, "W": 2},
        stop_line_distance=80,
    )
    inbound_lanes = {
        "N": (_Lane("left"), _Lane("straight", "right")),
        "E": (_Lane("straight"),),
        "S": (_Lane("straight"),),
        "W": (_Lane("straight"),),
    }

    paths = precompute_lane_paths(
        geometry=geometry,
        inbound_lanes_by_arm=inbound_lanes,
        outbound_lane_count_by_arm={"N": 2, "E": 2, "S": 2, "W": 2},
        window_width=960,
        window_height=720,
        lane_width=12,
    )

    assert set(paths) == {
        ("N", 0, "left"),
        ("N", 1, "straight"),
        ("N", 1, "right"),
        ("E", 0, "straight"),
        ("S", 0, "straight"),
        ("W", 0, "straight"),
    }


def test_turn_paths_are_deterministic_from_same_inputs():
    geometry = build_intersection_geometry(
        window_width=960,
        window_height=720,
        arm_count=4,
        road_width_by_arm={"N": 72, "E": 48, "S": 72, "W": 48},
        inbound_lane_count_by_arm={"N": 2, "E": 1, "S": 2, "W": 1},
        lane_width=12,
        outbound_lane_count_by_arm={"N": 3, "E": 3, "S": 3, "W": 3},
        stop_line_distance=80,
    )
    inbound_lanes = {
        "N": (_Lane("left"), _Lane("left")),
        "E": (_Lane("straight"),),
        "S": (_Lane("straight"), _Lane("straight")),
        "W": (_Lane("straight"),),
    }
    kwargs = dict(
        geometry=geometry,
        inbound_lanes_by_arm=inbound_lanes,
        outbound_lane_count_by_arm={"N": 3, "E": 3, "S": 3, "W": 3},
        window_width=960,
        window_height=720,
        lane_width=12,
    )

    first = precompute_lane_paths(**kwargs)
    second = precompute_lane_paths(**kwargs)

    assert first == second


def test_left_turn_from_north_rightmost_lane_targets_rightmost_outbound_lane():
    geometry = build_intersection_geometry(
        window_width=960,
        window_height=720,
        arm_count=4,
        road_width_by_arm={"N": 72, "E": 60, "S": 72, "W": 60},
        inbound_lane_count_by_arm={"N": 1, "E": 1, "S": 1, "W": 1},
        lane_width=12,
        outbound_lane_count_by_arm={"N": 2, "E": 3, "S": 2, "W": 2},
        stop_line_distance=80,
    )
    inbound_lanes = {
        "N": (_Lane("left"),),
        "E": (_Lane("straight"),),
        "S": (_Lane("straight"),),
        "W": (_Lane("straight"),),
    }
    paths = precompute_lane_paths(
        geometry=geometry,
        inbound_lanes_by_arm=inbound_lanes,
        outbound_lane_count_by_arm={"N": 2, "E": 3, "S": 2, "W": 2},
        window_width=960,
        window_height=720,
        lane_width=12,
    )

    lane_path = paths[("N", 0, "left")]
    assert lane_path.target_arm == "E"
    assert lane_path.target_outbound_lane_index == 2
    assert len(lane_path.points) > 2

    start = lane_path.points[0]
    end = lane_path.points[-1]
    assert end[0] > start[0]
    north_stop_line = next(arm.stop_line for arm in geometry.arms if arm.name == "N")
    (stop_start_x, stop_start_y), (stop_end_x, stop_end_y) = north_stop_line
    assert stop_start_y == stop_end_y
    assert math.isclose(start[1], float(stop_start_y), abs_tol=1e-9)
    assert min(stop_start_x, stop_end_x) <= start[0] <= max(stop_start_x, stop_end_x)

    # Quarter-turn radius equals horizontal/vertical offset from start to end.
    assert math.isclose(abs(end[0] - start[0]), abs(end[1] - start[1]), rel_tol=0, abs_tol=1e-9)
    # N->E left turn should stay in the south-east quadrant from the start point.
    assert all(point[0] >= start[0] and point[1] >= start[1] for point in lane_path.points[1:])


def test_turn_lane_mapping_is_right_aligned_with_leftmost_clamp():
    geometry = build_intersection_geometry(
        window_width=960,
        window_height=720,
        arm_count=4,
        road_width_by_arm={"N": 96, "E": 60, "S": 72, "W": 60},
        inbound_lane_count_by_arm={"N": 4, "E": 1, "S": 1, "W": 1},
        lane_width=12,
        outbound_lane_count_by_arm={"N": 2, "E": 3, "S": 2, "W": 2},
        stop_line_distance=80,
    )
    inbound_lanes = {
        "N": (_Lane("left"), _Lane("left"), _Lane("left"), _Lane("left")),
        "E": (_Lane("straight"),),
        "S": (_Lane("straight"),),
        "W": (_Lane("straight"),),
    }
    paths = precompute_lane_paths(
        geometry=geometry,
        inbound_lanes_by_arm=inbound_lanes,
        outbound_lane_count_by_arm={"N": 2, "E": 3, "S": 2, "W": 2},
        window_width=960,
        window_height=720,
        lane_width=12,
    )

    assert paths[("N", 3, "left")].target_outbound_lane_index == 2
    assert paths[("N", 2, "left")].target_outbound_lane_index == 1
    assert paths[("N", 1, "left")].target_outbound_lane_index == 0
    assert paths[("N", 0, "left")].target_outbound_lane_index == 0


def test_precompute_lane_paths_rejects_movement_target_arm_missing_from_geometry():
    geometry = build_intersection_geometry(
        window_width=960,
        window_height=720,
        arm_count=2,
        road_width_by_arm={"N": 48, "S": 48},
        inbound_lane_count_by_arm={"N": 1, "S": 1},
        lane_width=12,
        outbound_lane_count_by_arm={"N": 1, "S": 1},
        stop_line_distance=80,
    )
    inbound_lanes = {
        "N": (_Lane("left"),),
        "S": (_Lane("straight"),),
    }

    with pytest.raises(ValueError, match="targets missing arm"):
        precompute_lane_paths(
            geometry=geometry,
            inbound_lanes_by_arm=inbound_lanes,
            outbound_lane_count_by_arm={"N": 1, "S": 1},
            window_width=960,
            window_height=720,
            lane_width=12,
        )


def test_straight_path_to_south_uses_outbound_carriageway_offset_without_doubling():
    lane_width = 20
    geometry = build_intersection_geometry(
        window_width=960,
        window_height=720,
        arm_count=4,
        road_width_by_arm={"N": 140, "E": 80, "S": 80, "W": 80},
        inbound_lane_count_by_arm={"N": 6, "E": 2, "S": 1, "W": 2},
        straight_capable_lane_indices_by_arm={
            "N": (2, 3, 4),
            "E": (0, 1),
            "S": (0,),
            "W": (0, 1),
        },
        lane_width=lane_width,
        outbound_lane_count_by_arm={"N": 1, "E": 2, "S": 3, "W": 2},
        stop_line_distance=60,
    )
    inbound_lanes = {
        "N": (_Lane("left"), _Lane("left"), _Lane("straight"), _Lane("straight"), _Lane("straight"), _Lane("right")),
        "E": (_Lane("straight"), _Lane("straight")),
        "S": (_Lane("straight"),),
        "W": (_Lane("straight"), _Lane("straight")),
    }
    paths = precompute_lane_paths(
        geometry=geometry,
        inbound_lanes_by_arm=inbound_lanes,
        outbound_lane_count_by_arm={"N": 1, "E": 2, "S": 3, "W": 2},
        window_width=960,
        window_height=720,
        lane_width=lane_width,
    )

    # N lane index 2 (first straight lane) maps to S outbound lane index 0.
    lane_path = paths[("N", 2, "straight")]
    assert lane_path.target_arm == "S"
    assert lane_path.target_outbound_lane_index == 0
    # End x should be centered in S outbound lane 0 at x = 430, not shifted 2 lanes left to x = 390.
    assert lane_path.points[-1][0] == 430.0

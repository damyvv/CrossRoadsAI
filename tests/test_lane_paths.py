import math

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

    # Quarter-turn radius equals horizontal/vertical offset from start to end.
    assert math.isclose(abs(end[0] - start[0]), abs(end[1] - start[1]), rel_tol=0, abs_tol=1e-9)


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

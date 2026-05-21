import pytest

from crossroads.config import ROAD_WIDTH, STOP_LINE_DISTANCE, WINDOW_HEIGHT, WINDOW_WIDTH
from crossroads.intersection import (
    build_intersection_geometry,
    compute_road_width_by_arm_from_inbound_lanes,
    compute_road_width_from_inbound_lanes,
)


def test_build_intersection_geometry_has_four_cardinal_arms():
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=4,
        road_width=ROAD_WIDTH,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    assert [arm.name for arm in geometry.arms] == ["N", "E", "S", "W"]
    cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
    half_width = ROAD_WIDTH // 2
    assert [arm.stop_line for arm in geometry.arms] == [
        ((cx, cy - STOP_LINE_DISTANCE), (cx - half_width, cy - STOP_LINE_DISTANCE)),
        ((cx + STOP_LINE_DISTANCE, cy), (cx + STOP_LINE_DISTANCE, cy - half_width)),
        ((cx, cy + STOP_LINE_DISTANCE), (cx + half_width, cy + STOP_LINE_DISTANCE)),
        ((cx - STOP_LINE_DISTANCE, cy), (cx - STOP_LINE_DISTANCE, cy + half_width)),
    ]


def test_build_intersection_geometry_has_cardinal_arm_positions():
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=4,
        road_width=ROAD_WIDTH,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    assert [arm.position for arm in geometry.arms] == [
        (WINDOW_WIDTH // 2, 0),
        (WINDOW_WIDTH - 1, WINDOW_HEIGHT // 2),
        (WINDOW_WIDTH // 2, WINDOW_HEIGHT - 1),
        (0, WINDOW_HEIGHT // 2),
    ]


def test_build_intersection_geometry_has_center_lines_four_way():
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=4,
        road_width=ROAD_WIDTH,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    assert len(geometry.arm_center_lines) == 4
    cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
    assert geometry.arm_center_lines[0] == (
        (cx, 0),
        (cx, cy - STOP_LINE_DISTANCE),
    )


def test_build_intersection_geometry_computes_road_grid_from_config():
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=4,
        road_width=ROAD_WIDTH,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    assert geometry.road_rects == [
        (WINDOW_WIDTH // 2 - ROAD_WIDTH // 2, 0, ROAD_WIDTH, WINDOW_HEIGHT),
        (0, WINDOW_HEIGHT // 2 - ROAD_WIDTH // 2, WINDOW_WIDTH, ROAD_WIDTH),
    ]


def test_build_intersection_geometry_three_way():
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=3,
        missing_arm="S",
        road_width=ROAD_WIDTH,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    assert [arm.name for arm in geometry.arms] == ["N", "E", "W"]
    assert len(geometry.arms) == 3
    cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
    assert [arm.position for arm in geometry.arms] == [
        (cx, 0),
        (WINDOW_WIDTH - 1, cy),
        (0, cy),
    ]
    assert len(geometry.road_rects) == 2


def test_build_intersection_geometry_three_way_missing_arm_required():
    with pytest.raises(ValueError, match="missing_arm is required when arm_count is 3"):
        build_intersection_geometry(
            window_width=WINDOW_WIDTH,
            window_height=WINDOW_HEIGHT,
            arm_count=3,
            road_width=ROAD_WIDTH,
            stop_line_distance=STOP_LINE_DISTANCE,
        )


def test_build_intersection_geometry_three_way_missing_north_removes_north_arm():
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=3,
        missing_arm="N",
        road_width=ROAD_WIDTH,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    assert [arm.name for arm in geometry.arms] == ["E", "S", "W"]
    cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
    assert geometry.road_rects == [
        (cx - ROAD_WIDTH // 2, cy, ROAD_WIDTH, WINDOW_HEIGHT - cy),
        (0, cy - ROAD_WIDTH // 2, WINDOW_WIDTH, ROAD_WIDTH),
    ]


def test_build_intersection_geometry_two_way():
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=2,
        road_width=ROAD_WIDTH,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    assert [arm.name for arm in geometry.arms] == ["N", "S"]
    assert len(geometry.arms) == 2
    cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
    assert [arm.position for arm in geometry.arms] == [
        (cx, 0),
        (cx, WINDOW_HEIGHT - 1),
    ]
    assert len(geometry.road_rects) == 1


def test_compute_road_width_from_inbound_lanes_scales_with_max_lane_count():
    road_width = compute_road_width_from_inbound_lanes(
        inbound_lanes_by_arm={
            "N": (object(), object(), object(), object(), object()),
            "E": (object(), object()),
            "S": (object(),),
            "W": (object(), object()),
        },
        lane_width=12,
    )

    assert road_width == 84


@pytest.mark.parametrize(
    ("inbound_lanes_by_arm", "lane_width", "expected_road_width"),
    [
        ({"N": (object(),), "S": (object(),)}, 10, 30),
        ({"N": (object(), object()), "E": (object(),), "W": (object(),)}, 9, 36),
        (
            {"N": (object(),), "E": (object(), object(), object()), "S": (object(),)},
            8,
            40,
        ),
    ],
)
def test_compute_road_width_from_inbound_lanes_supports_2_3_4_arm_topologies(
    inbound_lanes_by_arm, lane_width, expected_road_width
):
    assert (
        compute_road_width_from_inbound_lanes(
            inbound_lanes_by_arm=inbound_lanes_by_arm, lane_width=lane_width
        )
        == expected_road_width
    )


def test_compute_road_width_by_arm_from_inbound_lanes_uses_inbound_plus_outbound():
    assert compute_road_width_by_arm_from_inbound_lanes(
        inbound_lanes_by_arm={
            "N": (object(), object(), object()),
            "E": (object(),),
        },
        lane_width=12,
        outbound_lane_count=2,
    ) == {
        "N": 60,
        "E": 36,
    }


def test_build_intersection_geometry_uses_per_arm_width_and_inbound_stop_line_span():
    lane_width = 12
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=4,
        road_width_by_arm={"N": 84, "E": 48, "S": 60, "W": 48},
        inbound_lane_count_by_arm={"N": 5, "E": 2, "S": 3, "W": 2},
        lane_width=lane_width,
        outbound_lane_count=2,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
    north_arm = geometry.arms[0]
    south_arm = geometry.arms[2]
    assert north_arm.center_line[1] == (cx, cy - STOP_LINE_DISTANCE)
    assert south_arm.center_line[1] == (cx, cy + STOP_LINE_DISTANCE)
    # N inbound is west side, length = 5 lanes * lane_width.
    assert north_arm.stop_line == (
        (cx, cy - STOP_LINE_DISTANCE),
        (cx - (5 * lane_width), cy - STOP_LINE_DISTANCE),
    )
    # S inbound is east side, length = 3 lanes * lane_width.
    assert south_arm.stop_line == (
        (cx, cy + STOP_LINE_DISTANCE),
        (cx + (3 * lane_width), cy + STOP_LINE_DISTANCE),
    )

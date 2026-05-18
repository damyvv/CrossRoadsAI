from crossroads.config import ROAD_WIDTH, STOP_LINE_DISTANCE, WINDOW_HEIGHT, WINDOW_WIDTH
from crossroads.intersection import build_intersection_geometry


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

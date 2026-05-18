from crossroads.config import ARM_COUNT, ROAD_WIDTH, STOP_LINE_DISTANCE, WINDOW_HEIGHT, WINDOW_WIDTH
from crossroads.intersection import build_intersection_geometry


def test_build_intersection_geometry_has_four_cardinal_arms():
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=ARM_COUNT,
        road_width=ROAD_WIDTH,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    assert [arm.name for arm in geometry.arms] == ["N", "E", "S", "W"]
    assert [arm.stop_line_point for arm in geometry.arms] == [
        (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - STOP_LINE_DISTANCE),
        (WINDOW_WIDTH // 2 + STOP_LINE_DISTANCE, WINDOW_HEIGHT // 2),
        (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + STOP_LINE_DISTANCE),
        (WINDOW_WIDTH // 2 - STOP_LINE_DISTANCE, WINDOW_HEIGHT // 2),
    ]


def test_build_intersection_geometry_has_cardinal_arm_positions():
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=ARM_COUNT,
        road_width=ROAD_WIDTH,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    assert [arm.position for arm in geometry.arms] == [
        (WINDOW_WIDTH // 2, 0),
        (WINDOW_WIDTH - 1, WINDOW_HEIGHT // 2),
        (WINDOW_WIDTH // 2, WINDOW_HEIGHT - 1),
        (0, WINDOW_HEIGHT // 2),
    ]


def test_build_intersection_geometry_is_data_driven_for_arm_count():
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=6,
        road_width=ROAD_WIDTH,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    assert len(geometry.arms) == 6
    assert [arm.name for arm in geometry.arms] == [
        "ARM_1",
        "ARM_2",
        "ARM_3",
        "ARM_4",
        "ARM_5",
        "ARM_6",
    ]


def test_build_intersection_geometry_has_center_lines():
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=ARM_COUNT,
        road_width=ROAD_WIDTH,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    assert len(geometry.arm_center_lines) == 4
    cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
    assert geometry.arm_center_lines[0] == (
        (cx, cy - STOP_LINE_DISTANCE - 100),
        (cx, cy + STOP_LINE_DISTANCE + 100),
    )


def test_build_intersection_geometry_computes_road_grid_from_config():
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=ARM_COUNT,
        road_width=ROAD_WIDTH,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    assert geometry.road_rects == [
        (WINDOW_WIDTH // 2 - ROAD_WIDTH // 2, 0, ROAD_WIDTH, WINDOW_HEIGHT),
        (0, WINDOW_HEIGHT // 2 - ROAD_WIDTH // 2, WINDOW_WIDTH, ROAD_WIDTH),
    ]


from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ArmGeometry:
    name: str
    position: tuple[int, int]
    stop_line_point: tuple[int, int]
    center_line: tuple[tuple[int, int], tuple[int, int]]


@dataclass(frozen=True)
class IntersectionGeometry:
    center: tuple[int, int]
    arms: list[ArmGeometry]
    road_rects: list[tuple[int, int, int, int]]
    arm_center_lines: list[tuple[tuple[int, int], tuple[int, int]]]


def _arm_name(index: int, arm_count: int) -> str:
    names_4 = ["N", "E", "S", "W"]
    names_3 = ["N", "E", "W"]
    names_2 = ["N", "S"]
    
    if arm_count == 4:
        return names_4[index]
    if arm_count == 3:
        return names_3[index]
    if arm_count == 2:
        return names_2[index]
    return f"ARM_{index + 1}"


def build_intersection_geometry(
    *,
    window_width: int,
    window_height: int,
    arm_count: int,
    road_width: int,
    stop_line_distance: int,
) -> IntersectionGeometry:
    center = (window_width // 2, window_height // 2)
    cx, cy = center

    if arm_count == 4:
        return _build_four_way_intersection(center, cx, cy, window_width, window_height, road_width, stop_line_distance)
    elif arm_count == 3:
        return _build_three_way_intersection(center, cx, cy, window_width, window_height, road_width, stop_line_distance)
    elif arm_count == 2:
        return _build_two_way_intersection(center, cx, cy, window_width, window_height, road_width, stop_line_distance)
    else:
        raise ValueError("arm_count must be 2, 3, or 4")


def _build_four_way_intersection(center, cx, cy, window_width, window_height, road_width, stop_line_distance):
    positions = [
        (cx, 0),
        (window_width - 1, cy),
        (cx, window_height - 1),
        (0, cy),
    ]
    stop_lines = [
        (cx, cy - stop_line_distance),
        (cx + stop_line_distance, cy),
        (cx, cy + stop_line_distance),
        (cx - stop_line_distance, cy),
    ]
    center_lines = [
        ((cx, 0), (cx, cy - stop_line_distance)),
        ((cx + stop_line_distance, cy), (window_width - 1, cy)),
        ((cx, cy + stop_line_distance), (cx, window_height - 1)),
        ((cx - stop_line_distance, cy), (0, cy)),
    ]
    arms = [
        ArmGeometry(
            name=_arm_name(index, 4),
            position=positions[index],
            stop_line_point=stop_line_point,
            center_line=center_lines[index],
        )
        for index, stop_line_point in enumerate(stop_lines)
    ]
    road_rects = [
        (cx - road_width // 2, 0, road_width, window_height),
        (0, cy - road_width // 2, window_width, road_width),
    ]
    arm_center_lines = center_lines
    return IntersectionGeometry(center=center, arms=arms, road_rects=road_rects, arm_center_lines=arm_center_lines)


def _build_three_way_intersection(center, cx, cy, window_width, window_height, road_width, stop_line_distance):
    positions = [
        (cx, 0),
        (window_width - 1, cy),
        (0, cy),
    ]
    stop_lines = [
        (cx, cy - stop_line_distance),
        (cx + stop_line_distance, cy),
        (cx - stop_line_distance, cy),
    ]
    center_lines = [
        ((cx, 0), (cx, cy - stop_line_distance)),
        ((cx + stop_line_distance, cy), (window_width - 1, cy)),
        ((cx - stop_line_distance, cy), (0, cy)),
    ]
    arms = [
        ArmGeometry(
            name=_arm_name(index, 3),
            position=positions[index],
            stop_line_point=stop_line_point,
            center_line=center_lines[index],
        )
        for index, stop_line_point in enumerate(stop_lines)
    ]
    road_rects = [
        (cx - road_width // 2, 0, road_width, cy),
        (0, cy - road_width // 2, window_width, road_width),
    ]
    arm_center_lines = center_lines
    return IntersectionGeometry(center=center, arms=arms, road_rects=road_rects, arm_center_lines=arm_center_lines)


def _build_two_way_intersection(center, cx, cy, window_width, window_height, road_width, stop_line_distance):
    positions = [
        (cx, 0),
        (cx, window_height - 1),
    ]
    stop_lines = [
        (cx, cy - stop_line_distance),
        (cx, cy + stop_line_distance),
    ]
    center_lines = [
        ((cx, 0), (cx, cy - stop_line_distance)),
        ((cx, cy + stop_line_distance), (cx, window_height - 1)),
    ]
    arms = [
        ArmGeometry(
            name=_arm_name(index, 2),
            position=positions[index],
            stop_line_point=stop_line_point,
            center_line=center_lines[index],
        )
        for index, stop_line_point in enumerate(stop_lines)
    ]
    road_rects = [
        (cx - road_width // 2, 0, road_width, window_height),
    ]
    arm_center_lines = center_lines
    return IntersectionGeometry(center=center, arms=arms, road_rects=road_rects, arm_center_lines=arm_center_lines)


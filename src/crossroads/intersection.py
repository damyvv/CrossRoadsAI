from dataclasses import dataclass


@dataclass(frozen=True)
class ArmGeometry:
    name: str
    position: tuple[int, int]
    stop_line_point: tuple[int, int]


@dataclass(frozen=True)
class IntersectionGeometry:
    center: tuple[int, int]
    arms: list[ArmGeometry]
    road_rects: list[tuple[int, int, int, int]]


def _arm_name(index: int, arm_count: int) -> str:
    if arm_count == 4:
        return ["N", "E", "S", "W"][index]
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
    positions = [
        (cx, 0),
        (window_width, cy),
        (cx, window_height),
        (0, cy),
    ]
    stop_lines = [
        (cx, cy - stop_line_distance),
        (cx + stop_line_distance, cy),
        (cx, cy + stop_line_distance),
        (cx - stop_line_distance, cy),
    ]

    if arm_count == 4:
        arms = [
            ArmGeometry(
                name=_arm_name(index, arm_count),
                position=positions[index],
                stop_line_point=stop_line_point,
            )
            for index, stop_line_point in enumerate(stop_lines)
        ]
        road_rects = [
            (cx - road_width // 2, 0, road_width, window_height),
            (0, cy - road_width // 2, window_width, road_width),
        ]
        return IntersectionGeometry(center=center, arms=arms, road_rects=road_rects)

    if arm_count < 2:
        raise ValueError("arm_count must be at least 2")

    # Fallback for non-cardinal layouts: place stop-lines uniformly on a circle.
    # Uses integer rounding to keep rendering coordinates pixel-aligned.
    import math

    arms = []
    for index in range(arm_count):
        angle = math.radians(-90 + index * 360 / arm_count)
        stop_line_point = (
            int(round(cx + stop_line_distance * math.cos(angle))),
            int(round(cy + stop_line_distance * math.sin(angle))),
        )
        arm_position = (
            int(round(cx + max(cx, cy) * math.cos(angle))),
            int(round(cy + max(cx, cy) * math.sin(angle))),
        )
        arms.append(
            ArmGeometry(name=_arm_name(index, arm_count), position=arm_position, stop_line_point=stop_line_point)
        )
    road_rects = [
        (cx - road_width // 2, 0, road_width, window_height),
        (0, cy - road_width // 2, window_width, road_width),
    ]
    return IntersectionGeometry(center=center, arms=arms, road_rects=road_rects)

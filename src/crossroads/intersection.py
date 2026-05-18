from dataclasses import dataclass


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

    if arm_count == 4:
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
            ((cx, cy - stop_line_distance - 100), (cx, cy + stop_line_distance + 100)),
            ((cx - stop_line_distance - 100, cy), (cx + stop_line_distance + 100, cy)),
            ((cx, cy - stop_line_distance - 100), (cx, cy + stop_line_distance + 100)),
            ((cx - stop_line_distance - 100, cy), (cx + stop_line_distance + 100, cy)),
        ]
        arms = [
            ArmGeometry(
                name=_arm_name(index, arm_count),
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

    if arm_count < 2:
        raise ValueError("arm_count must be at least 2")

    # For non-cardinal layouts: place stop-lines uniformly on a circle.
    # arm_count > 4 is not yet fully supported; roads are only defined for 4-arm layout.
    import math

    arms = []
    arm_center_lines = []
    for index in range(arm_count):
        angle = math.radians(-90 + index * 360 / arm_count)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        stop_line_point = (
            int(round(cx + stop_line_distance * cos_a)),
            int(round(cy + stop_line_distance * sin_a)),
        )

        # Clamp arm position to window bounds
        max_radius = max(abs(cx), abs(cy))
        arm_position = (
            max(0, min(window_width - 1, int(round(cx + max_radius * cos_a)))),
            max(0, min(window_height - 1, int(round(cy + max_radius * sin_a)))),
        )

        center_line = (stop_line_point, arm_position)
        arms.append(
            ArmGeometry(name=_arm_name(index, arm_count), position=arm_position, stop_line_point=stop_line_point, center_line=center_line)
        )
        arm_center_lines.append(center_line)

    road_rects = []
    return IntersectionGeometry(center=center, arms=arms, road_rects=road_rects, arm_center_lines=arm_center_lines)

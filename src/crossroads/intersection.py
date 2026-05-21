from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ArmGeometry:
    name: str
    position: tuple[int, int]
    stop_line: tuple[tuple[int, int], tuple[int, int]]
    center_line: tuple[tuple[int, int], tuple[int, int]]


@dataclass(frozen=True)
class IntersectionGeometry:
    center: tuple[int, int]
    arms: list[ArmGeometry]
    road_rects: list[tuple[int, int, int, int]]
    arm_center_lines: list[tuple[tuple[int, int], tuple[int, int]]]


@dataclass(frozen=True)
class IntersectionTopology:
    arm_count: int
    arm_names: list[str]
    arm_specs: list[dict]
    road_rects_fn: Callable[[int, int, int, int, int], list[tuple[int, int, int, int]]]


# Topology specifications for supported intersections
_TOPOLOGIES = {
    2: IntersectionTopology(
        arm_count=2,
        arm_names=["N", "S"],
        arm_specs=[
            {"dx": 0, "dy": -1, "position_offset": (0, 0)},
            {"dx": 0, "dy": 1, "position_offset": (0, 0)},
        ],
        road_rects_fn=lambda cx, cy, window_width, window_height, road_width: [
            (cx - road_width // 2, 0, road_width, window_height),
        ],
    ),
    4: IntersectionTopology(
        arm_count=4,
        arm_names=["N", "E", "S", "W"],
        arm_specs=[
            {"dx": 0, "dy": -1, "position_offset": (0, 0)},
            {"dx": 1, "dy": 0, "position_offset": (0, 0)},
            {"dx": 0, "dy": 1, "position_offset": (0, 0)},
            {"dx": -1, "dy": 0, "position_offset": (0, 0)},
        ],
        road_rects_fn=lambda cx, cy, window_width, window_height, road_width: [
            (cx - road_width // 2, 0, road_width, window_height),
            (0, cy - road_width // 2, window_width, road_width),
        ],
    ),
}

_CARDINAL_ARM_ORDER = ("N", "E", "S", "W")
_ARM_DIRECTION = {
    "N": (0, -1),
    "E": (1, 0),
    "S": (0, 1),
    "W": (-1, 0),
}


def build_intersection_geometry(
    *,
    window_width: int,
    window_height: int,
    arm_count: int,
    missing_arm: str | None = None,
    road_width: int,
    stop_line_distance: int,
) -> IntersectionGeometry:
    if arm_count not in {2, 3, 4}:
        raise ValueError("arm_count must be 2, 3, or 4")
    if arm_count == 3:
        if missing_arm is None:
            raise ValueError("missing_arm is required when arm_count is 3")
        if missing_arm not in _CARDINAL_ARM_ORDER:
            raise ValueError("missing_arm must be one of: N, E, S, W")
    elif missing_arm is not None:
        raise ValueError("missing_arm is only supported when arm_count is 3")

    center = (window_width // 2, window_height // 2)
    cx, cy = center
    arm_names = _resolve_arm_names(arm_count=arm_count, missing_arm=missing_arm)

    arms = []
    center_lines = []

    for name in arm_names:
        dx, dy = _ARM_DIRECTION[name]

        stop_line_center = (
            cx + dx * stop_line_distance,
            cy + dy * stop_line_distance,
        )

        position = _compute_arm_position(
            cx, cy, dx, dy, window_width, window_height
        )

        center_line = (position, stop_line_center)

        stop_line = _compute_stop_line(stop_line_center, dx, dy, road_width)

        arms.append(
            ArmGeometry(
                name=name,
                position=position,
                stop_line=stop_line,
                center_line=center_line,
            )
        )
        center_lines.append(center_line)

    road_rects = _build_road_rects(
        arm_count=arm_count,
        missing_arm=missing_arm,
        cx=cx,
        cy=cy,
        window_width=window_width,
        window_height=window_height,
        road_width=road_width,
    )

    return IntersectionGeometry(
        center=center,
        arms=arms,
        road_rects=road_rects,
        arm_center_lines=center_lines,
    )


def _resolve_arm_names(*, arm_count: int, missing_arm: str | None) -> list[str]:
    if arm_count == 4:
        return list(_CARDINAL_ARM_ORDER)
    if arm_count == 3:
        assert missing_arm is not None
        return [arm for arm in _CARDINAL_ARM_ORDER if arm != missing_arm]
    return ["N", "S"]


def _build_road_rects(
    *,
    arm_count: int,
    missing_arm: str | None,
    cx: int,
    cy: int,
    window_width: int,
    window_height: int,
    road_width: int,
) -> list[tuple[int, int, int, int]]:
    if arm_count in _TOPOLOGIES:
        return _TOPOLOGIES[arm_count].road_rects_fn(
            cx, cy, window_width, window_height, road_width
        )

    assert missing_arm is not None
    vertical_full = (cx - road_width // 2, 0, road_width, window_height)
    horizontal_full = (0, cy - road_width // 2, window_width, road_width)

    if missing_arm == "N":
        return [
            (cx - road_width // 2, cy, road_width, window_height - cy),
            horizontal_full,
        ]
    if missing_arm == "S":
        return [
            (cx - road_width // 2, 0, road_width, cy),
            horizontal_full,
        ]
    if missing_arm == "E":
        return [
            vertical_full,
            (0, cy - road_width // 2, cx, road_width),
        ]
    return [
        vertical_full,
        (cx, cy - road_width // 2, window_width - cx, road_width),
    ]


def _compute_arm_position(
    cx: int, cy: int, dx: int, dy: int, window_width: int, window_height: int
) -> tuple[int, int]:
    """Compute arm endpoint position based on direction."""
    if dx == 0:
        return (cx, 0 if dy < 0 else window_height - 1)
    return (0 if dx < 0 else window_width - 1, cy)


def _compute_stop_line(
    center_point: tuple[int, int], dx: int, dy: int, road_width: int
) -> tuple[tuple[int, int], tuple[int, int]]:
    """Compute stop line from center of road to right edge.
    
    Right side is perpendicular to traffic direction:
    - North (dy=-1): right is West (x-)
    - East (dx=1): right is North (y-)
    - South (dy=1): right is East (x+)
    - West (dx=-1): right is South (y+)
    """
    cx, cy = center_point
    half_width = road_width // 2

    if dy != 0:
        # Vertical traffic (N/S): right is perpendicular on x-axis
        center_point_line = (cx, cy)
        right_point = (cx - half_width, cy) if dy < 0 else (cx + half_width, cy)
    else:
        # Horizontal traffic (E/W): right is perpendicular on y-axis
        center_point_line = (cx, cy)
        right_point = (cx, cy - half_width) if dx > 0 else (cx, cy + half_width)

    return (center_point_line, right_point)

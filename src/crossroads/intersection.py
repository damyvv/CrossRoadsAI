from dataclasses import dataclass
from typing import Callable


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
    3: IntersectionTopology(
        arm_count=3,
        arm_names=["N", "E", "W"],
        arm_specs=[
            {"dx": 0, "dy": -1, "position_offset": (0, 0)},
            {"dx": 1, "dy": 0, "position_offset": (0, 0)},
            {"dx": -1, "dy": 0, "position_offset": (0, 0)},
        ],
        road_rects_fn=lambda cx, cy, window_width, window_height, road_width: [
            (cx - road_width // 2, 0, road_width, cy),
            (0, cy - road_width // 2, window_width, road_width),
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


def build_intersection_geometry(
    *,
    window_width: int,
    window_height: int,
    arm_count: int,
    road_width: int,
    stop_line_distance: int,
) -> IntersectionGeometry:
    if arm_count not in _TOPOLOGIES:
        raise ValueError("arm_count must be 2, 3, or 4")

    center = (window_width // 2, window_height // 2)
    cx, cy = center
    topology = _TOPOLOGIES[arm_count]

    arms = []
    center_lines = []

    for index, arm_spec in enumerate(topology.arm_specs):
        dx, dy = arm_spec["dx"], arm_spec["dy"]
        name = topology.arm_names[index]

        stop_line_point = (
            cx + dx * stop_line_distance,
            cy + dy * stop_line_distance,
        )

        position = _compute_arm_position(
            cx, cy, dx, dy, window_width, window_height
        )

        center_line = (position, stop_line_point)

        arms.append(
            ArmGeometry(
                name=name,
                position=position,
                stop_line_point=stop_line_point,
                center_line=center_line,
            )
        )
        center_lines.append(center_line)

    road_rects = topology.road_rects_fn(
        cx, cy, window_width, window_height, road_width
    )

    return IntersectionGeometry(
        center=center,
        arms=arms,
        road_rects=road_rects,
        arm_center_lines=center_lines,
    )


def _compute_arm_position(
    cx: int, cy: int, dx: int, dy: int, window_width: int, window_height: int
) -> tuple[int, int]:
    """Compute arm endpoint position based on direction."""
    if dx == 0:
        return (cx, 0 if dy < 0 else window_height - 1)
    return (0 if dx < 0 else window_width - 1, cy)


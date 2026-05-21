from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import cos, pi, sin

from crossroads.intersection import ArmGeometry, IntersectionGeometry
from crossroads.vehicle import lane_center_world_position

_CARDINAL_ARM_ORDER = ("N", "E", "S", "W")
_TURN_SEGMENTS = 16
_VALID_MOVEMENTS = {"left", "straight", "right"}


@dataclass(frozen=True)
class LanePath:
    target_arm: str
    target_outbound_lane_index: int
    points: tuple[tuple[float, float], ...]


def precompute_lane_paths(
    *,
    geometry: IntersectionGeometry,
    inbound_lanes_by_arm: Mapping[str, Sequence[object]],
    outbound_lane_count_by_arm: Mapping[str, int],
    window_width: int,
    window_height: int,
    lane_width: float,
) -> dict[tuple[str, int, str], LanePath]:
    if lane_width <= 0:
        raise ValueError("lane_width must be positive")
    arms_by_name = {arm.name: arm for arm in geometry.arms}
    missing_arms = sorted(set(inbound_lanes_by_arm) - set(arms_by_name))
    if missing_arms:
        raise ValueError(f"inbound_lanes_by_arm has unknown arms: {missing_arms!r}")

    paths: dict[tuple[str, int, str], LanePath] = {}
    for source_arm, lane_defs in inbound_lanes_by_arm.items():
        if source_arm not in outbound_lane_count_by_arm:
            raise ValueError(f"missing outbound lane count for arm {source_arm!r}")
        if len(lane_defs) == 0:
            raise ValueError(f"inbound lane definitions for arm {source_arm!r} must not be empty")

        lane_indices_by_movement = _movement_lane_indices(lane_defs=lane_defs)
        for lane_index, lane_def in enumerate(lane_defs):
            movements = getattr(lane_def, "movements", None)
            if movements is None:
                raise ValueError(f"inbound lane definition for arm {source_arm!r} must define movements")
            for movement in movements:
                if movement not in _VALID_MOVEMENTS:
                    raise ValueError(f"unsupported movement for arm {source_arm!r}: {movement!r}")
                target_arm = _target_arm(source_arm=source_arm, movement=movement)
                if target_arm not in arms_by_name:
                    raise ValueError(
                        f"movement {movement!r} from arm {source_arm!r} targets missing arm {target_arm!r} in geometry"
                    )
                if target_arm not in outbound_lane_count_by_arm:
                    raise ValueError(f"missing outbound lane count for destination arm {target_arm!r}")

                target_outbound_lane_index = _target_outbound_lane_index(
                    source_lane_index=lane_index,
                    movement_lane_indices=lane_indices_by_movement[movement],
                    outbound_lane_count=outbound_lane_count_by_arm[target_arm],
                )
                points = _path_points(
                    geometry=geometry,
                    source_arm=source_arm,
                    source_lane_index=lane_index,
                    source_lane_count=len(lane_defs),
                    target_arm=target_arm,
                    target_outbound_lane_index=target_outbound_lane_index,
                    movement=movement,
                    window_width=window_width,
                    window_height=window_height,
                    lane_width=lane_width,
                    arms_by_name=arms_by_name,
                )
                paths[(source_arm, lane_index, movement)] = LanePath(
                    target_arm=target_arm,
                    target_outbound_lane_index=target_outbound_lane_index,
                    points=points,
                )
    return paths


def _movement_lane_indices(*, lane_defs: Sequence[object]) -> dict[str, tuple[int, ...]]:
    result = {"left": [], "straight": [], "right": []}
    for lane_index, lane_def in enumerate(lane_defs):
        for movement in getattr(lane_def, "movements", ()):
            if movement in result:
                result[movement].append(lane_index)
    # Right-aligned mapping starts from right-most turning lane.
    return {movement: tuple(sorted(indices, reverse=True)) for movement, indices in result.items()}


def _target_outbound_lane_index(
    *,
    source_lane_index: int,
    movement_lane_indices: Sequence[int],
    outbound_lane_count: int,
) -> int:
    if outbound_lane_count <= 0:
        raise ValueError("outbound_lane_count must be positive")
    rank_from_right = movement_lane_indices.index(source_lane_index)
    return max(outbound_lane_count - 1 - rank_from_right, 0)


def _path_points(
    *,
    geometry: IntersectionGeometry,
    source_arm: str,
    source_lane_index: int,
    source_lane_count: int,
    target_arm: str,
    target_outbound_lane_index: int,
    movement: str,
    window_width: int,
    window_height: int,
    lane_width: float,
    arms_by_name: Mapping[str, ArmGeometry],
) -> tuple[tuple[float, float], ...]:
    source_arm_geometry = arms_by_name[source_arm]
    source_stop_distance = _distance_for_stop_line_world_coordinate(
        arm=source_arm,
        stop_line_anchor=source_arm_geometry.stop_line[0],
        window_width=window_width,
        window_height=window_height,
    )
    start = lane_center_world_position(
        arm=source_arm,
        distance=source_stop_distance,
        window_width=window_width,
        window_height=window_height,
        road_width=1,
        lane_index=source_lane_index,
        lane_count=source_lane_count,
        lane_width=lane_width,
        inbound_lane_offset=source_arm_geometry.inbound_lane_offset,
    )

    if movement == "straight":
        end = _straight_end_point(
            source_arm=source_arm,
            target_arm=target_arm,
            target_outbound_lane_index=target_outbound_lane_index,
            lane_width=lane_width,
            geometry=geometry,
            arms_by_name=arms_by_name,
        )
        return (start, end)

    destination_lane_axis_coordinate = _destination_lane_axis_coordinate(
        target_arm=target_arm,
        target_outbound_lane_index=target_outbound_lane_index,
        lane_width=lane_width,
        geometry=geometry,
        arms_by_name=arms_by_name,
    )
    return _quarter_turn_path(start=start, target_arm=target_arm, lane_axis_coordinate=destination_lane_axis_coordinate)


def _straight_end_point(
    *,
    source_arm: str,
    target_arm: str,
    target_outbound_lane_index: int,
    lane_width: float,
    geometry: IntersectionGeometry,
    arms_by_name: Mapping[str, ArmGeometry],
) -> tuple[float, float]:
    target_axis = _destination_lane_axis_coordinate(
        target_arm=target_arm,
        target_outbound_lane_index=target_outbound_lane_index,
        lane_width=lane_width,
        geometry=geometry,
        arms_by_name=arms_by_name,
    )
    target_stop = _stop_line_distance(
        arm=target_arm,
        geometry=arms_by_name[target_arm],
        center=geometry.center,
    )

    if source_arm in {"N", "S"}:
        return (
            target_axis,
            (
                geometry.center[1] - target_stop
                if target_arm == "N"
                else geometry.center[1] + target_stop
            ),
        )
    return (
        (
            geometry.center[0] + target_stop
            if target_arm == "E"
            else geometry.center[0] - target_stop
        ),
        target_axis,
    )


def _quarter_turn_path(
    *,
    start: tuple[float, float],
    target_arm: str,
    lane_axis_coordinate: float,
) -> tuple[tuple[float, float], ...]:
    sx, sy = start
    if target_arm in {"E", "W"}:
        radius = abs(lane_axis_coordinate - sy)
        end = (sx + radius if target_arm == "E" else sx - radius, lane_axis_coordinate)
        center = (end[0], sy)
    else:
        radius = abs(lane_axis_coordinate - sx)
        end = (lane_axis_coordinate, sy - radius if target_arm == "N" else sy + radius)
        center = (sx, end[1])
    if radius == 0:
        return (start, end)

    start_angle = _angle(center=center, point=start)
    end_angle = _angle(center=center, point=end)
    return _sample_arc(center=center, radius=radius, start_angle=start_angle, end_angle=end_angle)


def _sample_arc(
    *,
    center: tuple[float, float],
    radius: float,
    start_angle: float,
    end_angle: float,
) -> tuple[tuple[float, float], ...]:
    delta = ((end_angle - start_angle) + pi) % (2.0 * pi) - pi
    if delta == -pi:
        delta = pi
    step = delta / _TURN_SEGMENTS
    return tuple(
        (
            center[0] + radius * cos(start_angle + (step * i)),
            center[1] + radius * sin(start_angle + (step * i)),
        )
        for i in range(_TURN_SEGMENTS + 1)
    )


def _destination_lane_axis_coordinate(
    *,
    target_arm: str,
    target_outbound_lane_index: int,
    lane_width: float,
    geometry: IntersectionGeometry,
    arms_by_name: Mapping[str, ArmGeometry],
) -> float:
    if target_outbound_lane_index < 0:
        raise ValueError("target_outbound_lane_index must be non-negative")
    cx, cy = geometry.center
    target_geometry = arms_by_name[target_arm]
    negative_gap, positive_gap = _carriageway_gaps(
        arm=target_arm,
        arm_geometry=target_geometry,
    )
    lane_offset = lane_width * (target_outbound_lane_index + 0.5)

    if target_arm == "N":
        return cx + positive_gap + lane_offset
    if target_arm == "S":
        return cx - negative_gap - lane_offset
    if target_arm == "E":
        return cy + positive_gap + lane_offset
    if target_arm == "W":
        return cy - negative_gap - lane_offset
    raise ValueError(f"unknown arm: {target_arm!r}")


def _carriageway_gaps(*, arm: str, arm_geometry: ArmGeometry) -> tuple[float, float]:
    separation = arm_geometry.carriageway_separation
    if arm in {"N", "E"}:
        negative_gap = float(arm_geometry.inbound_lane_offset)
        positive_gap = float(separation) - negative_gap
        return (negative_gap, positive_gap)
    if arm in {"S", "W"}:
        positive_gap = float(arm_geometry.inbound_lane_offset)
        negative_gap = float(separation) - positive_gap
        return (negative_gap, positive_gap)
    raise ValueError(f"unknown arm: {arm!r}")


def _stop_line_distance(*, arm: str, geometry: ArmGeometry, center: tuple[int, int]) -> float:
    stop_x, stop_y = geometry.stop_line[0]
    cx, cy = center
    if arm == "N":
        return float(cy - stop_y)
    if arm == "S":
        return float(stop_y - cy)
    if arm == "E":
        return float(stop_x - cx)
    if arm == "W":
        return float(cx - stop_x)
    raise ValueError(f"unknown arm: {arm!r}")


def _distance_for_stop_line_world_coordinate(
    *,
    arm: str,
    stop_line_anchor: tuple[int, int],
    window_width: int,
    window_height: int,
) -> float:
    stop_x, stop_y = stop_line_anchor
    if arm == "N":
        return float(stop_y)
    if arm == "S":
        return float((window_height - 1) - stop_y)
    if arm == "E":
        return float((window_width - 1) - stop_x)
    if arm == "W":
        return float(stop_x)
    raise ValueError(f"unknown arm: {arm!r}")


def _target_arm(*, source_arm: str, movement: str) -> str:
    source_index = _CARDINAL_ARM_ORDER.index(source_arm)
    if movement == "left":
        return _CARDINAL_ARM_ORDER[(source_index + 1) % len(_CARDINAL_ARM_ORDER)]
    if movement == "right":
        return _CARDINAL_ARM_ORDER[(source_index - 1) % len(_CARDINAL_ARM_ORDER)]
    if movement == "straight":
        return _CARDINAL_ARM_ORDER[(source_index + 2) % len(_CARDINAL_ARM_ORDER)]
    raise ValueError(f"unknown movement: {movement!r}")


def _angle(*, center: tuple[float, float], point: tuple[float, float]) -> float:
    from math import atan2

    return atan2(point[1] - center[1], point[0] - center[0])

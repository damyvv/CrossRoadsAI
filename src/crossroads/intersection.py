from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from math import ceil
from typing import Callable


@dataclass(frozen=True)
class ArmGeometry:
    name: str
    position: tuple[int, int]
    stop_line: tuple[tuple[int, int], tuple[int, int]]
    center_line: tuple[tuple[int, int], tuple[int, int]]
    carriageway_separation: int
    inbound_lane_offset: int
    outbound_lane_offset: int


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
    road_width: int | None = None,
    road_width_by_arm: Mapping[str, int] | None = None,
    inbound_lane_count_by_arm: Mapping[str, int] | None = None,
    straight_capable_lane_indices_by_arm: Mapping[str, Sequence[int]] | None = None,
    lane_width: int | None = None,
    carriageway_separation_override: int | None = None,
    outbound_lane_count: int = 2,
    outbound_lane_count_by_arm: Mapping[str, int] | None = None,
    stop_line_distance: int | Mapping[str, int],
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
    carriageway_override_component = _validated_carriageway_separation_override(
        carriageway_separation_override
    )
    arm_names = _resolve_arm_names(arm_count=arm_count, missing_arm=missing_arm)
    arm_names_set = set(arm_names)

    if road_width_by_arm is None:
        if road_width is None:
            raise ValueError("road_width or road_width_by_arm must be provided")
        road_width_by_arm = {arm: road_width for arm in arm_names}
    else:
        missing_widths = sorted(arm_names_set - set(road_width_by_arm))
        if missing_widths:
            raise ValueError(f"missing road width definitions for arms: {missing_widths!r}")
        road_width_by_arm = {arm: road_width_by_arm[arm] for arm in arm_names}

    if inbound_lane_count_by_arm is None:
        if road_width is None:
            raise ValueError("road_width is required when inbound_lane_count_by_arm is not provided")
        inbound_width_by_arm = {arm: road_width_by_arm[arm] // 2 for arm in arm_names}
        outbound_width_by_arm = {arm: road_width_by_arm[arm] // 2 for arm in arm_names}
        legacy_mode = True
        effective_carriageway_separation_by_arm = {arm: 0 for arm in arm_names}
    else:
        if lane_width is None:
            raise ValueError("lane_width is required when inbound_lane_count_by_arm is provided")
        if lane_width <= 0:
            raise ValueError("lane_width must be positive")
        missing_inbound = sorted(arm_names_set - set(inbound_lane_count_by_arm))
        if missing_inbound:
            raise ValueError(f"missing inbound lane count definitions for arms: {missing_inbound!r}")

        if outbound_lane_count_by_arm is None:
            if outbound_lane_count <= 0:
                raise ValueError("outbound_lane_count must be positive")
            resolved_outbound_lane_count_by_arm = {
                arm: outbound_lane_count for arm in arm_names
            }
        else:
            missing_outbound = sorted(arm_names_set - set(outbound_lane_count_by_arm))
            if missing_outbound:
                raise ValueError(
                    f"missing outbound lane count definitions for arms: {missing_outbound!r}"
                )
            unknown_outbound = sorted(set(outbound_lane_count_by_arm) - arm_names_set)
            if unknown_outbound:
                raise ValueError(
                    f"unknown arm in outbound lane count definitions: {unknown_outbound!r}"
                )
            resolved_outbound_lane_count_by_arm = {}
            for arm in arm_names:
                value = outbound_lane_count_by_arm[arm]
                if value <= 0:
                    raise ValueError(
                        f"outbound lane count must be positive for arm {arm!r}"
                    )
                resolved_outbound_lane_count_by_arm[arm] = value

        inbound_width_by_arm = {
            arm: inbound_lane_count_by_arm[arm] * lane_width for arm in arm_names
        }
        outbound_width_by_arm = {
            arm: resolved_outbound_lane_count_by_arm[arm] * lane_width for arm in arm_names
        }
        legacy_mode = False
        effective_carriageway_separation_by_arm = derive_carriageway_separation_by_arm(
            arm_names=arm_names,
            inbound_lane_count_by_arm=inbound_lane_count_by_arm,
            straight_capable_lane_indices_by_arm=straight_capable_lane_indices_by_arm,
            lane_width=lane_width,
            outbound_lane_count=outbound_lane_count,
            outbound_lane_count_by_arm=resolved_outbound_lane_count_by_arm,
            carriageway_separation_override=carriageway_separation_override,
        )

    if legacy_mode:
        effective_carriageway_separation_by_arm = {
            arm: carriageway_override_component for arm in arm_names
        }

    arms = []
    center_lines = []

    for name in arm_names:
        dx, dy = _ARM_DIRECTION[name]

        arm_stop = stop_line_distance[name] if isinstance(stop_line_distance, Mapping) else stop_line_distance
        stop_line_center = (
            cx + dx * arm_stop,
            cy + dy * arm_stop,
        )

        position = _compute_arm_position(
            cx, cy, dx, dy, window_width, window_height
        )

        center_line = (position, stop_line_center)

        stop_line = _compute_stop_line(
            arm_name=name,
            center_point=stop_line_center,
            dx=dx,
            dy=dy,
            inbound_width=inbound_width_by_arm[name],
            carriageway_separation=effective_carriageway_separation_by_arm[name],
            legacy_mode=legacy_mode,
            carriageway_separation_override_component=carriageway_override_component,
        )
        negative_gap, positive_gap = _split_carriageway_gap_for_arm(
            arm=name,
            carriageway_separation=effective_carriageway_separation_by_arm[name],
            legacy_mode=legacy_mode,
            carriageway_separation_override_component=carriageway_override_component,
        )
        inbound_lane_offset = negative_gap if name in {"N", "E"} else positive_gap
        outbound_lane_offset = positive_gap if name in {"N", "E"} else negative_gap

        arms.append(
            ArmGeometry(
                name=name,
                position=position,
                stop_line=stop_line,
                center_line=center_line,
                carriageway_separation=effective_carriageway_separation_by_arm[name],
                inbound_lane_offset=inbound_lane_offset,
                outbound_lane_offset=outbound_lane_offset,
            )
        )
        if effective_carriageway_separation_by_arm[name] <= 0:
            center_lines.append(center_line)

    road_rects = _build_road_rects(
        arm_count=arm_count,
        missing_arm=missing_arm,
        cx=cx,
        cy=cy,
        window_width=window_width,
        window_height=window_height,
        arm_names=arm_names,
        inbound_width_by_arm=inbound_width_by_arm,
        outbound_width_by_arm=outbound_width_by_arm,
        legacy_mode=legacy_mode,
        carriageway_separation_by_arm=effective_carriageway_separation_by_arm,
        carriageway_separation_override_component=carriageway_override_component,
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
    arm_names: Sequence[str],
    inbound_width_by_arm: Mapping[str, int],
    outbound_width_by_arm: Mapping[str, int],
    legacy_mode: bool,
    carriageway_separation_by_arm: Mapping[str, int],
    carriageway_separation_override_component: int,
    road_width: int | None,
) -> list[tuple[int, int, int, int]]:
    if legacy_mode:
        assert road_width is not None
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

    _ = (arm_count, missing_arm)
    road_rects: list[tuple[int, int, int, int]] = []
    for arm in arm_names:
        negative_gap, positive_gap = _split_carriageway_gap_for_arm(
            arm=arm,
            carriageway_separation=carriageway_separation_by_arm[arm],
            legacy_mode=legacy_mode,
            carriageway_separation_override_component=carriageway_separation_override_component,
        )
        inbound_width = inbound_width_by_arm[arm]
        outbound_width = outbound_width_by_arm[arm]
        if arm == "N":
            road_rects.append((cx - negative_gap - inbound_width, 0, inbound_width, cy))
            road_rects.append((cx + positive_gap, 0, outbound_width, cy))
        elif arm == "S":
            road_rects.append((cx - negative_gap - outbound_width, cy, outbound_width, window_height - cy))
            road_rects.append((cx + positive_gap, cy, inbound_width, window_height - cy))
        elif arm == "E":
            road_rects.append((cx, cy - negative_gap - inbound_width, window_width - cx, inbound_width))
            road_rects.append((cx, cy + positive_gap, window_width - cx, outbound_width))
        elif arm == "W":
            road_rects.append((0, cy - negative_gap - outbound_width, cx, outbound_width))
            road_rects.append((0, cy + positive_gap, cx, inbound_width))
    return road_rects


def _compute_arm_position(
    cx: int, cy: int, dx: int, dy: int, window_width: int, window_height: int
) -> tuple[int, int]:
    """Compute arm endpoint position based on direction."""
    if dx == 0:
        return (cx, 0 if dy < 0 else window_height - 1)
    return (0 if dx < 0 else window_width - 1, cy)


def _compute_stop_line(
    *,
    arm_name: str,
    center_point: tuple[int, int],
    dx: int,
    dy: int,
    inbound_width: int,
    carriageway_separation: int,
    legacy_mode: bool,
    carriageway_separation_override_component: int,
) -> tuple[tuple[int, int], tuple[int, int]]:
    """Compute stop line across inbound carriageway only.
    
    Right side is perpendicular to traffic direction:
    - North (dy=-1): right is West (x-)
    - East (dx=1): right is North (y-)
    - South (dy=1): right is East (x+)
    - West (dx=-1): right is South (y+)
    """
    cx, cy = center_point

    negative_gap, positive_gap = _split_carriageway_gap_for_arm(
        arm=arm_name,
        carriageway_separation=carriageway_separation,
        legacy_mode=legacy_mode,
        carriageway_separation_override_component=carriageway_separation_override_component,
    )

    if dy != 0:
        # Vertical traffic (N/S): right is perpendicular on x-axis
        inner_edge = cx - negative_gap if dy < 0 else cx + positive_gap
        center_point_line = (inner_edge, cy)
        right_point = (
            (inner_edge - inbound_width, cy)
            if dy < 0
            else (inner_edge + inbound_width, cy)
        )
    else:
        # Horizontal traffic (E/W): right is perpendicular on y-axis
        inner_edge = cy - negative_gap if dx > 0 else cy + positive_gap
        center_point_line = (cx, inner_edge)
        right_point = (
            (cx, inner_edge - inbound_width)
            if dx > 0
            else (cx, inner_edge + inbound_width)
        )

    return (center_point_line, right_point)


def derive_carriageway_separation_by_arm(
    *,
    arm_names: Sequence[str],
    inbound_lane_count_by_arm: Mapping[str, int],
    straight_capable_lane_indices_by_arm: Mapping[str, Sequence[int]] | None,
    lane_width: int,
    outbound_lane_count: int,
    outbound_lane_count_by_arm: Mapping[str, int] | None = None,
    carriageway_separation_override: int | None = None,
) -> dict[str, int]:
    override = _validated_carriageway_separation_override(carriageway_separation_override)
    straight_indices_by_arm = straight_capable_lane_indices_by_arm or {}

    derived_by_arm: dict[str, int] = {}
    for arm in arm_names:
        opposite_arm = _opposite_arm_name(arm)
        if opposite_arm is None or opposite_arm not in inbound_lane_count_by_arm:
            derived_by_arm[arm] = override
            continue

        inbound_lane_count = inbound_lane_count_by_arm[opposite_arm]
        straight_indices = tuple(straight_indices_by_arm.get(opposite_arm, ()))
        _validate_straight_lane_indices(
            arm=opposite_arm,
            inbound_lane_count=inbound_lane_count,
            straight_lane_indices=straight_indices,
        )
        arm_outbound_lane_count = (
            outbound_lane_count
            if outbound_lane_count_by_arm is None
            else outbound_lane_count_by_arm[arm]
        )
        auto_baseline = _auto_carriageway_separation_for_arm(
            straight_lane_indices=straight_indices,
            lane_width=lane_width,
            outbound_lane_count=arm_outbound_lane_count,
        )
        derived_by_arm[arm] = auto_baseline + override
    return derived_by_arm


def _auto_carriageway_separation_for_arm(
    *,
    straight_lane_indices: Sequence[int],
    lane_width: int,
    outbound_lane_count: int,
) -> int:
    straight_lane_count = len(straight_lane_indices)
    if straight_lane_count == 0:
        inbound_reference = 0.5
        outbound_reference = outbound_lane_count - 0.5
    elif outbound_lane_count > straight_lane_count:
        inbound_reference = max(straight_lane_indices) + 0.5
        outbound_reference = outbound_lane_count - 0.5
    else:
        inbound_reference = sum(index + 0.5 for index in straight_lane_indices) / straight_lane_count
        outbound_reference = outbound_lane_count / 2.0

    required = 2.0 * lane_width * (inbound_reference - outbound_reference)
    return max(0, int(ceil(required)))


def _opposite_arm_name(arm: str) -> str | None:
    if arm == "N":
        return "S"
    if arm == "S":
        return "N"
    if arm == "E":
        return "W"
    if arm == "W":
        return "E"
    return None


def _validated_carriageway_separation_override(
    carriageway_separation_override: int | None,
) -> int:
    if carriageway_separation_override is None:
        return 0
    if carriageway_separation_override < 0:
        raise ValueError("carriageway_separation must be >= 0")
    return carriageway_separation_override


def _validate_straight_lane_indices(
    *,
    arm: str,
    inbound_lane_count: int,
    straight_lane_indices: Sequence[int],
) -> None:
    seen: set[int] = set()
    for lane_index in straight_lane_indices:
        if lane_index in seen:
            raise ValueError(f"duplicate straight-capable lane index for arm {arm}: {lane_index}")
        seen.add(lane_index)
        if lane_index < 0 or lane_index >= inbound_lane_count:
            raise ValueError(
                f"straight-capable lane index out of range for arm {arm}: {lane_index}"
            )


def _split_carriageway_gap(carriageway_separation: int) -> tuple[int, int]:
    negative_side_gap = carriageway_separation // 2
    positive_side_gap = carriageway_separation - negative_side_gap
    return (negative_side_gap, positive_side_gap)


def _split_carriageway_gap_for_arm(
    *,
    arm: str,
    carriageway_separation: int,
    legacy_mode: bool,
    carriageway_separation_override_component: int = 0,
) -> tuple[int, int]:
    if carriageway_separation_override_component < 0:
        raise ValueError("carriageway_separation_override_component must be >= 0")
    if carriageway_separation_override_component > carriageway_separation:
        raise ValueError(
            "carriageway_separation_override_component cannot exceed carriageway_separation"
        )

    negative_gap, positive_gap = _split_carriageway_gap(carriageway_separation)
    if legacy_mode:
        return (negative_gap, positive_gap)

    baseline_component = carriageway_separation - carriageway_separation_override_component
    baseline_negative_gap, baseline_positive_gap = _split_carriageway_gap(
        baseline_component
    )
    override_negative_gap, override_positive_gap = _split_carriageway_gap(
        carriageway_separation_override_component
    )

    if arm in {"N", "E"}:
        # Keep inbound affected by explicit override only.
        # Apply auto baseline half-gap on outbound side.
        return (
            override_negative_gap,
            baseline_positive_gap + override_positive_gap,
        )
    if arm in {"S", "W"}:
        # Keep inbound affected by explicit override only.
        # Apply auto baseline half-gap on outbound side.
        return (
            baseline_negative_gap + override_negative_gap,
            override_positive_gap,
        )
    return (negative_gap, positive_gap)


def compute_road_width_from_inbound_lanes(
    *,
    inbound_lanes_by_arm: Mapping[str, Sequence[object]],
    lane_width: int,
    outbound_lane_count: int = 2,
    outbound_lane_count_by_arm: Mapping[str, int] | None = None,
) -> int:
    return max(
        compute_road_width_by_arm_from_inbound_lanes(
            inbound_lanes_by_arm=inbound_lanes_by_arm,
            lane_width=lane_width,
            outbound_lane_count=outbound_lane_count,
            outbound_lane_count_by_arm=outbound_lane_count_by_arm,
        ).values()
    )


def compute_road_width_by_arm_from_inbound_lanes(
    *,
    inbound_lanes_by_arm: Mapping[str, Sequence[object]],
    lane_width: int,
    outbound_lane_count: int = 2,
    outbound_lane_count_by_arm: Mapping[str, int] | None = None,
) -> dict[str, int]:
    if lane_width <= 0:
        raise ValueError("lane_width must be positive")
    if not inbound_lanes_by_arm:
        raise ValueError("inbound_lanes_by_arm must not be empty")
    for arm, lanes in inbound_lanes_by_arm.items():
        if len(lanes) <= 0:
            raise ValueError(f"each arm must define at least one inbound lane: {arm}")

    if outbound_lane_count_by_arm is None:
        if outbound_lane_count <= 0:
            raise ValueError("outbound_lane_count must be positive")
        resolved_outbound_lane_count_by_arm = {
            arm: outbound_lane_count for arm in inbound_lanes_by_arm
        }
    else:
        inbound_arms = set(inbound_lanes_by_arm)
        missing_outbound = sorted(inbound_arms - set(outbound_lane_count_by_arm))
        if missing_outbound:
            raise ValueError(
                f"missing outbound lane count definitions for arms: {missing_outbound!r}"
            )
        unknown_outbound = sorted(set(outbound_lane_count_by_arm) - inbound_arms)
        if unknown_outbound:
            raise ValueError(
                f"unknown arm in outbound lane count definitions: {unknown_outbound!r}"
            )
        resolved_outbound_lane_count_by_arm = {}
        for arm in inbound_lanes_by_arm:
            value = outbound_lane_count_by_arm[arm]
            if value <= 0:
                raise ValueError(f"outbound lane count must be positive for arm {arm!r}")
            resolved_outbound_lane_count_by_arm[arm] = value

    return {
        arm: (len(lanes) + resolved_outbound_lane_count_by_arm[arm]) * lane_width
        for arm, lanes in inbound_lanes_by_arm.items()
    }


def compute_outbound_lane_count_by_arm_from_inbound_lanes(
    *,
    inbound_lanes_by_arm: Mapping[str, Sequence[object]],
    minimum_outbound_lane_count: int = 1,
) -> dict[str, int]:
    if not inbound_lanes_by_arm:
        raise ValueError("inbound_lanes_by_arm must not be empty")
    if minimum_outbound_lane_count <= 0:
        raise ValueError("minimum_outbound_lane_count must be positive")

    arm_names = set(inbound_lanes_by_arm)

    def _neighbor_arm(name: str, *, offset: int) -> str | None:
        index = _CARDINAL_ARM_ORDER.index(name)
        candidate = _CARDINAL_ARM_ORDER[(index + offset) % len(_CARDINAL_ARM_ORDER)]
        return candidate if candidate in arm_names else None

    def _count_lanes_with_movement(arm: str | None, movement: str) -> int:
        if arm is None:
            return 0
        count = 0
        for lane in inbound_lanes_by_arm[arm]:
            movements = getattr(lane, "movements", None)
            if movements is None:
                raise ValueError(
                    f"inbound lane definition for arm {arm!r} must define movements"
                )
            if movement in movements:
                count += 1
        return count

    outbound_lane_count_by_arm: dict[str, int] = {}
    for arm in inbound_lanes_by_arm:
        clockwise_arm = _neighbor_arm(arm, offset=1)
        counterclockwise_arm = _neighbor_arm(arm, offset=-1)
        opposite_arm = _neighbor_arm(arm, offset=2)
        outbound_lane_count_by_arm[arm] = max(
            minimum_outbound_lane_count,
            _count_lanes_with_movement(clockwise_arm, "right"),
            _count_lanes_with_movement(counterclockwise_arm, "left"),
            _count_lanes_with_movement(opposite_arm, "straight"),
        )

    return outbound_lane_count_by_arm

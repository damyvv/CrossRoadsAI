import pytest

from crossroads.config import ROAD_WIDTH, STOP_LINE_DISTANCE, WINDOW_HEIGHT, WINDOW_WIDTH
from crossroads.intersection import (
    build_intersection_geometry,
    compute_outbound_lane_count_by_arm_from_inbound_lanes,
    compute_road_width_by_arm_from_inbound_lanes,
    compute_road_width_from_inbound_lanes,
)
from crossroads.vehicle import lane_center_world_position


class _Lane:
    def __init__(self, *movements: str) -> None:
        self.movements = movements


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


def test_compute_road_width_by_arm_from_inbound_lanes_supports_per_arm_outbound_lanes():
    assert compute_road_width_by_arm_from_inbound_lanes(
        inbound_lanes_by_arm={
            "N": (object(), object(), object()),
            "E": (object(),),
        },
        lane_width=12,
        outbound_lane_count_by_arm={"N": 4, "E": 2},
    ) == {
        "N": 84,
        "E": 36,
    }


def test_compute_outbound_lane_count_by_arm_from_inbound_lanes_uses_neighbor_movements():
    outbound_lane_count_by_arm = compute_outbound_lane_count_by_arm_from_inbound_lanes(
        inbound_lanes_by_arm={
            "N": (_Lane("left"), _Lane("straight"), _Lane("straight")),
            "E": (_Lane("right"), _Lane("right"), _Lane("right")),
            "S": (_Lane("straight"), _Lane("straight"), _Lane("left")),
            "W": (_Lane("left"),),
        }
    )

    assert outbound_lane_count_by_arm == {
        "N": 3,  # max(E right=3, W left=1, S straight=2)
        "E": 1,  # max(S right=0, N left=1, W straight=0)
        "S": 2,  # max(W right=0, E left=0, N straight=2)
        "W": 1,  # max(N right=0, S left=1, E straight=0)
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
        stop_line_distance=0,
    )

    cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
    north_arm = geometry.arms[0]
    south_arm = geometry.arms[2]
    # Auto base for N/S: max E/W extent = max(inbound_E=24, outbound_E=24, ...) = 24
    ns_base = 24
    assert north_arm.center_line[1] == (cx, cy - ns_base)
    assert south_arm.center_line[1] == (cx, cy + ns_base)
    # N inbound is west side, length = 5 lanes * lane_width.
    assert north_arm.stop_line == (
        (cx, cy - ns_base),
        (cx - (5 * lane_width), cy - ns_base),
    )
    # S inbound is east side, length = 3 lanes * lane_width.
    assert south_arm.stop_line == (
        (cx, cy + ns_base),
        (cx + (3 * lane_width), cy + ns_base),
    )


def test_build_intersection_geometry_rejects_negative_carriageway_separation():
    with pytest.raises(ValueError, match="carriageway_separation must be >= 0"):
        build_intersection_geometry(
            window_width=WINDOW_WIDTH,
            window_height=WINDOW_HEIGHT,
            arm_count=4,
            road_width_by_arm={"N": 84, "E": 48, "S": 60, "W": 48},
            inbound_lane_count_by_arm={"N": 5, "E": 2, "S": 3, "W": 2},
            lane_width=12,
            carriageway_separation_override=-1,
            outbound_lane_count=2,
            stop_line_distance=STOP_LINE_DISTANCE,
        )


def test_build_intersection_geometry_applies_carriageway_separation_to_stop_line_span():
    lane_width = 12
    carriageway_separation = 10
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=4,
        road_width_by_arm={"N": 84, "E": 48, "S": 60, "W": 48},
        inbound_lane_count_by_arm={"N": 5, "E": 2, "S": 3, "W": 2},
        lane_width=lane_width,
        carriageway_separation_override=carriageway_separation,
        outbound_lane_count=2,
        stop_line_distance=0,
    )

    cx, cy = WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2
    north_arm = geometry.arms[0]
    south_arm = geometry.arms[2]
    expected_north_offset = (5 * lane_width) + carriageway_separation // 2
    expected_south_offset = (3 * lane_width) + carriageway_separation // 2
    # Auto base for N/S: E/W arm extent with sep=10 (all override, evenly split) = 24 + 5 = 29
    ns_base = 29

    assert north_arm.stop_line == (
        (cx - carriageway_separation // 2, cy - ns_base),
        (cx - expected_north_offset, cy - ns_base),
    )
    assert south_arm.stop_line == (
        (cx + carriageway_separation // 2, cy + ns_base),
        (cx + expected_south_offset, cy + ns_base),
    )


def test_build_intersection_geometry_auto_separation_is_per_arm_and_adds_override():
    lane_width = 12
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=4,
        road_width_by_arm={"N": 72, "E": 48, "S": 72, "W": 48},
        inbound_lane_count_by_arm={"N": 4, "E": 2, "S": 4, "W": 2},
        straight_capable_lane_indices_by_arm={
            "N": (0, 1),
            "E": (0, 1),
            "S": (2, 3),
            "W": (0, 1),
        },
        lane_width=lane_width,
        carriageway_separation_override=4,
        outbound_lane_count=2,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    by_arm = {arm.name: arm for arm in geometry.arms}
    # N baseline is driven by S straight lanes, S by N straight lanes.
    assert by_arm["N"].carriageway_separation == 52
    assert by_arm["S"].carriageway_separation == 4
    assert by_arm["E"].carriageway_separation == 4
    assert by_arm["W"].carriageway_separation == 4


def test_build_intersection_geometry_right_aligns_when_outbound_exceeds_opposite_straight():
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=4,
        road_width_by_arm={"N": 96, "E": 48, "S": 72, "W": 48},
        inbound_lane_count_by_arm={"N": 4, "E": 2, "S": 4, "W": 2},
        straight_capable_lane_indices_by_arm={
            "N": (0, 1),
            "E": (0, 1),
            "S": (2, 3),
            "W": (0, 1),
        },
        lane_width=12,
        carriageway_separation_override=0,
        outbound_lane_count_by_arm={"N": 4, "E": 2, "S": 2, "W": 2},
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    by_arm = {arm.name: arm for arm in geometry.arms}
    assert by_arm["N"].carriageway_separation == 0


@pytest.mark.parametrize("carriageway_separation_override", [0, 40])
def test_south_straight_lane_aligns_with_north_outbound_rightmost_lane(
    carriageway_separation_override: int,
):
    lane_width = 20
    inbound_lanes_by_arm = {
        "N": (
            _Lane("left"),
            _Lane("left"),
            _Lane("straight"),
            _Lane("straight"),
            _Lane("straight"),
            _Lane("right"),
        ),
        "E": (_Lane("left", "straight"), _Lane("straight", "right")),
        "S": (_Lane("left", "straight", "right"),),
        "W": (_Lane("left", "straight"), _Lane("straight", "right")),
    }
    outbound_lane_count_by_arm = compute_outbound_lane_count_by_arm_from_inbound_lanes(
        inbound_lanes_by_arm=inbound_lanes_by_arm
    )
    road_width_by_arm = compute_road_width_by_arm_from_inbound_lanes(
        inbound_lanes_by_arm=inbound_lanes_by_arm,
        lane_width=lane_width,
        outbound_lane_count_by_arm=outbound_lane_count_by_arm,
    )
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=4,
        road_width_by_arm=road_width_by_arm,
        inbound_lane_count_by_arm={arm: len(lanes) for arm, lanes in inbound_lanes_by_arm.items()},
        straight_capable_lane_indices_by_arm={
            arm: tuple(i for i, lane in enumerate(lanes) if "straight" in lane.movements)
            for arm, lanes in inbound_lanes_by_arm.items()
        },
        lane_width=lane_width,
        carriageway_separation_override=carriageway_separation_override,
        outbound_lane_count_by_arm=outbound_lane_count_by_arm,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    by_arm = {arm.name: arm for arm in geometry.arms}
    south_straight_x, _ = lane_center_world_position(
        arm="S",
        distance=0.0,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        road_width=max(road_width_by_arm.values()),
        lane_index=0,
        lane_count=1,
        lane_width=lane_width,
        inbound_lane_offset=by_arm["S"].inbound_lane_offset,
    )

    cx = WINDOW_WIDTH // 2
    north_neg_gap = by_arm["N"].carriageway_separation // 2
    north_pos_gap = by_arm["N"].carriageway_separation - north_neg_gap
    north_outbound_rightmost_x = cx + north_pos_gap + (lane_width / 2.0)
    assert south_straight_x == north_outbound_rightmost_x


def test_build_intersection_geometry_skips_auto_alignment_when_no_straight_lanes():
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=4,
        road_width_by_arm={"N": 72, "E": 48, "S": 72, "W": 48},
        inbound_lane_count_by_arm={"N": 4, "E": 2, "S": 4, "W": 2},
        straight_capable_lane_indices_by_arm={
            "N": (),
            "E": (0, 1),
            "S": (),
            "W": (0, 1),
        },
        lane_width=12,
        carriageway_separation_override=0,
        outbound_lane_count=2,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    by_arm = {arm.name: arm for arm in geometry.arms}
    assert by_arm["N"].carriageway_separation == 0
    assert by_arm["S"].carriageway_separation == 0


def test_build_intersection_geometry_removes_centerline_only_for_separated_arms():
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=4,
        road_width_by_arm={"N": 72, "E": 48, "S": 72, "W": 48},
        inbound_lane_count_by_arm={"N": 4, "E": 2, "S": 4, "W": 2},
        straight_capable_lane_indices_by_arm={
            "N": (0, 1),
            "E": (0, 1),
            "S": (2, 3),
            "W": (0, 1),
        },
        lane_width=12,
        carriageway_separation_override=0,
        outbound_lane_count=2,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    # Only N has positive separation in this setup.
    assert len(geometry.arm_center_lines) == 3


# ---------------------------------------------------------------------------
# Auto Stop Line Base / Intersection Rectangle tests
# ---------------------------------------------------------------------------

def test_stop_line_base_auto_aligns_with_perpendicular_arm_edges():
    """N/S stop lines land at outer edge of E/W roads; E/W at outer edge of N/S roads."""
    lane_width = 10
    # 2 inbound + 2 outbound per arm, no carriageway separation → arm extent = 20
    geometry = build_intersection_geometry(
        window_width=200,
        window_height=200,
        arm_count=4,
        road_width_by_arm={"N": 40, "E": 40, "S": 40, "W": 40},
        inbound_lane_count_by_arm={"N": 2, "E": 2, "S": 2, "W": 2},
        outbound_lane_count=2,
        lane_width=lane_width,
        stop_line_distance=0,
    )

    cx, cy = 100, 100
    by_arm = {arm.name: arm for arm in geometry.arms}
    assert by_arm["N"].stop_line[0][1] == cy - 20
    assert by_arm["S"].stop_line[0][1] == cy + 20
    assert by_arm["E"].stop_line[0][0] == cx + 20
    assert by_arm["W"].stop_line[0][0] == cx - 20


def test_stop_line_base_uses_half_of_widest_perpendicular_arm_physical_width():
    """E/W base = widest N/S arm total physical width // 2 (not max of a single-side extent)."""
    lane_width = 10
    # N: 1 inbound (10) + 3 outbound (30), sep=0 → total physical width = 40
    # S: 1 inbound (10) + 1 outbound (10), sep=0 → total = 20
    # E/W: 1 inbound + 1 outbound → total = 20
    geometry = build_intersection_geometry(
        window_width=200,
        window_height=200,
        arm_count=4,
        road_width_by_arm={"N": 40, "E": 20, "S": 20, "W": 20},
        inbound_lane_count_by_arm={"N": 1, "E": 1, "S": 1, "W": 1},
        outbound_lane_count_by_arm={"N": 3, "E": 1, "S": 1, "W": 1},
        lane_width=lane_width,
        stop_line_distance=0,
    )

    cx, cy = 100, 100
    by_arm = {arm.name: arm for arm in geometry.arms}
    # E/W base = max(N_total=40, S_total=20) // 2 = 20  (gap = 40 = N arm width)
    assert by_arm["E"].stop_line[0][0] == cx + 20
    assert by_arm["W"].stop_line[0][0] == cx - 20
    assert geometry.effective_stop_line_distance_by_arm["E"] + geometry.effective_stop_line_distance_by_arm["W"] == 40
    # N/S base = max(E_total=20, W_total=20) // 2 = 10
    assert by_arm["N"].stop_line[0][1] == cy - 10
    assert by_arm["S"].stop_line[0][1] == cy + 10


def test_stop_line_distance_adds_as_offset_on_top_of_auto_base():
    """stop_line_distance is an extra offset added to the auto-calculated base."""
    lane_width = 10
    geometry = build_intersection_geometry(
        window_width=200,
        window_height=200,
        arm_count=4,
        road_width_by_arm={"N": 40, "E": 40, "S": 40, "W": 40},
        inbound_lane_count_by_arm={"N": 2, "E": 2, "S": 2, "W": 2},
        outbound_lane_count=2,
        lane_width=lane_width,
        stop_line_distance=15,
    )

    cx, cy = 100, 100
    by_arm = {arm.name: arm for arm in geometry.arms}
    # Auto base = 20, offset = 15 → effective = 35
    assert by_arm["N"].stop_line[0][1] == cy - 35
    assert by_arm["S"].stop_line[0][1] == cy + 35
    assert by_arm["E"].stop_line[0][0] == cx + 35
    assert by_arm["W"].stop_line[0][0] == cx - 35


def test_stop_line_per_arm_mapping_overrides_global_offset():
    """A per-arm mapping overrides the global offset for that arm; auto base still applies."""
    lane_width = 10
    geometry = build_intersection_geometry(
        window_width=200,
        window_height=200,
        arm_count=4,
        road_width_by_arm={"N": 40, "E": 40, "S": 40, "W": 40},
        inbound_lane_count_by_arm={"N": 2, "E": 2, "S": 2, "W": 2},
        outbound_lane_count=2,
        lane_width=lane_width,
        stop_line_distance={"N": 5, "E": 0, "S": 5, "W": 0},
    )

    cx, cy = 100, 100
    by_arm = {arm.name: arm for arm in geometry.arms}
    # Auto base = 20; N/S get +5, E/W get +0
    assert by_arm["N"].stop_line[0][1] == cy - 25
    assert by_arm["S"].stop_line[0][1] == cy + 25
    assert by_arm["E"].stop_line[0][0] == cx + 20
    assert by_arm["W"].stop_line[0][0] == cx - 20


def test_stop_line_base_three_arm_uses_only_existing_perpendicular_arms():
    """3-arm intersection: E/W base uses only S (no N); S base uses both E and W."""
    lane_width = 10
    # S: 3 inbound (30) + 2 outbound (20) → total physical width = 50
    # E/W: 1 inbound (10) + 1 outbound (10) → total = 20
    # E/W base = max(S_total=50) // 2 = 25 → E<->W gap = 50 = S arm width
    # S base from E/W: total = 20 → 20 // 2 = 10
    geometry = build_intersection_geometry(
        window_width=200,
        window_height=200,
        arm_count=3,
        missing_arm="N",
        road_width_by_arm={"E": 20, "S": 50, "W": 20},
        inbound_lane_count_by_arm={"E": 1, "S": 3, "W": 1},
        outbound_lane_count_by_arm={"E": 1, "S": 2, "W": 1},
        lane_width=lane_width,
        stop_line_distance=0,
    )

    cx, cy = 100, 100
    by_arm = {arm.name: arm for arm in geometry.arms}
    assert by_arm["E"].stop_line[0][0] == cx + 25
    assert by_arm["W"].stop_line[0][0] == cx - 25
    assert by_arm["S"].stop_line[0][1] == cy + 10


def test_stop_line_base_two_arm_is_zero_so_offset_is_the_full_distance():
    """2-arm (N+S only): no E/W arms → zero auto base, stop_line_distance is the full distance."""
    geometry = build_intersection_geometry(
        window_width=200,
        window_height=200,
        arm_count=2,
        road_width_by_arm={"N": 40, "S": 40},
        inbound_lane_count_by_arm={"N": 2, "S": 2},
        outbound_lane_count=2,
        lane_width=10,
        stop_line_distance=30,
    )

    cy = 100
    by_arm = {arm.name: arm for arm in geometry.arms}
    assert by_arm["N"].stop_line[0][1] == cy - 30
    assert by_arm["S"].stop_line[0][1] == cy + 30


def test_effective_stop_line_distance_by_arm_exposed_on_geometry():
    """IntersectionGeometry exposes the total (base + offset) per arm."""
    lane_width = 10
    geometry = build_intersection_geometry(
        window_width=200,
        window_height=200,
        arm_count=4,
        road_width_by_arm={"N": 40, "E": 40, "S": 40, "W": 40},
        inbound_lane_count_by_arm={"N": 2, "E": 2, "S": 2, "W": 2},
        outbound_lane_count=2,
        lane_width=lane_width,
        stop_line_distance=7,
    )

    # Base = 20, offset = 7 → effective = 27 for all arms
    assert geometry.effective_stop_line_distance_by_arm == {
        "N": 27, "E": 27, "S": 27, "W": 27
    }


def test_ew_stop_line_gap_equals_widest_ns_arm_physical_width():
    """E<->W stop line distance = widest N/S arm total physical width (not 2x max single extent)."""
    lane_width = 30
    # N: 6 inbound (180) + 1 outbound (30), sep=0 → physical width = 210
    # S: 1 inbound (30) + 3 outbound (90), sep=0 → physical width = 120
    # E/W: 2 inbound (60) + 2 outbound (60), sep=0 → physical width = 120
    geometry = build_intersection_geometry(
        window_width=960,
        window_height=720,
        arm_count=4,
        road_width_by_arm={"N": 210, "E": 120, "S": 120, "W": 120},
        inbound_lane_count_by_arm={"N": 6, "E": 2, "S": 1, "W": 2},
        outbound_lane_count_by_arm={"N": 1, "E": 2, "S": 3, "W": 2},
        lane_width=lane_width,
        stop_line_distance=0,
    )

    by_arm = {arm.name: arm for arm in geometry.arms}
    e_dist = geometry.effective_stop_line_distance_by_arm["E"]
    w_dist = geometry.effective_stop_line_distance_by_arm["W"]
    ew_gap = e_dist + w_dist
    assert ew_gap == 210, f"E<->W gap {ew_gap} != widest N/S arm width 210"
    assert e_dist == w_dist, f"E and W should have same base: {e_dist} vs {w_dist}"

"""
Rendering module for the intersection simulation.
Can render to any pygame.Surface, including offscreen surfaces for testing.
"""
from math import degrees
from typing import Mapping, Sequence

import pygame

from crossroads.config import (
    BACKGROUND_COLOR,
    CENTER_MARK_COLOR,
    HUD_BACKGROUND_COLOR,
    HUD_PADDING,
    HUD_TEXT_COLOR,
    ROAD_COLOR,
    ROAD_WIDTH,
    STOP_LINE_COLOR,
    TRAFFIC_LIGHT_RADIUS,
    VEHICLE_COLOR,
    VEHICLE_LENGTH,
    VEHICLE_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from crossroads.intersection import IntersectionGeometry
from crossroads.simulation import SimulationState
from crossroads.traffic_light import LightState
from crossroads.vehicle import lane_center_world_position


_CENTER_LINE_COLOR = (200, 200, 200)
_MARKING_COLOR = _CENTER_LINE_COLOR
_LANE_MARKING_DASH_PATTERN = [4, 4]

_LIGHT_COLORS = {
    LightState.GREEN: (0, 255, 0),
    LightState.YELLOW: (255, 255, 0),
    LightState.RED: (255, 0, 0),
}


def _draw_dashed_line(
    surface: pygame.Surface,
    color: tuple[int, int, int],
    start: tuple[int, int],
    end: tuple[int, int],
    width: int = 1,
    dash_pattern: list[int] | None = None,
) -> None:
    """Draw a dashed line on the given surface."""
    if dash_pattern is None:
        dash_pattern = [4, 4]

    dx = end[0] - start[0]
    dy = end[1] - start[1]
    distance = (dx**2 + dy**2) ** 0.5

    if distance == 0:
        return

    dash_total = sum(dash_pattern)
    segments = int(distance / dash_total) + 1

    for segment in range(segments):
        for i, pattern_part in enumerate(dash_pattern):
            progress = (segment * dash_total + sum(dash_pattern[:i])) / distance
            if i % 2 == 0:
                if progress < 1:
                    next_progress = min(
                        (segment * dash_total + sum(dash_pattern[: i + 1])) / distance, 1
                    )
                    seg_start = (
                        start[0] + dx * progress,
                        start[1] + dy * progress,
                    )
                    seg_end = (
                        start[0] + dx * next_progress,
                        start[1] + dy * next_progress,
                    )
                    pygame.draw.line(surface, color, seg_start, seg_end, width)


def _draw_vehicle(
    surface: pygame.Surface,
    arm: str,
    position: float,
    center_x: int,
    center_y: int,
    *,
    lane_index: int,
    lane_count: int,
    world_window_width: int,
    world_window_height: int,
    road_width: int,
    lane_width: int,
    inbound_lane_offset: int,
    vehicle_length: int,
    vehicle_width: int,
    world_position: tuple[float, float] | None = None,
    world_heading_radians: float | None = None,
) -> None:
    """Draw a vehicle on the surface."""
    if world_position is None:
        world_x, world_y = lane_center_world_position(
            arm=arm,
            distance=position,
            window_width=world_window_width,
            window_height=world_window_height,
            road_width=road_width,
            lane_index=lane_index,
            lane_count=lane_count,
            lane_width=lane_width,
            inbound_lane_offset=inbound_lane_offset,
        )
    else:
        world_x, world_y = world_position
    adj_x = center_x - world_window_width // 2 + world_x
    adj_y = center_y - world_window_height // 2 + world_y

    if world_heading_radians is not None:
        cache = getattr(_draw_vehicle, "_base_surface_cache", None)
        if cache is None:
            cache = {}
            setattr(_draw_vehicle, "_base_surface_cache", cache)
        key = (vehicle_length, vehicle_width)
        vehicle_surface = cache.get(key)
        if vehicle_surface is None:
            vehicle_surface = pygame.Surface((vehicle_length, vehicle_width), pygame.SRCALPHA)
            pygame.draw.rect(
                vehicle_surface,
                VEHICLE_COLOR,
                pygame.Rect(0, 0, vehicle_length, vehicle_width),
            )
            cache[key] = vehicle_surface

        rotated_surface = pygame.transform.rotate(
            vehicle_surface,
            -degrees(world_heading_radians),
        )
        rotated_rect = rotated_surface.get_rect(
            center=(int(round(adj_x)), int(round(adj_y)))
        )
        surface.blit(rotated_surface, rotated_rect)
        return
        return

    if arm in ("N", "S"):
        rect = pygame.Rect(
            int(adj_x - vehicle_width // 2),
            int(adj_y - vehicle_length // 2),
            vehicle_width,
            vehicle_length,
        )
    else:
        rect = pygame.Rect(
            int(adj_x - vehicle_length // 2),
            int(adj_y - vehicle_width // 2),
            vehicle_length,
            vehicle_width,
        )
    pygame.draw.rect(surface, VEHICLE_COLOR, rect)


def _draw_hud_metrics(
    surface: pygame.Surface, average_wait_time: float, screen_width: int, screen_height: int
) -> None:
    """Draw a HUD overlay showing metrics in the top-right corner of the screen."""
    font = pygame.font.Font(None, 24)
    text_surface = font.render(f"Avg Wait: {average_wait_time:.2f}s", True, HUD_TEXT_COLOR)

    text_width = text_surface.get_width()
    text_height = text_surface.get_height()

    bg_rect = pygame.Rect(
        screen_width - text_width - 2 * HUD_PADDING,
        HUD_PADDING,
        text_width + 2 * HUD_PADDING,
        text_height + 2 * HUD_PADDING,
    )
    text_x = bg_rect.left + HUD_PADDING
    text_y = bg_rect.top + HUD_PADDING

    pygame.draw.rect(surface, HUD_BACKGROUND_COLOR, bg_rect)
    surface.blit(text_surface, (text_x, text_y))


def _draw_lane_signals(
    *,
    surface: pygame.Surface,
    geometry: IntersectionGeometry,
    state: SimulationState,
    center_x: int,
    center_y: int,
    world_window_width: int,
    world_window_height: int,
    road_width: int,
    lane_width: int,
) -> None:
    for arm in geometry.arms:
        lane_count = state.lane_counts_by_arm.get(arm.name, 1)
        lane_signal_states = state.lane_light_states
        for lane_index in range(lane_count):
            lane_state = lane_signal_states.get((arm.name, lane_index), state.light_states[arm.name])
            color = _LIGHT_COLORS[lane_state]
            if arm.name in ("N", "S"):
                signal_x, _ = lane_center_world_position(
                    arm=arm.name,
                    distance=0.0,
                    window_width=world_window_width,
                    window_height=world_window_height,
                    road_width=road_width,
                    lane_index=lane_index,
                    lane_count=lane_count,
                    lane_width=lane_width,
                    inbound_lane_offset=arm.inbound_lane_offset,
                )
                signal_y = float(arm.stop_line[0][1])
            else:
                _, signal_y = lane_center_world_position(
                    arm=arm.name,
                    distance=0.0,
                    window_width=world_window_width,
                    window_height=world_window_height,
                    road_width=road_width,
                    lane_index=lane_index,
                    lane_count=lane_count,
                    lane_width=lane_width,
                    inbound_lane_offset=arm.inbound_lane_offset,
                )
                signal_x = float(arm.stop_line[0][0])

            adj_x = int(center_x - world_window_width // 2 + signal_x)
            adj_y = int(center_y - world_window_height // 2 + signal_y)
            pygame.draw.circle(surface, color, (adj_x, adj_y), TRAFFIC_LIGHT_RADIUS)


def _draw_lane_direction_markings(
    *,
    surface: pygame.Surface,
    geometry: IntersectionGeometry,
    lane_counts_by_arm: Mapping[str, int],
    lane_width: int,
    world_window_width: int,
    world_window_height: int,
    inbound_lane_movements_by_arm: Mapping[str, Sequence[Sequence[str]]] | None,
    lane_marker_scale: float = 1.0,
    center_x: int = 0,
    center_y: int = 0,
) -> None:
    if inbound_lane_movements_by_arm is None:
        return

    forward_by_arm = {"N": (0.0, 1.0), "S": (0.0, -1.0), "E": (-1.0, 0.0), "W": (1.0, 0.0)}
    
    # Calculate render offset for world→surface translation
    render_offset_x = center_x - world_window_width // 2
    render_offset_y = center_y - world_window_height // 2

    for arm in geometry.arms:
        lane_count = lane_counts_by_arm.get(arm.name, 1)
        lane_movements = inbound_lane_movements_by_arm.get(arm.name)
        if not lane_movements:
            continue

        stop_x, stop_y = arm.stop_line[0]
        marker_offset = lane_width * 2.0
        for lane_index in range(min(lane_count, len(lane_movements))):
            # road_width is unused since lane_width is explicitly provided; use 1 as placeholder
            lane_center_x, lane_center_y = lane_center_world_position(
                arm=arm.name,
                distance=0.0,
                window_width=world_window_width,
                window_height=world_window_height,
                road_width=1,
                lane_index=lane_index,
                lane_count=lane_count,
                lane_width=lane_width,
                inbound_lane_offset=arm.inbound_lane_offset,
            )
            if arm.name == "N":
                marker_center = (lane_center_x, stop_y - marker_offset)
            elif arm.name == "S":
                marker_center = (lane_center_x, stop_y + marker_offset)
            elif arm.name == "E":
                marker_center = (stop_x + marker_offset, lane_center_y)
            else:
                marker_center = (stop_x - marker_offset, lane_center_y)

            fx, fy = forward_by_arm[arm.name]
            left = (fy, -fx)
            right = (-fy, fx)
            marker_length = lane_width * 1.6 * lane_marker_scale
            branch_length = lane_width * 0.9 * lane_marker_scale

            def _draw_arrow(tip: tuple[float, float], direction: tuple[float, float]) -> None:
                dx, dy = direction
                perp = (-dy, dx)
                a = (
                    tip[0] - (dx * (lane_width * 0.5 * lane_marker_scale)) + (perp[0] * (lane_width * 0.35 * lane_marker_scale)),
                    tip[1] - (dy * (lane_width * 0.5 * lane_marker_scale)) + (perp[1] * (lane_width * 0.35 * lane_marker_scale)),
                )
                b = (
                    tip[0] - (dx * (lane_width * 0.5 * lane_marker_scale)) - (perp[0] * (lane_width * 0.35 * lane_marker_scale)),
                    tip[1] - (dy * (lane_width * 0.5 * lane_marker_scale)) - (perp[1] * (lane_width * 0.35 * lane_marker_scale)),
                )
                pygame.draw.polygon(surface, _MARKING_COLOR, (tip, a, b))

            p0 = (
               marker_center[0] - (fx * marker_length * 0.5) + render_offset_x,
               marker_center[1] - (fy * marker_length * 0.5) + render_offset_y,
            )
            p1 = (
               marker_center[0] + (fx * marker_length * 0.5) + render_offset_x,
               marker_center[1] + (fy * marker_length * 0.5) + render_offset_y,
            )
            movements = set(lane_movements[lane_index])
            if "straight" in movements:
                pygame.draw.line(surface, _MARKING_COLOR, p0, p1, width=2)
                _draw_arrow(p1, (fx, fy))
            if "left" in movements:
                pivot = (
                   marker_center[0] + (fx * marker_length * 0.1) + render_offset_x,
                   marker_center[1] + (fy * marker_length * 0.1) + render_offset_y,
                )
                left_tip = (
                    pivot[0] + (left[0] * branch_length),
                    pivot[1] + (left[1] * branch_length),
                )
                pygame.draw.line(surface, _MARKING_COLOR, p0, pivot, width=2)
                pygame.draw.line(surface, _MARKING_COLOR, pivot, left_tip, width=2)
                _draw_arrow(left_tip, left)
            if "right" in movements:
                pivot = (
                   marker_center[0] + (fx * marker_length * 0.1) + render_offset_x,
                   marker_center[1] + (fy * marker_length * 0.1) + render_offset_y,
                )
                right_tip = (
                    pivot[0] + (right[0] * branch_length),
                    pivot[1] + (right[1] * branch_length),
                )
                pygame.draw.line(surface, _MARKING_COLOR, p0, pivot, width=2)
                pygame.draw.line(surface, _MARKING_COLOR, pivot, right_tip, width=2)
                _draw_arrow(right_tip, right)


def _draw_lane_separation_markings(
    *,
    surface: pygame.Surface,
    geometry: IntersectionGeometry,
    lane_counts_by_arm: Mapping[str, int],
    outbound_lane_count_by_arm: Mapping[str, int] | None,
    lane_width: int,
    world_window_width: int,
    world_window_height: int,
    center_x: int = 0,
    center_y: int = 0,
) -> None:
    cx, cy = geometry.center
    
    # Calculate render offset for world→surface translation
    render_offset_x = center_x - world_window_width // 2
    render_offset_y = center_y - world_window_height // 2
    
    for arm in geometry.arms:
        lane_count = lane_counts_by_arm.get(arm.name, 1)
        outbound_count = (
            lane_count
            if outbound_lane_count_by_arm is None
            else outbound_lane_count_by_arm.get(arm.name, lane_count)
        )
        for boundary_index in range(1, lane_count):
            offset = arm.inbound_lane_offset + (lane_width * boundary_index)
            if arm.name == "N":
                x = cx - offset + render_offset_x
                start, end = (x, 0 + render_offset_y), (x, arm.stop_line[0][1] + render_offset_y)
            elif arm.name == "S":
                x = cx + offset + render_offset_x
                start, end = (x, arm.stop_line[0][1] + render_offset_y), (x, world_window_height - 1 + render_offset_y)
            elif arm.name == "E":
                y = cy - offset + render_offset_y
                start, end = (arm.stop_line[0][0] + render_offset_x, y), (world_window_width - 1 + render_offset_x, y)
            else:
                y = cy + offset + render_offset_y
                start, end = (0 + render_offset_x, y), (arm.stop_line[0][0] + render_offset_x, y)
            _draw_dashed_line(surface, _MARKING_COLOR, start, end, width=2, dash_pattern=_LANE_MARKING_DASH_PATTERN)

        for boundary_index in range(1, outbound_count):
            offset = arm.outbound_lane_offset + (lane_width * boundary_index)
            if arm.name == "N":
                x = cx + offset + render_offset_x
                start, end = (x, 0 + render_offset_y), (x, cy + render_offset_y)
            elif arm.name == "S":
                x = cx - offset + render_offset_x
                start, end = (x, cy + render_offset_y), (x, world_window_height - 1 + render_offset_y)
            elif arm.name == "E":
                y = cy + offset + render_offset_y
                start, end = (cx + render_offset_x, y), (world_window_width - 1 + render_offset_x, y)
            else:
                y = cy - offset + render_offset_y
                start, end = (0 + render_offset_x, y), (cx + render_offset_x, y)
            _draw_dashed_line(surface, _MARKING_COLOR, start, end, width=2, dash_pattern=_LANE_MARKING_DASH_PATTERN)


def render(
    surface: pygame.Surface,
    geometry: IntersectionGeometry,
    state: SimulationState,
    average_wait_time: float,
    *,
    world_window_width: int = WINDOW_WIDTH,
    world_window_height: int = WINDOW_HEIGHT,
    road_width: int = ROAD_WIDTH,
    lane_width: int = VEHICLE_WIDTH,
    vehicle_length: int = VEHICLE_LENGTH,
    vehicle_width: int = VEHICLE_WIDTH,
    outbound_lane_count_by_arm: Mapping[str, int] | None = None,
    inbound_lane_movements_by_arm: Mapping[str, Sequence[Sequence[str]]] | None = None,
    lane_marker_scale: float = 1.0,
) -> None:
    """
    Render the intersection simulation to a pygame surface.
    
    Args:
        surface: pygame.Surface to render to (can be offscreen)
        geometry: IntersectionGeometry with road and arm layout
        state: SimulationState with current vehicle and light positions
        average_wait_time: Average wait time in seconds for HUD display
        world_window_width: Width in world units for the viewport (default: WINDOW_WIDTH)
        world_window_height: Height in world units for the viewport (default: WINDOW_HEIGHT)
        road_width: Width of road segments (default: ROAD_WIDTH)
        lane_width: Width of lanes in pixels (default: VEHICLE_WIDTH)
        vehicle_length: Length of vehicles in pixels (default: VEHICLE_LENGTH)
        vehicle_width: Width of vehicles in pixels (default: VEHICLE_WIDTH)
        outbound_lane_count_by_arm: Mapping of arm name to outbound lane count for drawing lane separations.
            If None, no outbound lane markings are drawn. Keys should match arm names in geometry.
        inbound_lane_movements_by_arm: Mapping of arm name to sequences of allowed movements per inbound lane
            (e.g., {"N": [["straight", "left"], ["straight"]]}). If None, no lane direction markings are drawn.
            Keys should match arm names in geometry. Each sequence length should match lane count for the arm.
        lane_marker_scale: Scale multiplier for lane marker geometry (arrows and separations).
            Default 1.0; use values < 1.0 to shrink markers, > 1.0 to enlarge them.
    """
    current_width, current_height = surface.get_size()
    center_x = current_width // 2
    center_y = current_height // 2

    surface.fill(BACKGROUND_COLOR)

    # Draw roads
    for rect in geometry.road_rects:
        adjusted_rect = (
            center_x - world_window_width // 2 + rect[0],
            center_y - world_window_height // 2 + rect[1],
            rect[2],
            rect[3],
        )
        pygame.draw.rect(surface, ROAD_COLOR, adjusted_rect)

    # Draw stop lines
    for arm in geometry.arms:
        start, end = arm.stop_line
        adjusted_start = (
            center_x - world_window_width // 2 + start[0],
            center_y - world_window_height // 2 + start[1],
        )
        adjusted_end = (
            center_x - world_window_width // 2 + end[0],
            center_y - world_window_height // 2 + end[1],
        )
        pygame.draw.line(surface, STOP_LINE_COLOR, adjusted_start, adjusted_end, width=3)

    # Draw center lines
    for center_line in geometry.arm_center_lines:
        start, end = center_line
        adjusted_start = (
            center_x - world_window_width // 2 + start[0],
            center_y - world_window_height // 2 + start[1],
        )
        adjusted_end = (
            center_x - world_window_width // 2 + end[0],
            center_y - world_window_height // 2 + end[1],
        )
        pygame.draw.line(surface, _CENTER_LINE_COLOR, adjusted_start, adjusted_end, width=2)

    _draw_lane_separation_markings(
        surface=surface,
        geometry=geometry,
        lane_counts_by_arm=state.lane_counts_by_arm,
        outbound_lane_count_by_arm=outbound_lane_count_by_arm,
        lane_width=lane_width,
        world_window_width=world_window_width,
        world_window_height=world_window_height,
        center_x=center_x,
        center_y=center_y,
    )

    _draw_lane_direction_markings(
        surface=surface,
        geometry=geometry,
        lane_counts_by_arm=state.lane_counts_by_arm,
        lane_width=lane_width,
        world_window_width=world_window_width,
        world_window_height=world_window_height,
        inbound_lane_movements_by_arm=inbound_lane_movements_by_arm,
        lane_marker_scale=lane_marker_scale,
        center_x=center_x,
        center_y=center_y,
    )

    # Draw center mark
    adjusted_center = (center_x, center_y)
    pygame.draw.circle(surface, CENTER_MARK_COLOR, adjusted_center, 4)

    # Draw vehicles
    inbound_lane_offset_by_arm = {
        arm.name: arm.inbound_lane_offset for arm in geometry.arms
    }
    for vehicle in state.vehicles:
        lane_count = state.lane_counts_by_arm.get(vehicle.arm, 1)
        _draw_vehicle(
            surface=surface,
            arm=vehicle.arm,
            position=vehicle.position,
            center_x=center_x,
            center_y=center_y,
            lane_index=vehicle.lane_index,
            lane_count=lane_count,
            world_window_width=world_window_width,
            world_window_height=world_window_height,
            road_width=road_width,
            lane_width=lane_width,
            inbound_lane_offset=inbound_lane_offset_by_arm.get(vehicle.arm, 0),
            vehicle_length=vehicle_length,
            vehicle_width=vehicle_width,
            world_position=vehicle.world_position,
            world_heading_radians=vehicle.world_heading_radians,
        )

    _draw_lane_signals(
        surface=surface,
        geometry=geometry,
        state=state,
        center_x=center_x,
        center_y=center_y,
        world_window_width=world_window_width,
        world_window_height=world_window_height,
        road_width=road_width,
        lane_width=lane_width,
    )

    # Draw HUD metrics
    _draw_hud_metrics(
        surface=surface,
        average_wait_time=average_wait_time,
        screen_width=current_width,
        screen_height=current_height,
    )

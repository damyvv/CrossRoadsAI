"""
Rendering module for the intersection simulation.
Can render to any pygame.Surface, including offscreen surfaces for testing.
"""
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
_CENTER_LINE_DASH_PATTERN = [4, 4]

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
) -> None:
    """Draw a vehicle on the surface."""
    world_x, world_y = lane_center_world_position(
        arm=arm,
        distance=position,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        road_width=ROAD_WIDTH,
    )
    adj_x = center_x - WINDOW_WIDTH // 2 + world_x
    adj_y = center_y - WINDOW_HEIGHT // 2 + world_y

    if arm in ("N", "S"):
        rect = pygame.Rect(
            int(adj_x - VEHICLE_WIDTH // 2),
            int(adj_y - VEHICLE_LENGTH // 2),
            VEHICLE_WIDTH,
            VEHICLE_LENGTH,
        )
    else:
        rect = pygame.Rect(
            int(adj_x - VEHICLE_LENGTH // 2),
            int(adj_y - VEHICLE_WIDTH // 2),
            VEHICLE_LENGTH,
            VEHICLE_WIDTH,
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


def render(
    surface: pygame.Surface,
    geometry: IntersectionGeometry,
    state: SimulationState,
    average_wait_time: float,
) -> None:
    """
    Render the intersection simulation to a pygame surface.
    
    Args:
        surface: pygame.Surface to render to (can be offscreen)
        geometry: IntersectionGeometry with road and arm layout
        state: SimulationState with current vehicle and light positions
        average_wait_time: Average wait time in seconds for HUD display
    """
    current_width, current_height = surface.get_size()
    center_x = current_width // 2
    center_y = current_height // 2

    surface.fill(BACKGROUND_COLOR)

    # Draw roads
    for rect in geometry.road_rects:
        adjusted_rect = (
            center_x - WINDOW_WIDTH // 2 + rect[0],
            center_y - WINDOW_HEIGHT // 2 + rect[1],
            rect[2],
            rect[3],
        )
        pygame.draw.rect(surface, ROAD_COLOR, adjusted_rect)

    # Draw stop lines
    for arm in geometry.arms:
        start, end = arm.stop_line
        adjusted_start = (center_x - WINDOW_WIDTH // 2 + start[0], center_y - WINDOW_HEIGHT // 2 + start[1])
        adjusted_end = (center_x - WINDOW_WIDTH // 2 + end[0], center_y - WINDOW_HEIGHT // 2 + end[1])
        pygame.draw.line(surface, STOP_LINE_COLOR, adjusted_start, adjusted_end, width=3)

    # Draw center lines
    for center_line in geometry.arm_center_lines:
        start, end = center_line
        adjusted_start = (center_x - WINDOW_WIDTH // 2 + start[0], center_y - WINDOW_HEIGHT // 2 + start[1])
        adjusted_end = (center_x - WINDOW_WIDTH // 2 + end[0], center_y - WINDOW_HEIGHT // 2 + end[1])
        _draw_dashed_line(
            surface, _CENTER_LINE_COLOR, adjusted_start, adjusted_end, width=2, dash_pattern=_CENTER_LINE_DASH_PATTERN
        )

    # Draw center mark
    adjusted_center = (center_x, center_y)
    pygame.draw.circle(surface, CENTER_MARK_COLOR, adjusted_center, 4)

    # Draw vehicles
    for vehicle in state.vehicles:
        _draw_vehicle(
            surface=surface,
            arm=vehicle.arm,
            position=vehicle.position,
            center_x=center_x,
            center_y=center_y,
        )

    # Draw traffic lights
    for arm in geometry.arms:
        mid_x = (arm.stop_line[0][0] + arm.stop_line[1][0]) // 2
        mid_y = (arm.stop_line[0][1] + arm.stop_line[1][1]) // 2
        adj_x = center_x - WINDOW_WIDTH // 2 + mid_x
        adj_y = center_y - WINDOW_HEIGHT // 2 + mid_y
        color = _LIGHT_COLORS[state.light_states[arm.name]]
        pygame.draw.circle(surface, color, (adj_x, adj_y), TRAFFIC_LIGHT_RADIUS)

    # Draw HUD metrics
    _draw_hud_metrics(
        surface=surface,
        average_wait_time=average_wait_time,
        screen_width=current_width,
        screen_height=current_height,
    )

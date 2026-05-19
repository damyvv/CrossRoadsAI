import pygame

from crossroads.config import (
    LIGHT_COLOR_GREEN,
    LIGHT_COLOR_RED,
    LIGHT_COLOR_YELLOW,
    TRAFFIC_LIGHT_RADIUS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from crossroads.intersection import ArmGeometry
from crossroads.traffic_light import LightState

_LIGHT_COLORS = {
    LightState.GREEN: LIGHT_COLOR_GREEN,
    LightState.YELLOW: LIGHT_COLOR_YELLOW,
    LightState.RED: LIGHT_COLOR_RED,
}


def draw_traffic_lights(
    *,
    surface: pygame.Surface,
    arms: tuple[ArmGeometry, ...],
    light_states: dict[str, LightState],
    center_x: int,
    center_y: int,
) -> None:
    for arm in arms:
        mid_x = (arm.stop_line[0][0] + arm.stop_line[1][0]) // 2
        mid_y = (arm.stop_line[0][1] + arm.stop_line[1][1]) // 2
        adj_x = center_x - WINDOW_WIDTH // 2 + mid_x
        adj_y = center_y - WINDOW_HEIGHT // 2 + mid_y
        color = _LIGHT_COLORS[light_states[arm.name]]
        pygame.draw.circle(surface, color, (adj_x, adj_y), TRAFFIC_LIGHT_RADIUS)

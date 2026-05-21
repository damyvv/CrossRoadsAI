import pygame

from crossroads.intersection import ArmGeometry
from crossroads.traffic_light import LightState
from crossroads.runtime_config import RuntimeConfig


def draw_traffic_lights(
    *,
    surface: pygame.Surface,
    arms: tuple[ArmGeometry, ...],
    light_states: dict[str, LightState],
    center_x: int,
    center_y: int,
    runtime_config: RuntimeConfig,
) -> None:
    _light_colors = {
        LightState.GREEN: runtime_config.light_color_green,
        LightState.YELLOW: runtime_config.light_color_yellow,
        LightState.RED: runtime_config.light_color_red,
    }
    for arm in arms:
        mid_x = (arm.stop_line[0][0] + arm.stop_line[1][0]) // 2
        mid_y = (arm.stop_line[0][1] + arm.stop_line[1][1]) // 2
        adj_x = center_x - runtime_config.window_width // 2 + mid_x
        adj_y = center_y - runtime_config.window_height // 2 + mid_y
        color = _light_colors[light_states[arm.name]]
        pygame.draw.circle(surface, color, (adj_x, adj_y), runtime_config.traffic_light_radius)

import pygame

from crossroads.config import (
    ARM_COUNT,
    BACKGROUND_COLOR,
    CENTER_MARK_COLOR,
    GREEN_DURATION_TICKS,
    LIGHT_COLOR_GREEN,
    LIGHT_COLOR_RED,
    LIGHT_COLOR_YELLOW,
    ROAD_COLOR,
    ROAD_WIDTH,
    STOP_LINE_COLOR,
    STOP_LINE_DISTANCE,
    TRAFFIC_LIGHT_RADIUS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    YELLOW_DURATION_TICKS,
)
from crossroads.intersection import build_intersection_geometry
from crossroads.traffic_light import LightState, TrafficLightController
from crossroads.traffic_phasing import ArmPhase


CENTER_LINE_COLOR = (200, 200, 200)
CENTER_LINE_DASH_PATTERN = [4, 4]


def _draw_dashed_line(surface: pygame.Surface, color: tuple[int, int, int], start: tuple[int, int], end: tuple[int, int], width: int = 1, dash_pattern: list[int] | None = None) -> None:
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
                    next_progress = min((segment * dash_total + sum(dash_pattern[:i+1])) / distance, 1)
                    seg_start = (
                        start[0] + dx * progress,
                        start[1] + dy * progress,
                    )
                    seg_end = (
                        start[0] + dx * next_progress,
                        start[1] + dy * next_progress,
                    )
                    pygame.draw.line(surface, color, seg_start, seg_end, width)


_LIGHT_COLORS = {
    LightState.GREEN: LIGHT_COLOR_GREEN,
    LightState.YELLOW: LIGHT_COLOR_YELLOW,
    LightState.RED: LIGHT_COLOR_RED,
}


def run(*, max_frames: int | None = None) -> None:
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("CrossRoadsAI — Slice 2")
    clock = pygame.time.Clock()

    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=ARM_COUNT,
        road_width=ROAD_WIDTH,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    arm_phases = [
        ArmPhase(arms=["N", "S"], name="NS"),
        ArmPhase(arms=["E", "W"], name="EW"),
    ]
    controller = TrafficLightController(
        arm_names=[arm.name for arm in geometry.arms],
        phases=arm_phases,
        green_ticks=GREEN_DURATION_TICKS,
        yellow_ticks=YELLOW_DURATION_TICKS,
    )

    running = True
    frame_count = 0
    while running:
        current_width, current_height = screen.get_size()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill(BACKGROUND_COLOR)

        center_x = current_width // 2
        center_y = current_height // 2

        for rect in geometry.road_rects:
            adjusted_rect = (
                center_x - WINDOW_WIDTH // 2 + rect[0],
                center_y - WINDOW_HEIGHT // 2 + rect[1],
                rect[2],
                rect[3],
            )
            pygame.draw.rect(screen, ROAD_COLOR, adjusted_rect)

        for arm in geometry.arms:
            start, end = arm.stop_line
            adjusted_start = (center_x - WINDOW_WIDTH // 2 + start[0], center_y - WINDOW_HEIGHT // 2 + start[1])
            adjusted_end = (center_x - WINDOW_WIDTH // 2 + end[0], center_y - WINDOW_HEIGHT // 2 + end[1])
            pygame.draw.line(screen, STOP_LINE_COLOR, adjusted_start, adjusted_end, width=3)

        for center_line in geometry.arm_center_lines:
            start, end = center_line
            adjusted_start = (center_x - WINDOW_WIDTH // 2 + start[0], center_y - WINDOW_HEIGHT // 2 + start[1])
            adjusted_end = (center_x - WINDOW_WIDTH // 2 + end[0], center_y - WINDOW_HEIGHT // 2 + end[1])
            _draw_dashed_line(screen, CENTER_LINE_COLOR, adjusted_start, adjusted_end, width=2, dash_pattern=CENTER_LINE_DASH_PATTERN)

        adjusted_center = (center_x, center_y)
        pygame.draw.circle(screen, CENTER_MARK_COLOR, adjusted_center, 4)

        for arm in geometry.arms:
            mid_x = (arm.stop_line[0][0] + arm.stop_line[1][0]) // 2
            mid_y = (arm.stop_line[0][1] + arm.stop_line[1][1]) // 2
            adj_x = center_x - WINDOW_WIDTH // 2 + mid_x
            adj_y = center_y - WINDOW_HEIGHT // 2 + mid_y
            color = _LIGHT_COLORS[controller.state(arm.name)]
            pygame.draw.circle(screen, color, (adj_x, adj_y), TRAFFIC_LIGHT_RADIUS)

        controller.advance_tick()

        pygame.display.flip()
        clock.tick(60)
        frame_count += 1
        if max_frames is not None and frame_count >= max_frames:
            running = False

    pygame.quit()

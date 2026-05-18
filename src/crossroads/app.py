import pygame

from crossroads.config import (
    ARM_COUNT,
    BACKGROUND_COLOR,
    CENTER_MARK_COLOR,
    ROAD_COLOR,
    ROAD_WIDTH,
    STOP_LINE_COLOR,
    STOP_LINE_DISTANCE,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from crossroads.intersection import ArmGeometry, build_intersection_geometry


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


def run(*, max_frames: int | None = None) -> None:
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("CrossRoadsAI — Slice 1")
    clock = pygame.time.Clock()

    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=ARM_COUNT,
        road_width=ROAD_WIDTH,
        stop_line_distance=STOP_LINE_DISTANCE,
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
        pygame.display.flip()
        clock.tick(60)
        frame_count += 1
        if max_frames is not None and frame_count >= max_frames:
            running = False

    pygame.quit()


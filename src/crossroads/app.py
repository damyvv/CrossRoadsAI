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


def _stop_line_segment(arm: ArmGeometry, *, center: tuple[int, int], road_width: int) -> tuple[tuple[int, int], tuple[int, int]]:
    x, y = arm.stop_line_point
    cx, cy = center
    half_width = road_width // 2
    if abs(x - cx) > abs(y - cy):
        return (x, y - half_width), (x, y + half_width)
    return (x - half_width, y), (x + half_width, y)


def run(*, max_frames: int | None = None) -> None:
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
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
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        screen.fill(BACKGROUND_COLOR)
        for rect in geometry.road_rects:
            pygame.draw.rect(screen, ROAD_COLOR, rect)

        for arm in geometry.arms:
            start, end = _stop_line_segment(arm, center=geometry.center, road_width=ROAD_WIDTH)
            pygame.draw.line(screen, STOP_LINE_COLOR, start, end, width=3)

        pygame.draw.circle(screen, CENTER_MARK_COLOR, geometry.center, 4)
        pygame.display.flip()
        clock.tick(60)
        frame_count += 1
        if max_frames is not None and frame_count >= max_frames:
            running = False

    pygame.quit()

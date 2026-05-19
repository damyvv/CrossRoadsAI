import pygame

from crossroads.config import (
    ARM_COUNT,
    BACKGROUND_COLOR,
    CENTER_MARK_COLOR,
    LIGHT_COLOR_GREEN,
    ROAD_COLOR,
    ROAD_WIDTH,
    STOP_LINE_COLOR,
    STOP_LINE_DISTANCE,
    TRAFFIC_LIGHT_RADIUS,
    VEHICLE_ACCELERATION,
    VEHICLE_COLOR,
    VEHICLE_DECELERATION,
    VEHICLE_LENGTH,
    VEHICLE_SPAWN_ARM,
    VEHICLE_TOP_SPEED,
    VEHICLE_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from crossroads.intersection import build_intersection_geometry
from crossroads.vehicle import Vehicle, VehicleState, crossing_bounds_for_arm, world_position_for_distance


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


def _draw_constant_green_lights(
    *,
    surface: pygame.Surface,
    stop_lines: list[tuple[tuple[int, int], tuple[int, int]]],
    center_x: int,
    center_y: int,
) -> None:
    for start, end in stop_lines:
        mid_x = (start[0] + end[0]) // 2
        mid_y = (start[1] + end[1]) // 2
        adj_x = center_x - WINDOW_WIDTH // 2 + mid_x
        adj_y = center_y - WINDOW_HEIGHT // 2 + mid_y
        pygame.draw.circle(surface, LIGHT_COLOR_GREEN, (adj_x, adj_y), TRAFFIC_LIGHT_RADIUS)


def _draw_vehicle(
    *,
    surface: pygame.Surface,
    vehicle: Vehicle,
    center_x: int,
    center_y: int,
) -> None:
    world_x, world_y = world_position_for_distance(
        arm=vehicle.arm,
        distance=vehicle.position,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
    )
    adj_x = center_x - WINDOW_WIDTH // 2 + world_x
    adj_y = center_y - WINDOW_HEIGHT // 2 + world_y

    if vehicle.arm in ("N", "S"):
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


def run(*, max_frames: int | None = None) -> None:
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("CrossRoadsAI — Slice 3")
    clock = pygame.time.Clock()

    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=ARM_COUNT,
        road_width=ROAD_WIDTH,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    crossing_start, crossing_end = crossing_bounds_for_arm(
        arm=VEHICLE_SPAWN_ARM,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        road_width=ROAD_WIDTH,
    )
    vehicles = [
        Vehicle(
            arm=VEHICLE_SPAWN_ARM,
            crossing_start=crossing_start,
            crossing_end=crossing_end,
            target_velocity=VEHICLE_TOP_SPEED,
            max_velocity=VEHICLE_TOP_SPEED,
            acceleration=VEHICLE_ACCELERATION,
            deceleration=VEHICLE_DECELERATION,
        )
    ]

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

        _draw_constant_green_lights(
            surface=screen,
            stop_lines=[arm.stop_line for arm in geometry.arms],
            center_x=center_x,
            center_y=center_y,
        )

        for vehicle in vehicles:
            _draw_vehicle(surface=screen, vehicle=vehicle, center_x=center_x, center_y=center_y)
            vehicle.advance_tick()
        vehicles = [vehicle for vehicle in vehicles if vehicle.state != VehicleState.EXITED]

        pygame.display.flip()
        clock.tick(60)
        frame_count += 1
        if max_frames is not None and frame_count >= max_frames:
            running = False

    pygame.quit()

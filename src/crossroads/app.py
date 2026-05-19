import pygame

from crossroads.config import (
    ARM_COUNT,
    BACKGROUND_COLOR,
    CENTER_MARK_COLOR,
    GREEN_DURATION_TICKS,
    HUD_BACKGROUND_COLOR,
    HUD_PADDING,
    HUD_TEXT_COLOR,
    ROAD_COLOR,
    ROAD_WIDTH,
    SIMULATION_TICKS_PER_SECOND,
    STOP_LINE_COLOR,
    STOP_LINE_DISTANCE,
    VEHICLE_ACCELERATION,
    VEHICLE_COLOR,
    VEHICLE_DECELERATION,
    VEHICLE_LENGTH,
    VEHICLE_QUEUE_GAP,
    VEHICLE_STOP_DISTANCE_BEFORE_LINE,
    VEHICLE_SPAWN_RATE_PER_SECOND,
    VEHICLE_SPAWN_SEED,
    VEHICLE_TOP_SPEED,
    VEHICLE_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    YELLOW_DURATION_TICKS,
)
from crossroads.intersection import build_intersection_geometry
from crossroads.simulation import IntersectionSimulation, TrafficSpawnConfig, VehicleFlowConfig
from crossroads.traffic_light_rendering import draw_traffic_lights
from crossroads.traffic_phasing import default_four_way_phases
from crossroads.vehicle import lane_center_world_position


CENTER_LINE_COLOR = (200, 200, 200)
CENTER_LINE_DASH_PATTERN = [4, 4]

HUD_CORNER = "top-right"


def _draw_hud_metrics(surface: pygame.Surface, average_wait_time: float, screen_width: int, screen_height: int) -> None:
    """Draw a HUD overlay showing metrics in a corner of the screen."""
    font = pygame.font.Font(None, 24)
    text_surface = font.render(f"Avg Wait: {average_wait_time:.2f}s", True, HUD_TEXT_COLOR)
    
    text_width = text_surface.get_width()
    text_height = text_surface.get_height()
    
    if HUD_CORNER == "top-right":
        bg_rect = pygame.Rect(
            screen_width - text_width - 2 * HUD_PADDING,
            HUD_PADDING,
            text_width + 2 * HUD_PADDING,
            text_height + 2 * HUD_PADDING,
        )
        text_x = bg_rect.left + HUD_PADDING
        text_y = bg_rect.top + HUD_PADDING
    else:
        bg_rect = pygame.Rect(
            HUD_PADDING,
            HUD_PADDING,
            text_width + 2 * HUD_PADDING,
            text_height + 2 * HUD_PADDING,
        )
        text_x = bg_rect.left + HUD_PADDING
        text_y = bg_rect.top + HUD_PADDING
    
    pygame.draw.rect(surface, HUD_BACKGROUND_COLOR, bg_rect)
    surface.blit(text_surface, (text_x, text_y))


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


def _draw_vehicle(
    *,
    surface: pygame.Surface,
    arm: str,
    position: float,
    center_x: int,
    center_y: int,
) -> None:
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


def run(*, max_frames: int | None = None) -> None:
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("CrossRoadsAI — Slice 4")
    clock = pygame.time.Clock()

    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=ARM_COUNT,
        road_width=ROAD_WIDTH,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    simulation = IntersectionSimulation(
        arm_names=tuple(arm.name for arm in geometry.arms),
        phases=default_four_way_phases(),
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        stop_line_distance=STOP_LINE_DISTANCE,
        green_ticks=GREEN_DURATION_TICKS,
        yellow_ticks=YELLOW_DURATION_TICKS,
        vehicle_flow=VehicleFlowConfig(
            top_speed=VEHICLE_TOP_SPEED,
            acceleration=VEHICLE_ACCELERATION,
            deceleration=VEHICLE_DECELERATION,
            length=VEHICLE_LENGTH,
            queue_gap=VEHICLE_QUEUE_GAP,
            stop_distance_before_line=VEHICLE_STOP_DISTANCE_BEFORE_LINE,
        ),
        spawn=TrafficSpawnConfig(
            lambda_per_second=VEHICLE_SPAWN_RATE_PER_SECOND,
            ticks_per_second=SIMULATION_TICKS_PER_SECOND,
            seed=VEHICLE_SPAWN_SEED,
        ),
    )

    running = True
    frame_count = 0
    while running:
        simulation_state = simulation.state()
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

        for vehicle in simulation_state.vehicles:
            _draw_vehicle(
                surface=screen,
                arm=vehicle.arm,
                position=vehicle.position,
                center_x=center_x,
                center_y=center_y,
            )

        draw_traffic_lights(
            surface=screen,
            arms=geometry.arms,
            light_states=simulation_state.light_states,
            center_x=center_x,
            center_y=center_y,
        )

        # Draw HUD with metrics
        average_wait_ticks = simulation.average_wait_time()
        average_wait_seconds = average_wait_ticks / SIMULATION_TICKS_PER_SECOND
        _draw_hud_metrics(
            surface=screen,
            average_wait_time=average_wait_seconds,
            screen_width=current_width,
            screen_height=current_height,
        )

        simulation.advance_tick()

        pygame.display.flip()
        clock.tick(SIMULATION_TICKS_PER_SECOND)
        frame_count += 1
        if max_frames is not None and frame_count >= max_frames:
            running = False

    pygame.quit()

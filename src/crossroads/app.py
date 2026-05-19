import pygame

from crossroads.config import (
    ARM_COUNT,
    BACKGROUND_COLOR,
    CENTER_MARK_COLOR,
    GREEN_DURATION_TICKS,
    ROAD_COLOR,
    ROAD_WIDTH,
    SIMULATION_TICKS_PER_SECOND,
    STOP_LINE_COLOR,
    STOP_LINE_DISTANCE,
    VEHICLE_ACCELERATION,
    VEHICLE_COLOR,
    VEHICLE_DECELERATION,
    VEHICLE_LENGTH,
    VEHICLE_SPAWN_RATE_PER_SECOND,
    VEHICLE_SPAWN_SEED,
    VEHICLE_TOP_SPEED,
    VEHICLE_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    YELLOW_DURATION_TICKS,
)
from crossroads.intersection import build_intersection_geometry
from crossroads.traffic_generator import TrafficGenerator
from crossroads.traffic_light import LightState, TrafficLightController
from crossroads.traffic_light_rendering import draw_traffic_lights
from crossroads.traffic_phasing import default_four_way_phases
from crossroads.vehicle import (
    Vehicle,
    VehicleState,
    lane_center_world_position,
    spawn_distance_for_length,
    state_thresholds_for_arm,
)


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


def _draw_vehicle(
    *,
    surface: pygame.Surface,
    vehicle: Vehicle,
    center_x: int,
    center_y: int,
) -> None:
    world_x, world_y = lane_center_world_position(
        arm=vehicle.arm,
        distance=vehicle.position,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        road_width=ROAD_WIDTH,
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


def _entry_occupied_by_arm(
    *,
    arm_names: tuple[str, ...],
    vehicles: list[Vehicle],
    entry_distance: float,
    clearance_distance: float,
) -> dict[str, bool]:
    if clearance_distance < 0:
        raise ValueError("clearance_distance must be non-negative")
    blocked_distance = entry_distance + clearance_distance
    return {
        arm: any(vehicle.arm == arm and vehicle.position <= blocked_distance for vehicle in vehicles)
        for arm in arm_names
    }


def _advance_vehicles(
    *,
    vehicles: list[Vehicle],
    arm_names: tuple[str, ...],
    controller: TrafficLightController,
    queue_gap: float,
) -> None:
    for arm in arm_names:
        arm_vehicles = sorted(
            (vehicle for vehicle in vehicles if vehicle.arm == arm),
            key=lambda vehicle: vehicle.position,
            reverse=True,
        )
        can_enter_intersection = controller.state(arm) == LightState.GREEN
        for index, vehicle in enumerate(arm_vehicles):
            max_position = None
            if index > 0:
                max_position = arm_vehicles[index - 1].position - queue_gap
            vehicle.advance_tick(
                can_enter_intersection=can_enter_intersection,
                max_position=max_position,
            )


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

    controller = TrafficLightController(
        arm_names=[arm.name for arm in geometry.arms],
        phases=list(default_four_way_phases()),
        green_ticks=GREEN_DURATION_TICKS,
        yellow_ticks=YELLOW_DURATION_TICKS,
    )

    arm_names = tuple(arm.name for arm in geometry.arms)
    thresholds_by_arm = {
        arm_name: state_thresholds_for_arm(
            arm=arm_name,
            window_width=WINDOW_WIDTH,
            window_height=WINDOW_HEIGHT,
            stop_line_distance=STOP_LINE_DISTANCE,
            vehicle_length=VEHICLE_LENGTH,
        )
        for arm_name in arm_names
    }
    spawn_distance = spawn_distance_for_length(VEHICLE_LENGTH)
    traffic_generator = TrafficGenerator(
        arm_names=arm_names,
        lambda_per_second=VEHICLE_SPAWN_RATE_PER_SECOND,
        ticks_per_second=SIMULATION_TICKS_PER_SECOND,
        seed=VEHICLE_SPAWN_SEED,
    )
    vehicles: list[Vehicle] = []

    running = True
    frame_count = 0
    while running:
        current_width, current_height = screen.get_size()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        occupied_entries = _entry_occupied_by_arm(
            arm_names=arm_names,
            vehicles=vehicles,
            entry_distance=spawn_distance,
            clearance_distance=float(VEHICLE_LENGTH),
        )
        for spawn_arm in traffic_generator.advance_tick(entry_occupied_by_arm=occupied_entries):
            thresholds = thresholds_by_arm[spawn_arm]
            vehicles.append(
                Vehicle(
                    arm=spawn_arm,
                    crossing_distance=thresholds.crossing,
                    exit_distance=thresholds.exited,
                    discard_distance=thresholds.discard,
                    target_velocity=VEHICLE_TOP_SPEED,
                    max_velocity=VEHICLE_TOP_SPEED,
                    acceleration=VEHICLE_ACCELERATION,
                    deceleration=VEHICLE_DECELERATION,
                    position=spawn_distance,
                )
            )

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

        for vehicle in vehicles:
            _draw_vehicle(surface=screen, vehicle=vehicle, center_x=center_x, center_y=center_y)
        _advance_vehicles(
            vehicles=vehicles,
            arm_names=arm_names,
            controller=controller,
            queue_gap=float(VEHICLE_LENGTH),
        )
        vehicles = [vehicle for vehicle in vehicles if vehicle.state != VehicleState.DISCARD]

        draw_traffic_lights(
            surface=screen,
            arms=geometry.arms,
            controller=controller,
            center_x=center_x,
            center_y=center_y,
        )

        controller.advance_tick()

        pygame.display.flip()
        clock.tick(SIMULATION_TICKS_PER_SECOND)
        frame_count += 1
        if max_frames is not None and frame_count >= max_frames:
            running = False

    pygame.quit()

import pygame

from crossroads.config import (
    ARM_COUNT,
    GREEN_DURATION_TICKS,
    ROAD_WIDTH,
    SIMULATION_TICKS_PER_SECOND,
    STOP_LINE_DISTANCE,
    VEHICLE_ACCELERATION,
    VEHICLE_DECELERATION,
    VEHICLE_LENGTH,
    VEHICLE_QUEUE_GAP,
    VEHICLE_STOP_DISTANCE_BEFORE_LINE,
    VEHICLE_SPAWN_RATE_PER_SECOND,
    VEHICLE_SPAWN_SEED,
    VEHICLE_TOP_SPEED,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    YELLOW_DURATION_TICKS,
)
from crossroads.intersection import build_intersection_geometry
from crossroads.renderer import render
from crossroads.simulation import IntersectionSimulation, TrafficSpawnConfig, VehicleFlowConfig
from crossroads.traffic_light import TrafficLightController
from crossroads.traffic_phasing import default_four_way_phases


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
        phases=default_four_way_phases(),
        green_ticks=GREEN_DURATION_TICKS,
        yellow_ticks=YELLOW_DURATION_TICKS,
    )

    simulation = IntersectionSimulation(
        arm_names=tuple(arm.name for arm in geometry.arms),
        controller=controller,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        stop_line_distance=STOP_LINE_DISTANCE,
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

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        average_wait_ticks = simulation.average_wait_time()
        average_wait_seconds = average_wait_ticks / SIMULATION_TICKS_PER_SECOND

        render(
            surface=screen,
            geometry=geometry,
            state=simulation_state,
            average_wait_time=average_wait_seconds,
        )

        simulation.advance_tick()

        pygame.display.flip()
        clock.tick(SIMULATION_TICKS_PER_SECOND)
        frame_count += 1
        if max_frames is not None and frame_count >= max_frames:
            running = False

    pygame.quit()

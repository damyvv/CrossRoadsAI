import pygame

from crossroads.intersection import (
    build_intersection_geometry,
    compute_road_width_from_inbound_lanes,
)
from crossroads.renderer import render
from crossroads.runtime_config import RuntimeConfig, resolve_runtime_config
from crossroads.simulation import (
    InboundLaneSpawnConfig,
    IntersectionSimulation,
    TrafficSpawnConfig,
    VehicleFlowConfig,
)
from crossroads.traffic_light import TrafficLightController


def run(*, max_frames: int | None = None, runtime_config: RuntimeConfig | None = None) -> None:
    runtime_config = runtime_config or resolve_runtime_config(config_path=None)
    road_width = compute_road_width_from_inbound_lanes(
        inbound_lanes_by_arm=runtime_config.inbound_lanes_by_arm,
        lane_width=runtime_config.vehicle_width,
    )
    pygame.init()
    screen = pygame.display.set_mode(
        (runtime_config.window_width, runtime_config.window_height), pygame.RESIZABLE
    )
    pygame.display.set_caption("CrossRoadsAI — Slice 4")
    clock = pygame.time.Clock()

    geometry = build_intersection_geometry(
        window_width=runtime_config.window_width,
        window_height=runtime_config.window_height,
        arm_count=runtime_config.arm_count,
        missing_arm=runtime_config.missing_arm,
        road_width=road_width,
        stop_line_distance=runtime_config.stop_line_distance,
    )

    controller = TrafficLightController(
        arm_names=[arm.name for arm in geometry.arms],
        phases=list(runtime_config.phases),
        green_ticks=runtime_config.green_duration_ticks,
        yellow_ticks=runtime_config.yellow_duration_ticks,
    )

    simulation = IntersectionSimulation(
        arm_names=tuple(arm.name for arm in geometry.arms),
        controller=controller,
        window_width=runtime_config.window_width,
        window_height=runtime_config.window_height,
        stop_line_distance=runtime_config.stop_line_distance,
        vehicle_flow=VehicleFlowConfig(
            top_speed=runtime_config.vehicle_top_speed,
            acceleration=runtime_config.vehicle_acceleration,
            deceleration=runtime_config.vehicle_deceleration,
            length=runtime_config.vehicle_length,
            queue_gap=runtime_config.vehicle_queue_gap,
            stop_distance_before_line=runtime_config.vehicle_stop_distance_before_line,
        ),
        spawn=TrafficSpawnConfig(
            lambda_per_second=runtime_config.vehicle_spawn_rate_per_second,
            lambda_per_second_by_arm=runtime_config.vehicle_spawn_rate_per_second_by_arm,
            ticks_per_second=runtime_config.simulation_ticks_per_second,
            seed=runtime_config.vehicle_spawn_seed,
            inbound_lanes_by_arm={
                arm: tuple(
                    InboundLaneSpawnConfig(
                        movements=lane.movements,
                        movement_probabilities=lane.movement_probabilities,
                    )
                    for lane in lanes
                )
                for arm, lanes in runtime_config.inbound_lanes_by_arm.items()
            },
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
        average_wait_seconds = average_wait_ticks / runtime_config.simulation_ticks_per_second

        render(
            surface=screen,
            geometry=geometry,
            state=simulation_state,
            average_wait_time=average_wait_seconds,
            world_window_width=runtime_config.window_width,
            world_window_height=runtime_config.window_height,
            road_width=road_width,
            vehicle_length=runtime_config.vehicle_length,
            vehicle_width=runtime_config.vehicle_width,
        )

        simulation.advance_tick()

        pygame.display.flip()
        clock.tick(runtime_config.simulation_ticks_per_second)
        frame_count += 1
        if max_frames is not None and frame_count >= max_frames:
            running = False

    pygame.quit()

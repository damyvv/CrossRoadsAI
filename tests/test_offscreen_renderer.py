"""
Offscreen renderer tests that verify rendering to pygame surfaces without a display.
"""
import pytest

import pygame

# Inlined config constants (previously in crossroads.config)
GREEN_DURATION_TICKS = 150
ROAD_WIDTH = 120
SIMULATION_TICKS_PER_SECOND = 60
STOP_LINE_DISTANCE = 70
VEHICLE_ACCELERATION = 0.20
VEHICLE_COLOR = (70, 130, 240)
VEHICLE_DECELERATION = 0.30
VEHICLE_LENGTH = 24
VEHICLE_QUEUE_GAP = 8
VEHICLE_STOP_DISTANCE_BEFORE_LINE = 10.0
VEHICLE_TOP_SPEED = 4.0
VEHICLE_WIDTH = 12
WINDOW_HEIGHT = 720
WINDOW_WIDTH = 960
YELLOW_DURATION_TICKS = 60
from crossroads.intersection import build_intersection_geometry
from crossroads.renderer import render
from crossroads.simulation import IntersectionSimulation, TrafficSpawnConfig, VehicleFlowConfig
from crossroads.traffic_light import LightState, TrafficLightController
from crossroads.traffic_phasing import default_four_way_phases


@pytest.fixture(scope="module", autouse=True)
def init_pygame():
    """Initialize pygame with dummy video driver for tests."""
    if not pygame.get_init():
        pygame.init()
    yield
    pygame.quit()


def test_offscreen_render_without_display():
    """Verify that rendering works with offscreen surface without pygame.display."""
    pygame.init()

    # Create offscreen surface
    surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))

    # Build geometry
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=4,
        road_width=25,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    # Create a simple simulation state
    from crossroads.simulation import SimulationState, VehicleSnapshot
    from crossroads.vehicle import VehicleState

    state = SimulationState(
        light_states={"N": LightState.GREEN, "E": LightState.RED, "S": LightState.GREEN, "W": LightState.RED},
        vehicles=(
            VehicleSnapshot(arm="N", position=100.0, state=VehicleState.APPROACHING, wait_ticks=5),
            VehicleSnapshot(arm="E", position=80.0, state=VehicleState.STOPPED, wait_ticks=0),
        ),
    )

    # Render to offscreen surface
    render(surface=surface, geometry=geometry, state=state, average_wait_time=1.5)

    # Verify surface was rendered
    assert surface.get_size() == (WINDOW_WIDTH, WINDOW_HEIGHT)


def test_offscreen_renderer_draws_traffic_lights():
    """Verify that renderer draws traffic lights with correct colors."""
    pygame.init()

    surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=4,
        road_width=25,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    from crossroads.simulation import SimulationState

    # Test GREEN light
    state_green = SimulationState(
        light_states={"N": LightState.GREEN, "E": LightState.RED, "S": LightState.GREEN, "W": LightState.RED},
        vehicles=(),
    )
    render(surface=surface, geometry=geometry, state=state_green, average_wait_time=0.0)

    # Get the N arm stop line center (approximately where green light should be)
    # Since the surface is exactly WINDOW_WIDTH x WINDOW_HEIGHT, the light is drawn at its
    # world coordinates directly (center_x - WINDOW_WIDTH // 2 == 0)
    n_arm = geometry.arms[0]  # N arm
    light_x = (n_arm.stop_line[0][0] + n_arm.stop_line[1][0]) // 2
    light_y = (n_arm.stop_line[0][1] + n_arm.stop_line[1][1]) // 2

    # Check that a pixel near the light center has a green-ish color
    # (allowing for anti-aliasing and rasterization)
    pixel = surface.get_at((light_x, light_y))
    # GREEN light should be (0, 255, 0) or close to it
    assert pixel[1] > 200, f"Expected green pixel, got {pixel} at ({light_x}, {light_y})"


def test_offscreen_renderer_draws_one_signal_head_per_lane():
    pygame.init()

    lane_width = 12
    road_width = 48
    surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=4,
        road_width=road_width,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    from crossroads.simulation import SimulationState
    from crossroads.vehicle import lane_center_world_position

    state = SimulationState(
        light_states={"N": LightState.GREEN, "E": LightState.RED, "S": LightState.GREEN, "W": LightState.RED},
        lane_counts_by_arm={"N": 2, "E": 1, "S": 1, "W": 1},
        lane_light_states={
            ("N", 0): LightState.GREEN,
            ("N", 1): LightState.RED,
            ("E", 0): LightState.RED,
            ("S", 0): LightState.GREEN,
            ("W", 0): LightState.RED,
        },
        vehicles=(),
    )
    render(
        surface=surface,
        geometry=geometry,
        state=state,
        average_wait_time=0.0,
        road_width=road_width,
        vehicle_width=VEHICLE_WIDTH,
        lane_width=lane_width,
    )

    north_stop_line_y = geometry.arms[0].stop_line[0][1]
    lane_0_x, _ = lane_center_world_position(
        arm="N",
        distance=0.0,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        road_width=road_width,
        lane_index=0,
        lane_count=2,
        lane_width=lane_width,
    )
    lane_1_x, _ = lane_center_world_position(
        arm="N",
        distance=0.0,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        road_width=road_width,
        lane_index=1,
        lane_count=2,
        lane_width=lane_width,
    )

    lane_0_pixel = surface.get_at((int(lane_0_x), north_stop_line_y))
    lane_1_pixel = surface.get_at((int(lane_1_x), north_stop_line_y))
    assert lane_0_pixel[1] > 200, f"Expected green lane signal, got {lane_0_pixel}"
    assert lane_1_pixel[0] > 200 and lane_1_pixel[1] < 100, (
        f"Expected red lane signal, got {lane_1_pixel}"
    )


def test_offscreen_renderer_draws_vehicles():
    """Verify that renderer draws vehicles with correct color."""
    pygame.init()

    surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=4,
        road_width=25,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    from crossroads.simulation import SimulationState, VehicleSnapshot
    from crossroads.vehicle import lane_center_world_position
    from crossroads.vehicle import VehicleState

    # Create a vehicle on the North arm at a known position
    state = SimulationState(
        light_states={"N": LightState.GREEN, "E": LightState.RED, "S": LightState.GREEN, "W": LightState.RED},
        vehicles=(VehicleSnapshot(arm="N", position=150.0, state=VehicleState.CROSSING, wait_ticks=0),),
    )

    render(surface=surface, geometry=geometry, state=state, average_wait_time=0.0)

    world_x, world_y = lane_center_world_position(
        arm="N",
        distance=150.0,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        road_width=ROAD_WIDTH,
        lane_width=VEHICLE_WIDTH,
    )
    center_x, center_y = surface.get_width() // 2, surface.get_height() // 2
    pixel_x = center_x - WINDOW_WIDTH // 2 + int(world_x)
    pixel_y = center_y - WINDOW_HEIGHT // 2 + int(world_y)

    pixel = surface.get_at((pixel_x, pixel_y))
    assert tuple(pixel[:3]) == VEHICLE_COLOR, (
        f"Expected vehicle color {VEHICLE_COLOR} at ({pixel_x}, {pixel_y}), got {tuple(pixel[:3])}"
    )


def test_offscreen_renderer_with_full_simulation():
    """Verify renderer works with a full simulation running headlessly."""
    pygame.init()

    # Create simulation with injected controller
    controller = TrafficLightController(
        arm_names=["N", "E", "S", "W"],
        phases=default_four_way_phases(),
        green_ticks=GREEN_DURATION_TICKS,
        yellow_ticks=YELLOW_DURATION_TICKS,
    )

    simulation = IntersectionSimulation(
        arm_names=("N", "E", "S", "W"),
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
            lambda_per_second=2.0,
            ticks_per_second=SIMULATION_TICKS_PER_SECOND,
            seed=42,
        ),
    )

    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=4,
        road_width=25,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    # Create offscreen surface
    surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))

    # Run simulation and render several frames
    final_state = None
    for _ in range(10):
        final_state = simulation.state()
        avg_wait = simulation.average_wait_time()
        render(surface=surface, geometry=geometry, state=final_state, average_wait_time=avg_wait)
        simulation.advance_tick()

    # Verify simulation produced some state and metrics were tracked
    assert final_state is not None
    assert len(final_state.light_states) == 4
    assert all(arm in final_state.light_states for arm in ["N", "E", "S", "W"])

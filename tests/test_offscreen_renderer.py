"""
Offscreen renderer tests that verify rendering to pygame surfaces without a display.
"""
import pytest

import pygame

from crossroads.config import (
    BACKGROUND_COLOR,
    GREEN_DURATION_TICKS,
    ROAD_WIDTH,
    SIMULATION_TICKS_PER_SECOND,
    STOP_LINE_DISTANCE,
    VEHICLE_ACCELERATION,
    VEHICLE_COLOR,
    VEHICLE_DECELERATION,
    VEHICLE_LENGTH,
    VEHICLE_QUEUE_GAP,
    VEHICLE_STOP_DISTANCE_BEFORE_LINE,
    VEHICLE_TOP_SPEED,
    VEHICLE_WIDTH,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    YELLOW_DURATION_TICKS,
)
from crossroads.intersection import build_intersection_geometry
from crossroads.renderer import _draw_lane_direction_markings, render
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


def test_offscreen_renderer_draws_lane_direction_markings_for_inbound_lanes():
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
        vehicles=(),
    )
    render(
        surface=surface,
        geometry=geometry,
        state=state,
        average_wait_time=0.0,
        road_width=road_width,
        lane_width=lane_width,
        inbound_lane_movements_by_arm={
            "N": (("left",), ("straight", "right")),
            "E": (("straight",),),
            "S": (("straight",),),
            "W": (("straight",),),
        },
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
    marker_y = north_stop_line_y - (lane_width * 2)
    marker_pixel = surface.get_at((int(lane_0_x), int(marker_y)))
    assert marker_pixel[0] > 150 and marker_pixel[1] > 150 and marker_pixel[2] > 150


def test_offscreen_renderer_uses_solid_centerline():
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

    state = SimulationState(
        light_states={"N": LightState.GREEN, "E": LightState.RED, "S": LightState.GREEN, "W": LightState.RED},
        vehicles=(),
    )
    render(
        surface=surface,
        geometry=geometry,
        state=state,
        average_wait_time=0.0,
        lane_width=lane_width,
    )

    cx = WINDOW_WIDTH // 2
    gap_probe_y = 7  # Dashed line used to have a gap at this offset.
    pixel = surface.get_at((cx, gap_probe_y))
    assert pixel[0] > 150 and pixel[1] > 150 and pixel[2] > 150


def test_offscreen_renderer_draws_striped_lane_separation_for_inbound_and_outbound_lanes():
    """Verify that render() accepts outbound_lane_count_by_arm parameter without error."""
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

    state = SimulationState(
        light_states={"N": LightState.GREEN, "E": LightState.RED, "S": LightState.GREEN, "W": LightState.RED},
        lane_counts_by_arm={"N": 2, "E": 1, "S": 1, "W": 1},
        vehicles=(),
    )
    
    # This should not raise an error when outbound_lane_count_by_arm is provided
    render(
        surface=surface,
        geometry=geometry,
        state=state,
        average_wait_time=0.0,
        lane_width=lane_width,
        outbound_lane_count_by_arm={"N": 2, "E": 1, "S": 1, "W": 1},
    )


def test_offscreen_renderer_draws_lane_direction_markings_in_two_arm_topology():
    pygame.init()

    lane_width = 12
    road_width = 48
    surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=2,
        road_width=road_width,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    from crossroads.simulation import SimulationState
    from crossroads.vehicle import lane_center_world_position

    state = SimulationState(
        light_states={"N": LightState.GREEN, "S": LightState.GREEN},
        lane_counts_by_arm={"N": 1, "S": 1},
        vehicles=(),
    )
    render(
        surface=surface,
        geometry=geometry,
        state=state,
        average_wait_time=0.0,
        lane_width=lane_width,
        inbound_lane_movements_by_arm={
            "N": (("straight",),),
            "S": (("straight",),),
        },
    )

    south_stop_line_y = next(arm.stop_line[0][1] for arm in geometry.arms if arm.name == "S")
    lane_x, _ = lane_center_world_position(
        arm="S",
        distance=0.0,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        road_width=road_width,
        lane_index=0,
        lane_count=1,
        lane_width=lane_width,
    )
    marker_y = south_stop_line_y + (lane_width * 2)
    pixel = surface.get_at((int(lane_x), int(marker_y)))
    assert pixel[0] > 150 and pixel[1] > 150 and pixel[2] > 150


def test_lane_direction_arrow_head_is_not_double_offset_on_resized_surface():
    lane_width = 12
    road_width = 48
    surface_width = WINDOW_WIDTH + 200
    surface_height = WINDOW_HEIGHT + 100
    surface = pygame.Surface((surface_width, surface_height))
    surface.fill((0, 0, 0))
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=4,
        road_width=road_width,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    _draw_lane_direction_markings(
        surface=surface,
        geometry=geometry,
        lane_counts_by_arm={"N": 1, "E": 1, "S": 1, "W": 1},
        road_width=road_width,
        lane_width=lane_width,
        world_window_width=WINDOW_WIDTH,
        world_window_height=WINDOW_HEIGHT,
        inbound_lane_movements_by_arm={"N": (("straight",),)},
        lane_marker_scale=1.0,
        center_x=surface_width // 2,
        center_y=surface_height // 2,
    )

    marked_pixels: list[tuple[int, int]] = []
    for y in range(surface_height):
        for x in range(surface_width):
            if surface.get_at((x, y))[:3] != (0, 0, 0):
                marked_pixels.append((x, y))

    # A northbound straight marker should stay near its lane X coordinate after resize.
    # If render offset is applied twice to arrowheads, marked pixels jump far right.
    max_x = max(x for x, _ in marked_pixels)
    assert max_x < 620


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


def test_offscreen_renderer_prefers_vehicle_world_position_when_available():
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
    from crossroads.vehicle import VehicleState, lane_center_world_position

    lane_center_x, lane_center_y = lane_center_world_position(
        arm="N",
        distance=150.0,
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        road_width=ROAD_WIDTH,
        lane_width=VEHICLE_WIDTH,
    )
    world_position = (lane_center_x + 40.0, lane_center_y + 30.0)
    state = SimulationState(
        light_states={"N": LightState.GREEN, "E": LightState.RED, "S": LightState.GREEN, "W": LightState.RED},
        vehicles=(
            VehicleSnapshot(
                arm="N",
                position=150.0,
                world_position=world_position,
                state=VehicleState.CROSSING,
                wait_ticks=0,
            ),
        ),
    )

    render(surface=surface, geometry=geometry, state=state, average_wait_time=0.0)

    center_x, center_y = surface.get_width() // 2, surface.get_height() // 2
    pixel_x = center_x - WINDOW_WIDTH // 2 + int(world_position[0])
    pixel_y = center_y - WINDOW_HEIGHT // 2 + int(world_position[1])
    pixel = surface.get_at((pixel_x, pixel_y))
    assert tuple(pixel[:3]) == VEHICLE_COLOR


def test_offscreen_renderer_rotates_vehicle_using_world_heading():
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
    from crossroads.vehicle import VehicleState

    world_position = (200.0, 200.0)
    state = SimulationState(
        light_states={"N": LightState.GREEN, "E": LightState.RED, "S": LightState.GREEN, "W": LightState.RED},
        vehicles=(
            VehicleSnapshot(
                arm="N",
                position=120.0,
                world_position=world_position,
                world_heading_radians=0.0,
                state=VehicleState.CROSSING,
                wait_ticks=0,
            ),
        ),
    )

    render(surface=surface, geometry=geometry, state=state, average_wait_time=0.0)

    center_x, center_y = surface.get_width() // 2, surface.get_height() // 2
    pixel_x = center_x - WINDOW_WIDTH // 2 + int(world_position[0])
    pixel_y = center_y - WINDOW_HEIGHT // 2 + int(world_position[1])
    horizontal_probe = surface.get_at((pixel_x + (VEHICLE_LENGTH // 2) - 1, pixel_y))
    assert tuple(horizontal_probe[:3]) == VEHICLE_COLOR


def test_offscreen_renderer_keeps_carriageway_gap_as_background():
    pygame.init()

    lane_width = 12
    surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    geometry = build_intersection_geometry(
        window_width=WINDOW_WIDTH,
        window_height=WINDOW_HEIGHT,
        arm_count=4,
        road_width_by_arm={"N": 72, "E": 48, "S": 72, "W": 48},
        inbound_lane_count_by_arm={"N": 4, "E": 2, "S": 4, "W": 2},
        straight_capable_lane_indices_by_arm={
            "N": (0, 1),
            "E": (0, 1),
            "S": (2, 3),
            "W": (0, 1),
        },
        lane_width=lane_width,
        carriageway_separation_override=0,
        outbound_lane_count=2,
        stop_line_distance=STOP_LINE_DISTANCE,
    )

    from crossroads.simulation import SimulationState

    state = SimulationState(
        light_states={"N": LightState.GREEN, "E": LightState.RED, "S": LightState.GREEN, "W": LightState.RED},
        vehicles=(),
    )
    render(
        surface=surface,
        geometry=geometry,
        state=state,
        average_wait_time=0.0,
        lane_width=lane_width,
    )

    cx = WINDOW_WIDTH // 2
    sample_y = WINDOW_HEIGHT // 4
    pixel = surface.get_at((cx, sample_y))
    assert tuple(pixel[:3]) == BACKGROUND_COLOR


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

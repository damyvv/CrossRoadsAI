import pytest

from crossroads import config as legacy_config
from crossroads.runtime_config import load_runtime_config, resolve_runtime_config


def test_load_runtime_config_from_yaml(tmp_path):
    config_path = tmp_path / "simulation.yaml"
    config_path.write_text(
        "\n".join(
            [
                "window_width: 800",
                "window_height: 600",
                "arm_count: 4",
                "road_width: 110",
                "stop_line_distance: 65",
                "green_duration_ticks: 120",
                "yellow_duration_ticks: 45",
                "simulation_ticks_per_second: 60",
                "vehicle_top_speed: 4.5",
                "vehicle_acceleration: 0.25",
                "vehicle_deceleration: 0.35",
                "vehicle_length: 26",
                "vehicle_width: 11",
                "vehicle_queue_gap: 7",
                "vehicle_stop_distance_before_line: 9.0",
                "vehicle_spawn_rate_per_second: 1.5",
                "vehicle_spawn_rate_per_second_by_arm:",
                "  N: 2.0",
                "  E: 1.0",
                "vehicle_spawn_seed: 123",
            ]
        )
    )

    runtime_config = load_runtime_config(config_path)

    assert runtime_config.window_width == 800
    assert runtime_config.window_height == 600
    assert runtime_config.arm_count == 4
    assert runtime_config.road_width == 110
    assert runtime_config.stop_line_distance == 65
    assert runtime_config.green_duration_ticks == 120
    assert runtime_config.yellow_duration_ticks == 45
    assert runtime_config.simulation_ticks_per_second == 60
    assert runtime_config.vehicle_top_speed == 4.5
    assert runtime_config.vehicle_acceleration == 0.25
    assert runtime_config.vehicle_deceleration == 0.35
    assert runtime_config.vehicle_length == 26
    assert runtime_config.vehicle_width == 11
    assert runtime_config.vehicle_queue_gap == 7
    assert runtime_config.vehicle_stop_distance_before_line == 9.0
    assert runtime_config.vehicle_spawn_rate_per_second == 1.5
    assert runtime_config.vehicle_spawn_rate_per_second_by_arm == {"N": 2.0, "E": 1.0}
    assert runtime_config.vehicle_spawn_seed == 123


def test_load_runtime_config_rejects_unknown_key(tmp_path):
    config_path = tmp_path / "simulation.yaml"
    config_path.write_text(
        "\n".join(
            [
                "window_width: 960",
                "window_height: 720",
                "arm_count: 4",
                "road_width: 120",
                "stop_line_distance: 70",
                "green_duration_ticks: 150",
                "yellow_duration_ticks: 60",
                "simulation_ticks_per_second: 60",
                "vehicle_top_speed: 4.0",
                "vehicle_acceleration: 0.20",
                "vehicle_deceleration: 0.30",
                "vehicle_length: 24",
                "vehicle_width: 12",
                "vehicle_queue_gap: 8",
                "vehicle_stop_distance_before_line: 10.0",
                "vehicle_spawn_rate_per_second: 2.0",
                "vehicle_spawn_seed: 7",
                "unexpected_key: true",
            ]
        )
    )

    with pytest.raises(ValueError, match="unknown key: unexpected_key"):
        load_runtime_config(config_path)


def test_load_runtime_config_requires_deterministic_seed(tmp_path):
    config_path = tmp_path / "simulation.yaml"
    config_path.write_text(
        "\n".join(
            [
                "window_width: 960",
                "window_height: 720",
                "arm_count: 4",
                "road_width: 120",
                "stop_line_distance: 70",
                "green_duration_ticks: 150",
                "yellow_duration_ticks: 60",
                "simulation_ticks_per_second: 60",
                "vehicle_top_speed: 4.0",
                "vehicle_acceleration: 0.20",
                "vehicle_deceleration: 0.30",
                "vehicle_length: 24",
                "vehicle_width: 12",
                "vehicle_queue_gap: 8",
                "vehicle_stop_distance_before_line: 10.0",
                "vehicle_spawn_rate_per_second: 2.0",
            ]
        )
    )

    with pytest.raises(ValueError, match="missing required key: vehicle_spawn_seed"):
        load_runtime_config(config_path)


def test_resolve_runtime_config_falls_back_to_legacy_constants(tmp_path):
    runtime_config = resolve_runtime_config(
        config_path=None,
        default_path=tmp_path / "missing-simulation.yaml",
    )

    assert runtime_config.window_width == legacy_config.WINDOW_WIDTH
    assert runtime_config.window_height == legacy_config.WINDOW_HEIGHT
    assert runtime_config.arm_count == legacy_config.ARM_COUNT
    assert runtime_config.vehicle_spawn_seed == legacy_config.VEHICLE_SPAWN_SEED

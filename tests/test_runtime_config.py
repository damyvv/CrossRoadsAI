import pytest

from crossroads import config as legacy_config
from crossroads.runtime_config import load_runtime_config, resolve_runtime_config


def test_load_runtime_config_from_nested_yaml_with_optional_arm_spawn_rates(tmp_path):
    """Parse nested YAML with optional per-arm spawn rates."""
    config_path = tmp_path / "simulation.yaml"
    config_path.write_text(
        "\n".join(
            [
                "window:",
                "  width: 960",
                "  height: 720",
                "intersection:",
                "  arm_count: 4",
                "road:",
                "  width: 120",
                "  stop_line_distance: 70",
                "vehicle:",
                "  top_speed: 4.0",
                "  acceleration: 0.2",
                "  deceleration: 0.3",
                "  length: 24",
                "  width: 12",
                "  queue_gap: 8",
                "  stop_distance_before_line: 10.0",
                "  spawn_rate_per_second: 2.0",
                "  spawn_rate_per_second_by_arm:",
                "    N: 3.0",
                "    S: 1.0",
                "simulation:",
                "  green_duration_ticks: 150",
                "  yellow_duration_ticks: 60",
                "  ticks_per_second: 60",
                "  vehicle_spawn_seed: 42",
            ]
        )
    )

    runtime_config = load_runtime_config(config_path)

    # Verify nested key-to-flat key mapping for representative fields
    assert runtime_config.window_width == 960
    assert runtime_config.window_height == 720
    assert runtime_config.arm_count == 4
    assert runtime_config.road_width == 120
    assert runtime_config.stop_line_distance == 70
    assert runtime_config.vehicle_top_speed == 4.0
    assert runtime_config.vehicle_spawn_seed == 42
    assert runtime_config.simulation_ticks_per_second == 60
    assert runtime_config.vehicle_spawn_rate_per_second_by_arm == {"N": 3.0, "S": 1.0}


def test_load_runtime_config_from_nested_yaml_rejects_non_mapping_section(tmp_path):
    """Nested YAML section must be a mapping, not a scalar."""
    config_path = tmp_path / "simulation.yaml"
    config_path.write_text(
        "\n".join(
            [
                "window: not_a_mapping",
                "intersection:",
                "  arm_count: 4",
            ]
        )
    )

    with pytest.raises(ValueError, match="window must be a mapping"):
        load_runtime_config(config_path)


def test_load_runtime_config_from_nested_yaml_structure_rejects_unknown_key(tmp_path):
    """Reject unknown top-level keys in nested YAML structure."""
    config_path = tmp_path / "simulation.yaml"
    config_path.write_text(
        "\n".join(
            [
                "window:",
                "  width: 960",
                "  height: 720",
                "intersection:",
                "  arm_count: 4",
                "road:",
                "  width: 120",
                "  stop_line_distance: 70",
                "vehicle:",
                "  top_speed: 4.0",
                "  acceleration: 0.2",
                "  deceleration: 0.3",
                "  length: 24",
                "  width: 12",
                "  queue_gap: 8",
                "  stop_distance_before_line: 10.0",
                "  spawn_rate_per_second: 2.0",
                "simulation:",
                "  green_duration_ticks: 150",
                "  yellow_duration_ticks: 60",
                "  ticks_per_second: 60",
                "  vehicle_spawn_seed: 42",
                "unknown_section:",
                "  foo: bar",
            ]
        )
    )

    with pytest.raises(ValueError, match="unknown key"):
        load_runtime_config(config_path)


def test_load_runtime_config_from_nested_yaml_rejects_unknown_keys_in_section(tmp_path):
    """Reject unknown keys within a nested section."""
    config_path = tmp_path / "simulation.yaml"
    config_path.write_text(
        "\n".join(
            [
                "window:",
                "  width: 960",
                "  height: 720",
                "  typo_key: 123",
                "intersection:",
                "  arm_count: 4",
                "road:",
                "  width: 120",
                "  stop_line_distance: 70",
                "vehicle:",
                "  top_speed: 4.0",
                "  acceleration: 0.2",
                "  deceleration: 0.3",
                "  length: 24",
                "  width: 12",
                "  queue_gap: 8",
                "  stop_distance_before_line: 10.0",
                "  spawn_rate_per_second: 2.0",
                "simulation:",
                "  green_duration_ticks: 150",
                "  yellow_duration_ticks: 60",
                "  ticks_per_second: 60",
                "  vehicle_spawn_seed: 42",
            ]
        )
    )

    with pytest.raises(ValueError, match="unknown key in window section"):
        load_runtime_config(config_path)


def test_load_runtime_config_rejects_mixed_nested_and_flat_format(tmp_path):
    """Reject configs that mix nested and flat formats."""
    config_path = tmp_path / "simulation.yaml"
    config_path.write_text(
        "\n".join(
            [
                "window_width: 960",
                "window_height: 720",
                "intersection:",
                "  arm_count: 4",
            ]
        )
    )

    with pytest.raises(ValueError, match="mixes flat and nested formats"):
        load_runtime_config(config_path)



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


def test_load_runtime_config_rejects_unsupported_arm_count_for_current_slice(tmp_path):
    config_path = tmp_path / "simulation.yaml"
    config_path.write_text(
        "\n".join(
            [
                "window_width: 960",
                "window_height: 720",
                "arm_count: 3",
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
            ]
        )
    )

    with pytest.raises(
        ValueError, match="arm_count must be 4 in this slice; topology YAML support lands in #25"
    ):
        load_runtime_config(config_path)

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


def test_load_runtime_config_rejects_flat_format(tmp_path):
    """Flat format is not supported - only nested format with sections is allowed."""
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
                "vehicle_spawn_seed: 42",
            ]
        )
    )

    with pytest.raises(ValueError, match="unknown key"):
        load_runtime_config(config_path)


def test_load_runtime_config_reports_missing_section(tmp_path):
    """Report missing entire section with helpful message."""
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
            ]
        )
    )

    with pytest.raises(ValueError, match="missing section 'simulation'"):
        load_runtime_config(config_path)


def test_load_runtime_config_reports_missing_key_in_section(tmp_path):
    """Report missing required key within section with helpful message."""
    config_path = tmp_path / "simulation.yaml"
    config_path.write_text(
        "\n".join(
            [
                "window:",
                "  width: 960",
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

    with pytest.raises(ValueError, match="missing key 'height' in window section"):
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


# ============ TDD tests for #25: Topology and explicit Phase schedule ============

def test_load_topology_4arm_from_yaml(tmp_path):
    """Parse 4-arm topology without missing_arm."""
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
            ]
        )
    )

    runtime_config = load_runtime_config(config_path)

    assert runtime_config.arm_count == 4
    assert runtime_config.missing_arm is None


def test_load_topology_3arm_from_yaml_with_missing_arm(tmp_path):
    """Parse 3-arm topology with missing_arm specified."""
    config_path = tmp_path / "simulation.yaml"
    config_path.write_text(
        "\n".join(
            [
                "window:",
                "  width: 960",
                "  height: 720",
                "intersection:",
                "  arm_count: 3",
                "  missing_arm: N",
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

    runtime_config = load_runtime_config(config_path)

    assert runtime_config.arm_count == 3
    assert runtime_config.missing_arm == "N"


def test_load_phases_from_yaml(tmp_path):
    """Parse explicit phase schedule from YAML."""
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
                "phases:",
                "  - arms: [N, S]",
                "    name: NS",
                "  - arms: [E, W]",
                "    name: EW",
            ]
        )
    )

    runtime_config = load_runtime_config(config_path)

    assert len(runtime_config.phases) == 2
    assert runtime_config.phases[0].arms == ("N", "S")
    assert runtime_config.phases[0].name == "NS"
    assert runtime_config.phases[1].arms == ("E", "W")
    assert runtime_config.phases[1].name == "EW"


def test_reject_phase_with_invalid_arm_for_topology(tmp_path):
    """Reject phases that include arms not in topology."""
    config_path = tmp_path / "simulation.yaml"
    config_path.write_text(
        "\n".join(
            [
                "window:",
                "  width: 960",
                "  height: 720",
                "intersection:",
                "  arm_count: 3",
                "  missing_arm: N",
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
                "phases:",
                "  - arms: [N, S]",
                "    name: NS",
            ]
        )
    )

    with pytest.raises(ValueError, match="invalid arm .* in phase .* for topology"):
        load_runtime_config(config_path)


def test_reject_missing_arm_when_arm_count_is_3(tmp_path):
    config_path = tmp_path / "simulation.yaml"
    config_path.write_text(
        "\n".join(
            [
                "window:",
                "  width: 960",
                "  height: 720",
                "intersection:",
                "  arm_count: 3",
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

    with pytest.raises(ValueError, match="intersection.missing_arm is required when arm_count is 3"):
        load_runtime_config(config_path)


def test_reject_missing_arm_when_arm_count_is_not_3(tmp_path):
    config_path = tmp_path / "simulation.yaml"
    config_path.write_text(
        "\n".join(
            [
                "window:",
                "  width: 960",
                "  height: 720",
                "intersection:",
                "  arm_count: 4",
                "  missing_arm: N",
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

    with pytest.raises(ValueError, match="intersection.missing_arm is only allowed when arm_count is 3"):
        load_runtime_config(config_path)


def test_reject_top_level_topology_section(tmp_path):
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
                "topology:",
                "  missing_arm: N",
            ]
        )
    )

    with pytest.raises(ValueError, match="unknown key: topology"):
        load_runtime_config(config_path)


def test_reject_spawn_rate_for_missing_arm_in_three_arm_topology(tmp_path):
    config_path = tmp_path / "simulation.yaml"
    config_path.write_text(
        "\n".join(
            [
                "window:",
                "  width: 960",
                "  height: 720",
                "intersection:",
                "  arm_count: 3",
                "  missing_arm: N",
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
                "    N: 1.0",
                "simulation:",
                "  green_duration_ticks: 150",
                "  yellow_duration_ticks: 60",
                "  ticks_per_second: 60",
                "  vehicle_spawn_seed: 42",
            ]
        )
    )

    with pytest.raises(ValueError, match="unknown arm in vehicle_spawn_rate_per_second_by_arm: N"):
        load_runtime_config(config_path)


def test_reject_phases_missing_topology_arms(tmp_path):
    config_path = tmp_path / "simulation.yaml"
    config_path.write_text(
        "\n".join(
            [
                "window:",
                "  width: 960",
                "  height: 720",
                "intersection:",
                "  arm_count: 3",
                "  missing_arm: N",
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
                "phases:",
                "  - arms: [E, W]",
                "    name: EW",
            ]
        )
    )

    with pytest.raises(ValueError, match=r"missing arms from phases: \['S'\]"):
        load_runtime_config(config_path)


def test_reject_duplicate_arms_across_phases(tmp_path):
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
                "phases:",
                "  - arms: [N, S]",
                "    name: NS",
                "  - arms: [N, E, W]",
                "    name: NEW",
            ]
        )
    )

    with pytest.raises(ValueError, match=r"duplicate arms across phases: \['N'\]"):
        load_runtime_config(config_path)

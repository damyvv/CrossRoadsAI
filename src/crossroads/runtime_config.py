from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from crossroads import config as legacy_config
from crossroads.traffic_phasing import ArmPhase, validate_phase_schedule


@dataclass(frozen=True)
class RuntimeConfig:
    window_width: int
    window_height: int
    arm_count: int
    missing_arm: str | None
    road_width: int
    stop_line_distance: int
    green_duration_ticks: int
    yellow_duration_ticks: int
    simulation_ticks_per_second: int
    vehicle_top_speed: float
    vehicle_acceleration: float
    vehicle_deceleration: float
    vehicle_length: int
    vehicle_width: int
    vehicle_queue_gap: int
    vehicle_stop_distance_before_line: float
    vehicle_spawn_rate_per_second: float
    vehicle_spawn_rate_per_second_by_arm: dict[str, float] | None
    vehicle_spawn_seed: int
    phases: tuple[ArmPhase, ...]


_REQUIRED_KEYS = {
    "window_width",
    "window_height",
    "arm_count",
    "road_width",
    "stop_line_distance",
    "green_duration_ticks",
    "yellow_duration_ticks",
    "simulation_ticks_per_second",
    "vehicle_top_speed",
    "vehicle_acceleration",
    "vehicle_deceleration",
    "vehicle_length",
    "vehicle_width",
    "vehicle_queue_gap",
    "vehicle_stop_distance_before_line",
    "vehicle_spawn_rate_per_second",
    "vehicle_spawn_seed",
}
_OPTIONAL_KEYS = {"missing_arm", "vehicle_spawn_rate_per_second_by_arm", "_phases_data"}
_ALLOWED_KEYS = _REQUIRED_KEYS | _OPTIONAL_KEYS
_VALID_ARMS_BY_COUNT = {
    2: {"N", "S"},
    3: {"N", "E", "S", "W"},
    4: {"N", "E", "S", "W"},
}
_SUPPORTED_ARM_COUNTS = {4}

_NESTED_SECTIONS = {
    "window": {
        "width": "window_width",
        "height": "window_height",
    },
    "intersection": {
        "arm_count": "arm_count",
    },
    "road": {
        "width": "road_width",
        "stop_line_distance": "stop_line_distance",
    },
    "vehicle": {
        "top_speed": "vehicle_top_speed",
        "acceleration": "vehicle_acceleration",
        "deceleration": "vehicle_deceleration",
        "length": "vehicle_length",
        "width": "vehicle_width",
        "queue_gap": "vehicle_queue_gap",
        "stop_distance_before_line": "vehicle_stop_distance_before_line",
        "spawn_rate_per_second": "vehicle_spawn_rate_per_second",
    },
    "simulation": {
        "green_duration_ticks": "green_duration_ticks",
        "yellow_duration_ticks": "yellow_duration_ticks",
        "ticks_per_second": "simulation_ticks_per_second",
        "vehicle_spawn_seed": "vehicle_spawn_seed",
    },
}


def _load_raw_yaml(path: Path) -> dict[str, Any]:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise OSError(f"unable to read config file: {path}") from exc

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise ValueError(f"invalid YAML in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("configuration must be a YAML mapping at the top level")
    return data


def _flatten_nested_yaml(data: dict[str, Any]) -> dict[str, Any]:
    """Flatten nested YAML structure into flat structure.
    
    Converts nested format to flat structure. Phases are handled separately
    as they have special parsing logic.
    
    Converts nested format:
      window:
        width: 960
        height: 720
    To:
      window_width: 960
      window_height: 720
    
    Validates that all required nested keys are present with helpful error messages.
    """
    top_level_keys = set(data.keys())
    # phases is optional, not in _NESTED_SECTIONS
    nested_section_keys = set(_NESTED_SECTIONS.keys())
    allowed_top_level = nested_section_keys | {"phases"}
    
    # Validate no unknown sections
    unknown_sections = sorted(top_level_keys - allowed_top_level)
    if unknown_sections:
        raise ValueError(f"unknown key: {unknown_sections[0]}")
    
    # Validate required keys are present in their sections before flattening
    # This gives better error messages than the flat validation
    # Iterate in insertion order (not alphabetical) to match user expectations
    required_sections_ordered = list(_NESTED_SECTIONS.keys())
    
    # First pass: validate all required sections exist and are mappings
    for section in required_sections_ordered:
        if section not in data:
            key_mapping = _NESTED_SECTIONS[section]
            raise ValueError(f"missing section '{section}' in config; required keys: {', '.join(sorted(key_mapping.keys()))}")
        
        section_data = data[section]
        if not isinstance(section_data, dict):
            raise ValueError(f"{section} must be a mapping")
    
    # Second pass: validate content of each section
    for section in required_sections_ordered:
        section_data = data[section]
        key_mapping = _NESTED_SECTIONS[section]
        
        # Validate no unknown keys within the section
        # Special cases for optional keys in sections
        allowed_nested_keys = set(key_mapping.keys())
        if section == "intersection":
            allowed_nested_keys.add("missing_arm")
        if section == "vehicle":
            allowed_nested_keys.add("spawn_rate_per_second_by_arm")
        
        unknown_nested_keys = sorted(set(section_data.keys()) - allowed_nested_keys)
        if unknown_nested_keys:
            raise ValueError(f"unknown key in {section} section: {unknown_nested_keys[0]}")
        
        # Validate that required keys within the section are present
        missing_keys = sorted(set(key_mapping.keys()) - set(section_data.keys()))
        if missing_keys:
            raise ValueError(f"missing key '{missing_keys[0]}' in {section} section; required keys: {', '.join(sorted(key_mapping.keys()))}")
    
    # Flatten each required section
    flat = {}
    for section in required_sections_ordered:
        section_data = data[section]
        key_mapping = _NESTED_SECTIONS[section]
        # Flatten the section
        for nested_key, flat_key in key_mapping.items():
            if nested_key in section_data:
                flat[flat_key] = section_data[nested_key]
    
    # Handle optional vehicle_spawn_rate_per_second_by_arm if it exists in vehicle section
    if "vehicle" in data and isinstance(data["vehicle"], dict):
        if "spawn_rate_per_second_by_arm" in data["vehicle"]:
            flat["vehicle_spawn_rate_per_second_by_arm"] = data["vehicle"]["spawn_rate_per_second_by_arm"]
    
    # Handle optional intersection.missing_arm if provided
    if "intersection" in data and isinstance(data["intersection"], dict):
        if "missing_arm" in data["intersection"]:
            flat["missing_arm"] = data["intersection"]["missing_arm"]

    # Store phases raw data for later parsing
    if "phases" in data:
        flat["_phases_data"] = data["phases"]
    
    return flat



def _require_key(data: Mapping[str, Any], key: str) -> Any:
    if key not in data:
        raise ValueError(f"missing required key: {key}")
    return data[key]


def _validate_known_keys(data: Mapping[str, Any]) -> None:
    unknown_keys = sorted(set(data) - _ALLOWED_KEYS)
    if unknown_keys:
        raise ValueError(f"unknown key: {unknown_keys[0]}")


def _parse_int(
    data: Mapping[str, Any],
    key: str,
    *,
    minimum: int | None = None,
    allowed: set[int] | None = None,
) -> int:
    value = _require_key(data, key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{key} must be an integer")
    if minimum is not None and value < minimum:
        raise ValueError(f"{key} must be >= {minimum}")
    if allowed is not None and value not in allowed:
        allowed_values = ", ".join(str(item) for item in sorted(allowed))
        raise ValueError(f"{key} must be one of: {allowed_values}")
    return value


def _parse_float(
    data: Mapping[str, Any],
    key: str,
    *,
    minimum: float | None = None,
) -> float:
    value = _require_key(data, key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a number")
    parsed = float(value)
    if minimum is not None and parsed < minimum:
        raise ValueError(f"{key} must be >= {minimum}")
    return parsed


def _topology_arms(*, arm_count: int, missing_arm: str | None) -> set[str]:
    arms = set(_VALID_ARMS_BY_COUNT[arm_count])
    if arm_count == 3:
        assert missing_arm is not None
        arms.remove(missing_arm)
    return arms


def _parse_spawn_rates_by_arm(
    data: Mapping[str, Any],
    *,
    arm_count: int,
    missing_arm: str | None,
) -> dict[str, float] | None:
    if "vehicle_spawn_rate_per_second_by_arm" not in data:
        return None

    rates = data["vehicle_spawn_rate_per_second_by_arm"]
    if rates is None:
        return None
    if not isinstance(rates, dict):
        raise ValueError("vehicle_spawn_rate_per_second_by_arm must be a mapping")

    valid_arms = _topology_arms(arm_count=arm_count, missing_arm=missing_arm)
    parsed: dict[str, float] = {}
    for arm, value in rates.items():
        if not isinstance(arm, str):
            raise ValueError("vehicle_spawn_rate_per_second_by_arm keys must be arm strings")
        if arm not in valid_arms:
            raise ValueError(f"unknown arm in vehicle_spawn_rate_per_second_by_arm: {arm}")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(
                f"vehicle_spawn_rate_per_second_by_arm[{arm}] must be a non-negative number"
            )
        parsed_value = float(value)
        if parsed_value < 0:
            raise ValueError(
                f"vehicle_spawn_rate_per_second_by_arm[{arm}] must be a non-negative number"
            )
        parsed[arm] = parsed_value
    return parsed


def _parse_missing_arm(data: Mapping[str, Any], *, arm_count: int) -> str | None:
    if "missing_arm" not in data:
        if arm_count == 3:
            raise ValueError("intersection.missing_arm is required when arm_count is 3")
        return None

    if arm_count != 3:
        raise ValueError("intersection.missing_arm is only allowed when arm_count is 3")

    missing_arm = data["missing_arm"]
    if not isinstance(missing_arm, str):
        raise ValueError("intersection.missing_arm must be a string")

    valid_arms = _VALID_ARMS_BY_COUNT[3]
    if missing_arm not in valid_arms:
        raise ValueError(f"invalid intersection.missing_arm '{missing_arm}' for arm_count {arm_count}")
    
    return missing_arm


def _parse_phases(data: Mapping[str, Any], *, arm_count: int, missing_arm: str | None) -> tuple[ArmPhase, ...]:
    """Parse phases from YAML. If not specified, returns default phases for topology."""
    if "_phases_data" not in data:
        # Return default phases based on arm_count
        if arm_count == 4:
            return (
                ArmPhase(arms=("N", "S"), name="NS"),
                ArmPhase(arms=("E", "W"), name="EW"),
            )
        elif arm_count == 3:
            remaining_arms = tuple(sorted(_topology_arms(arm_count=arm_count, missing_arm=missing_arm)))
            phase_name = "".join(remaining_arms)
            return (ArmPhase(arms=remaining_arms, name=phase_name),)
        elif arm_count == 2:
            return (ArmPhase(arms=("N", "S"), name="NS"),)
        return ()
    
    phases_data = data["_phases_data"]
    if not isinstance(phases_data, list):
        raise ValueError("phases must be a list")
    
    # Determine valid arms for this topology
    valid_arms = _topology_arms(arm_count=arm_count, missing_arm=missing_arm)
    
    parsed_phases: list[ArmPhase] = []
    for i, phase_item in enumerate(phases_data):
        if not isinstance(phase_item, dict):
            raise ValueError(f"phase {i} must be a mapping")
        
        if "arms" not in phase_item:
            raise ValueError(f"phase {i} is missing required key 'arms'")
        if "name" not in phase_item:
            raise ValueError(f"phase {i} is missing required key 'name'")
        
        arms = phase_item["arms"]
        name = phase_item["name"]
        
        if not isinstance(arms, list):
            raise ValueError(f"phase {i} arms must be a list")
        if not isinstance(name, str):
            raise ValueError(f"phase {i} name must be a string")
        
        # Validate each arm in the phase
        for arm in arms:
            if not isinstance(arm, str):
                raise ValueError(f"phase {i} arms must be strings")
            if arm not in valid_arms:
                raise ValueError(f"invalid arm '{arm}' in phase '{name}' for topology arm_count={arm_count}, missing_arm={missing_arm}")

        parsed_phases.append(ArmPhase(arms=tuple(arms), name=name))
    
    if not parsed_phases:
        raise ValueError("phases list cannot be empty")
    return validate_phase_schedule(
        arm_names=sorted(valid_arms),
        phases=parsed_phases,
        require_full_coverage=True,
    )


def _from_mapping(data: Mapping[str, Any]) -> RuntimeConfig:
    _validate_known_keys(data)
    arm_count = _parse_int(data, "arm_count", allowed={2, 3, 4})
    
    missing_arm = _parse_missing_arm(data, arm_count=arm_count)
    
    # Parse phases
    phases = _parse_phases(data, arm_count=arm_count, missing_arm=missing_arm)
    
    spawn_rates_by_arm = _parse_spawn_rates_by_arm(
        data,
        arm_count=arm_count,
        missing_arm=missing_arm,
    )

    return RuntimeConfig(
        window_width=_parse_int(data, "window_width", minimum=1),
        window_height=_parse_int(data, "window_height", minimum=1),
        arm_count=arm_count,
        missing_arm=missing_arm,
        road_width=_parse_int(data, "road_width", minimum=1),
        stop_line_distance=_parse_int(data, "stop_line_distance", minimum=0),
        green_duration_ticks=_parse_int(data, "green_duration_ticks", minimum=1),
        yellow_duration_ticks=_parse_int(data, "yellow_duration_ticks", minimum=1),
        simulation_ticks_per_second=_parse_int(data, "simulation_ticks_per_second", minimum=1),
        vehicle_top_speed=_parse_float(data, "vehicle_top_speed", minimum=0.0),
        vehicle_acceleration=_parse_float(data, "vehicle_acceleration", minimum=0.0),
        vehicle_deceleration=_parse_float(data, "vehicle_deceleration", minimum=0.0),
        vehicle_length=_parse_int(data, "vehicle_length", minimum=1),
        vehicle_width=_parse_int(data, "vehicle_width", minimum=1),
        vehicle_queue_gap=_parse_int(data, "vehicle_queue_gap", minimum=0),
        vehicle_stop_distance_before_line=_parse_float(
            data, "vehicle_stop_distance_before_line", minimum=0.0
        ),
        vehicle_spawn_rate_per_second=_parse_float(data, "vehicle_spawn_rate_per_second", minimum=0.0),
        vehicle_spawn_rate_per_second_by_arm=spawn_rates_by_arm,
        vehicle_spawn_seed=_parse_int(data, "vehicle_spawn_seed"),
        phases=phases,
    )


def load_runtime_config(path: Path | str) -> RuntimeConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"config file not found: {config_path}")
    raw_data = _load_raw_yaml(config_path)
    flattened_data = _flatten_nested_yaml(raw_data)
    return _from_mapping(flattened_data)


def legacy_runtime_config() -> RuntimeConfig:
    if legacy_config.VEHICLE_SPAWN_SEED is None:
        raise ValueError(
            "config.py fallback requires VEHICLE_SPAWN_SEED to be set during YAML transition"
        )
    if legacy_config.ARM_COUNT not in _SUPPORTED_ARM_COUNTS:
        raise ValueError("config.py fallback currently supports ARM_COUNT=4 only")
    return RuntimeConfig(
        window_width=legacy_config.WINDOW_WIDTH,
        window_height=legacy_config.WINDOW_HEIGHT,
        arm_count=legacy_config.ARM_COUNT,
        missing_arm=None,
        road_width=legacy_config.ROAD_WIDTH,
        stop_line_distance=legacy_config.STOP_LINE_DISTANCE,
        green_duration_ticks=legacy_config.GREEN_DURATION_TICKS,
        yellow_duration_ticks=legacy_config.YELLOW_DURATION_TICKS,
        simulation_ticks_per_second=legacy_config.SIMULATION_TICKS_PER_SECOND,
        vehicle_top_speed=legacy_config.VEHICLE_TOP_SPEED,
        vehicle_acceleration=legacy_config.VEHICLE_ACCELERATION,
        vehicle_deceleration=legacy_config.VEHICLE_DECELERATION,
        vehicle_length=legacy_config.VEHICLE_LENGTH,
        vehicle_width=legacy_config.VEHICLE_WIDTH,
        vehicle_queue_gap=legacy_config.VEHICLE_QUEUE_GAP,
        vehicle_stop_distance_before_line=legacy_config.VEHICLE_STOP_DISTANCE_BEFORE_LINE,
        vehicle_spawn_rate_per_second=legacy_config.VEHICLE_SPAWN_RATE_PER_SECOND,
        vehicle_spawn_rate_per_second_by_arm=legacy_config.VEHICLE_SPAWN_RATE_PER_SECOND_BY_ARM,
        vehicle_spawn_seed=legacy_config.VEHICLE_SPAWN_SEED,
        phases=(
            ArmPhase(arms=("N", "S"), name="NS"),
            ArmPhase(arms=("E", "W"), name="EW"),
        ),
    )


def resolve_runtime_config(
    *,
    config_path: Path | str | None,
    default_path: Path | str | None = None,
) -> RuntimeConfig:
    if config_path is not None:
        return load_runtime_config(config_path)

    yaml_path = Path(default_path) if default_path is not None else Path("config/simulation.yaml")
    if yaml_path.exists():
        return load_runtime_config(yaml_path)

    return legacy_runtime_config()

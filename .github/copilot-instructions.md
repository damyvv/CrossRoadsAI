# Copilot Instructions: CrossRoadsAI

## Project Overview

**CrossRoadsAI** is a traffic intersection simulation using pygame. It models a configurable intersection (2-4 arms) with coordinated traffic light control via phasing logic.

- **Entry point**: `main.py` — parses `--max-frames` argument for headless testing
- **Visualization**: pygame window showing roads, stop lines, and traffic light state
- **Core simulation**: `src/crossroads/` packages the domain logic

## Architecture

### Key Components

1. **Intersection Geometry** (`src/crossroads/intersection.py`)
   - Computes screen positions for road arms (N/S/E/W or 2-3 arm subsets)
   - Supports arm_count 2, 3, or 4 via `_TOPOLOGIES` dict
   - Returns frozen dataclasses: `ArmGeometry` (per-arm) and `IntersectionGeometry` (full layout)

2. **Traffic Light State Machine** (`src/crossroads/traffic_light.py`)
   - `TrafficLight`: Single light with GREEN→YELLOW→RED cycle; `advance_tick()` transitions states
   - `TrafficLightController`: Manages all lights, enforces phases so only one phase is green at a time
   - **Phase switching rule**: When active phase turns all RED, next phase becomes GREEN

3. **Phasing Logic** (`src/crossroads/traffic_phasing.py`)
   - `ArmPhase`: Frozen dataclass grouping arms that share a green cycle (e.g., N/S together)
   - Standard 4-arm config: `[ArmPhase(["N", "S"], "NS"), ArmPhase(["E", "W"], "EW")]`

4. **Rendering** (`src/crossroads/app.py`)
   - `run(max_frames=None)`: pygame loop; reads config constants, builds geometry, ticks controller
   - Draws roads, stop lines, dashed centerlines, traffic lights as colored circles
   - Resizable window; clock-based frame rate

### Data Flow

```
config.py → app.py (window setup)
         → intersection.py (compute arm positions & roads)
         → traffic_light.py (init controller with phases)
         → each frame: controller.advance_tick() → lights update → pygame renders
```

## Development Workflow

**Build & Run**:
```bash
python main.py              # Interactive pygame window
python main.py --max-frames 60  # 60 frames then exit (CI/smoke tests)
```

**Tests** (TDD vertical-slice pattern):
```bash
pytest tests/               # Run all tests
pytest tests/test_traffic_light.py -v  # Single test file
```

Test philosophy (seen in `tests/test_traffic_light.py`):
- Each test verifies one state transition or phase behavior
- Use small `green_ticks` and `yellow_ticks` for deterministic sequencing
- Mock controller with arm_phases to isolate phasing logic

## Project Conventions

- **Immutability**: Geometry dataclasses use `frozen=True`; intersection is static
- **Tick-based timing**: All durations in ticks (60 FPS assumed). GREEN_DURATION_TICKS=30 → 0.5s green
- **Naming**: Compass directions (N/E/S/W); phases by arm pairs (NS, EW)
- **Constants**: All rendering/timing in `src/crossroads/config.py`; edit there, not in app.py

## Dependencies

- **pygame** (>= 2.5): Rendering only; no game logic dependencies
- **numpy** (>= 1.26): Installed but not used (future sensor data?)
- **pytest** (>= 8): Dev only; run via `pytest`

## Testing Patterns

1. **State machine tests**: Advance tick N times, assert state at each boundary
2. **Phase coordination tests**: Two phases with short durations; verify alternation
3. **No mocking**: Use real TrafficLight/Controller with configurable tick counts

## Integration Points

- **pygame.QUIT**: Exit game loop cleanly
- **pygame.VIDEORESIZE**: Window resize currently supported but intersection not rescaled
- **No I/O**: No config files, no persistent state, no network

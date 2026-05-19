# Agent Instructions: CrossRoadsAI

This file is the single source of truth for agent guidance in this repository.

## Project overview

**CrossRoadsAI** is a traffic intersection simulation using pygame. It models a configurable intersection (2-4 arms) with coordinated traffic light control via phasing logic.

- **Entry point**: `main.py` — parses `--max-frames` argument for headless testing
- **Visualization**: pygame window showing roads, stop lines, and traffic light state
- **Core simulation**: `src/crossroads/` packages the domain logic

## Architecture

### Key components

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

### Data flow

```
config.py → app.py (window setup)
         → intersection.py (compute arm positions & roads)
         → traffic_light.py (init controller with phases)
         → each frame: controller.advance_tick() → lights update → pygame renders
```

## Workflow and execution

### Python environment

- A project virtual environment exists at `.venv`. Agents should use it for running the app and all tests.
- Prefer explicit venv paths (for example `.venv/bin/python`) so commands work without shell activation.

### Verified command examples

```bash
./.venv/bin/python -m pytest tests -q
./.venv/bin/python -m pytest tests/test_traffic_light.py -v
SDL_VIDEODRIVER=dummy ./.venv/bin/python main.py --max-frames 60  # headless smoke test
./.venv/bin/python main.py                                         # interactive run
```

## Commit and PR conventions

- Always use **Conventional Commits** for commit messages (for example: `feat: ...`, `fix: ...`, `docs: ...`).
- If a PR created from an issue will fully resolve that issue, include `Closing #<issue-number>` in the PR body so the issue closes automatically on merge.

## Project conventions

- **Immutability**: Geometry dataclasses use `frozen=True`; intersection is static
- **Tick-based timing**: All durations in ticks (60 FPS assumed). GREEN_DURATION_TICKS=30 → 0.5s green
- **Naming**: Compass directions (N/E/S/W); phases by arm pairs (NS, EW)
- **Constants**: All rendering/timing in `src/crossroads/config.py`; edit there, not in app.py

## Testing patterns

1. **State machine tests**: Advance tick N times, assert state at each boundary
2. **Phase coordination tests**: Two phases with short durations; verify alternation
3. **No mocking**: Use real TrafficLight/Controller with configurable tick counts

## Integration points

- **pygame.QUIT**: Exit game loop cleanly
- **pygame.VIDEORESIZE**: Window resize currently supported but intersection not rescaled
- **No I/O**: No config files, no persistent state, no network

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues for this repository (via `gh`). See `docs/agents/issue-tracker.md`.

### Triage labels

Triage roles use the default label vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Domain docs follow a single-context layout (root `CONTEXT.md` + `docs/adr/`). See `docs/agents/domain.md`.

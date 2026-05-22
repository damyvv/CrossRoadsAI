import os

import pygame

from crossroads import app
from crossroads.runtime_config import resolve_runtime_config
from crossroads.traffic_light import LightState


def test_run_precomputes_lane_paths_for_simulation(monkeypatch):
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    runtime_config = resolve_runtime_config(config_path=None)

    observed = {"received_lane_paths": False}

    class _FakeSimulation:
        def __init__(self, **kwargs):
            lane_paths = kwargs.get("lane_paths_by_lane_movement")
            observed["received_lane_paths"] = bool(lane_paths)

        def state(self):
            from crossroads.simulation import SimulationState

            return SimulationState(light_states={"N": LightState.GREEN}, vehicles=())

        def average_wait_time(self):
            return 0.0

        def advance_tick(self):
            return None

    monkeypatch.setattr(app, "IntersectionSimulation", _FakeSimulation)
    monkeypatch.setattr(app, "render", lambda **_: None)
    monkeypatch.setattr(pygame.display, "flip", lambda: None)

    app.run(max_frames=1, runtime_config=runtime_config)

    assert observed["received_lane_paths"] is True

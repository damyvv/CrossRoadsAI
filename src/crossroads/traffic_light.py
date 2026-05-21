from __future__ import annotations

from enum import Enum, auto

from crossroads.traffic_phasing import ArmPhase, validate_phase_schedule


class LightState(Enum):
    GREEN = auto()
    YELLOW = auto()
    RED = auto()


class TrafficLight:
    """Single traffic light that cycles GREEN → YELLOW → RED and then stays RED."""

    def __init__(self, green_ticks: int, yellow_ticks: int) -> None:
        self._green_ticks = green_ticks
        self._yellow_ticks = yellow_ticks
        self._tick = 0
        self.state = LightState.GREEN

    def advance_tick(self) -> None:
        if self.state == LightState.RED:
            return
        self._tick += 1
        if self.state == LightState.GREEN and self._tick >= self._green_ticks:
            self.state = LightState.YELLOW
            self._tick = 0
        elif self.state == LightState.YELLOW and self._tick >= self._yellow_ticks:
            self.state = LightState.RED
            self._tick = 0

    def reset_to_green(self) -> None:
        self.state = LightState.GREEN
        self._tick = 0


class TrafficLightController:
    """Owns all traffic lights and advances them in round-robin phase order."""

    def __init__(
        self,
        arm_names: list[str],
        phases: list[ArmPhase],
        green_ticks: int,
        yellow_ticks: int,
    ) -> None:
        self._arm_names = set(arm_names)
        self._phases = list(
            validate_phase_schedule(
                arm_names=arm_names,
                phases=phases,
                require_full_coverage=True,
            )
        )
        self._phase_lights: list[TrafficLight] = [
            TrafficLight(green_ticks, yellow_ticks) for _ in self._phases
        ]
        self._active_phase: int = 0
        for i in range(1, len(self._phase_lights)):
            self._phase_lights[i].state = LightState.RED

    def state(self, arm: str) -> LightState:
        if arm not in self._arm_names:
            raise ValueError(f"Unknown arm: {arm!r}")
        active_phase = self._phases[self._active_phase]
        if arm in active_phase.arms:
            return self._phase_lights[self._active_phase].state
        return LightState.RED

    def advance_tick(self) -> None:
        active_light = self._phase_lights[self._active_phase]
        active_light.advance_tick()
        if active_light.state == LightState.RED:
            self._active_phase = (self._active_phase + 1) % len(self._phases)
            self._phase_lights[self._active_phase].reset_to_green()

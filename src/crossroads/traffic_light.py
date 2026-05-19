from __future__ import annotations

from collections import Counter
from enum import Enum, auto

from crossroads.traffic_phasing import ArmPhase


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
        self._validate_phase_coverage(arm_names=arm_names, phases=phases)
        self._phases = phases
        self._phase_lights: list[TrafficLight] = [
            TrafficLight(green_ticks, yellow_ticks) for _ in phases
        ]
        self._active_phase: int = 0
        for i in range(1, len(self._phase_lights)):
            self._phase_lights[i].state = LightState.RED

    def state(self, arm: str) -> LightState:
        for i, phase in enumerate(self._phases):
            if arm in phase.arms:
                return self._phase_lights[i].state
        raise ValueError(f"Unknown arm: {arm!r}")

    def advance_tick(self) -> None:
        active_light = self._phase_lights[self._active_phase]
        active_light.advance_tick()
        if active_light.state == LightState.RED:
            self._active_phase = (self._active_phase + 1) % len(self._phases)
            self._phase_lights[self._active_phase].reset_to_green()

    @staticmethod
    def _validate_phase_coverage(arm_names: list[str], phases: list[ArmPhase]) -> None:
        if not arm_names:
            raise ValueError("arm_names must not be empty")
        if not phases:
            raise ValueError("phases must not be empty")

        known_arms = set(arm_names)
        if len(known_arms) != len(arm_names):
            raise ValueError(f"duplicate arm names in arm_names: {arm_names!r}")

        phase_arms: list[str] = [arm for phase in phases for arm in phase.arms]
        duplicates = sorted(arm for arm, count in Counter(phase_arms).items() if count > 1)
        if duplicates:
            raise ValueError(f"duplicate arms across phases: {duplicates!r}")

        unknown = sorted(set(phase_arms) - known_arms)
        if unknown:
            raise ValueError(f"unknown arms referenced in phases: {unknown!r}")

        missing = sorted(known_arms - set(phase_arms))
        if missing:
            raise ValueError(f"missing arms from phases: {missing!r}")

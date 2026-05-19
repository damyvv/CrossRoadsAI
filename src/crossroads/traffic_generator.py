from __future__ import annotations

from dataclasses import dataclass, field
from math import exp, isfinite
from random import Random
from typing import Mapping


def _sample_poisson(*, lambda_per_tick: float, rng: Random) -> int:
    if not isfinite(lambda_per_tick) or lambda_per_tick < 0:
        raise ValueError("lambda_per_tick must be finite and non-negative")
    if lambda_per_tick == 0.0:
        return 0

    threshold = exp(-lambda_per_tick)
    product = 1.0
    sample_size = 0

    while product > threshold:
        sample_size += 1
        product *= rng.random()

    return sample_size - 1


@dataclass
class TrafficGenerator:
    arm_names: tuple[str, ...]
    lambda_per_second: float
    lambda_per_second_by_arm: Mapping[str, float] | None = None
    ticks_per_second: int = 60
    seed: int | None = None
    _random: Random = field(init=False, repr=False)
    _lambda_per_tick_by_arm: dict[str, float] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.arm_names:
            raise ValueError("arm_names must not be empty")
        if len(set(self.arm_names)) != len(self.arm_names):
            raise ValueError("arm_names must be unique")
        if not isfinite(self.lambda_per_second):
            raise ValueError("lambda_per_second must be finite")
        if self.lambda_per_second < 0:
            raise ValueError("lambda_per_second must be non-negative")
        if not isinstance(self.ticks_per_second, int):
            raise ValueError("ticks_per_second must be an integer")
        if self.ticks_per_second <= 0:
            raise ValueError("ticks_per_second must be positive")
        if self.lambda_per_second_by_arm is not None:
            for arm, arm_lambda in self.lambda_per_second_by_arm.items():
                if arm not in self.arm_names:
                    raise ValueError(f"unknown arm in lambda_per_second_by_arm: {arm!r}")
                if not isfinite(arm_lambda) or arm_lambda < 0:
                    raise ValueError("lambda_per_second_by_arm values must be finite and non-negative")

        self._random = Random(self.seed)
        self._lambda_per_tick_by_arm = {}
        for arm in self.arm_names:
            lambda_per_second = self.lambda_per_second
            if self.lambda_per_second_by_arm is not None:
                lambda_per_second = self.lambda_per_second_by_arm.get(arm, lambda_per_second)
            self._lambda_per_tick_by_arm[arm] = lambda_per_second / self.ticks_per_second

    def advance_tick(self, *, entry_occupied_by_arm: Mapping[str, bool]) -> list[str]:
        spawned_arms: list[str] = []

        for arm in self.arm_names:
            if arm not in entry_occupied_by_arm:
                raise ValueError(f"missing occupancy for arm {arm!r}")
            arrivals = _sample_poisson(lambda_per_tick=self._lambda_per_tick_by_arm[arm], rng=self._random)
            if arrivals > 0 and not entry_occupied_by_arm[arm]:
                spawned_arms.append(arm)

        return spawned_arms

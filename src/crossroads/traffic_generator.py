from __future__ import annotations

from dataclasses import dataclass, field
from math import exp
from random import Random
from typing import Mapping


def _sample_poisson(*, lambda_per_tick: float, rng: Random) -> int:
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
    ticks_per_second: int = 60
    seed: int | None = None
    _random: Random = field(init=False, repr=False)
    _lambda_per_tick: float = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.arm_names:
            raise ValueError("arm_names must not be empty")
        if self.lambda_per_second < 0:
            raise ValueError("lambda_per_second must be non-negative")
        if self.ticks_per_second <= 0:
            raise ValueError("ticks_per_second must be positive")

        self._random = Random(self.seed)
        self._lambda_per_tick = self.lambda_per_second / self.ticks_per_second

    def advance_tick(self, *, entry_occupied_by_arm: Mapping[str, bool]) -> list[str]:
        spawned_arms: list[str] = []

        for arm in self.arm_names:
            if arm not in entry_occupied_by_arm:
                raise ValueError(f"missing occupancy for arm {arm!r}")
            arrivals = _sample_poisson(lambda_per_tick=self._lambda_per_tick, rng=self._random)
            if arrivals > 0 and not entry_occupied_by_arm[arm]:
                spawned_arms.append(arm)

        return spawned_arms

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class ArmPhase:
    arms: tuple[str, ...]
    name: str

    def __init__(self, arms: Iterable[str], name: str) -> None:
        object.__setattr__(self, "arms", tuple(arms))
        object.__setattr__(self, "name", name)


def default_four_way_phases() -> tuple[ArmPhase, ...]:
    return (
        ArmPhase(arms=("N", "S"), name="NS"),
        ArmPhase(arms=("E", "W"), name="EW"),
    )

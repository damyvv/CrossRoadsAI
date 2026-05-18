from dataclasses import dataclass


@dataclass(frozen=True)
class ArmPhase:
    arms: tuple[str, ...]
    name: str

    def __init__(self, arms: list[str], name: str) -> None:
        object.__setattr__(self, "arms", tuple(arms))
        object.__setattr__(self, "name", name)

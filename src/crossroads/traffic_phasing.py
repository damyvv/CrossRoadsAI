from collections import Counter
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


def validate_phase_schedule(
    *,
    arm_names: Iterable[str],
    phases: Iterable[ArmPhase],
    require_full_coverage: bool = True,
) -> tuple[ArmPhase, ...]:
    known_arms = tuple(arm_names)
    if not known_arms:
        raise ValueError("arm_names must not be empty")
    if len(set(known_arms)) != len(known_arms):
        raise ValueError(f"duplicate arm names in arm_names: {list(known_arms)!r}")

    parsed_phases = tuple(phases)
    if not parsed_phases:
        raise ValueError("phases must not be empty")

    known_arms_set = set(known_arms)
    seen_arms: list[str] = []

    for index, phase in enumerate(parsed_phases):
        if not phase.arms:
            raise ValueError(f"phase {index} arms must not be empty")

        intra_phase_duplicates = sorted(
            arm for arm, count in Counter(phase.arms).items() if count > 1
        )
        if intra_phase_duplicates:
            raise ValueError(
                f"duplicate arms within phase '{phase.name}': {intra_phase_duplicates!r}"
            )

        unknown = sorted(set(phase.arms) - known_arms_set)
        if unknown:
            raise ValueError(f"unknown arms referenced in phases: {unknown!r}")

        seen_arms.extend(phase.arms)

    if require_full_coverage:
        missing = sorted(known_arms_set - set(seen_arms))
        if missing:
            raise ValueError(f"missing arms from phases: {missing!r}")

    return parsed_phases

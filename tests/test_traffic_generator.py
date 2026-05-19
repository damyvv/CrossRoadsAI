from math import ceil, floor, sqrt
import pytest

from crossroads.traffic_generator import TrafficGenerator


def test_same_seed_produces_identical_spawn_sequence():
    arms = ("N", "E", "S", "W")
    ticks = 300
    seed = 7
    spawn_rate_per_second = 5.0

    first = TrafficGenerator(
        arm_names=arms,
        lambda_per_second=spawn_rate_per_second,
        seed=seed,
    )
    second = TrafficGenerator(
        arm_names=arms,
        lambda_per_second=spawn_rate_per_second,
        seed=seed,
    )

    first_sequence: list[tuple[str, ...]] = []
    second_sequence: list[tuple[str, ...]] = []
    entry_clear = {arm: False for arm in arms}

    for _ in range(ticks):
        first_sequence.append(tuple(first.advance_tick(entry_occupied_by_arm=entry_clear)))
        second_sequence.append(tuple(second.advance_tick(entry_occupied_by_arm=entry_clear)))

    assert first_sequence == second_sequence


def test_no_spawn_occurs_when_arm_entry_is_occupied():
    arms = ("N",)
    generator = TrafficGenerator(
        arm_names=arms,
        lambda_per_second=600.0,
        seed=5,
    )

    occupied_entry = {"N": True}
    spawned_total = 0
    for _ in range(1000):
        spawned_total += len(generator.advance_tick(entry_occupied_by_arm=occupied_entry))

    assert spawned_total == 0


def test_per_arm_lambda_override_uses_override_for_that_arm():
    arms = ("N", "E")
    generator = TrafficGenerator(
        arm_names=arms,
        lambda_per_second=0.0,
        lambda_per_second_by_arm={"N": 120.0},
        seed=5,
    )
    clear_entry = {arm: False for arm in arms}
    counts = {arm: 0 for arm in arms}

    for _ in range(120):
        for arm in generator.advance_tick(entry_occupied_by_arm=clear_entry):
            counts[arm] += 1

    assert counts["N"] > 0
    assert counts["E"] == 0


def test_same_seed_and_per_arm_lambdas_produce_identical_spawn_sequence():
    arms = ("N", "E", "S", "W")
    ticks = 300
    seed = 19
    per_arm_lambda = {"N": 6.0, "E": 1.0, "S": 4.0, "W": 0.5}

    first = TrafficGenerator(
        arm_names=arms,
        lambda_per_second=2.0,
        lambda_per_second_by_arm=per_arm_lambda,
        seed=seed,
    )
    second = TrafficGenerator(
        arm_names=arms,
        lambda_per_second=2.0,
        lambda_per_second_by_arm=per_arm_lambda,
        seed=seed,
    )
    clear_entry = {arm: False for arm in arms}

    first_sequence = [
        tuple(first.advance_tick(entry_occupied_by_arm=clear_entry))
        for _ in range(ticks)
    ]
    second_sequence = [
        tuple(second.advance_tick(entry_occupied_by_arm=clear_entry))
        for _ in range(ticks)
    ]

    assert first_sequence == second_sequence


def test_different_per_arm_lambdas_produce_different_spawn_counts():
    arms = ("N", "E", "S", "W")
    ticks = 2000
    generator = TrafficGenerator(
        arm_names=arms,
        lambda_per_second=1.0,
        lambda_per_second_by_arm={"N": 10.0, "E": 1.0, "S": 10.0, "W": 1.0},
        seed=17,
    )
    clear_entry = {arm: False for arm in arms}
    counts = {arm: 0 for arm in arms}

    for _ in range(ticks):
        for arm in generator.advance_tick(entry_occupied_by_arm=clear_entry):
            counts[arm] += 1

    assert counts["N"] > counts["E"] * 3
    assert counts["S"] > counts["W"] * 3


def test_spawn_counts_over_1000_ticks_are_within_poisson_bounds():
    arms = ("N", "E", "S", "W")
    ticks = 1000
    spawn_rate_per_second = 6.0
    generator = TrafficGenerator(
        arm_names=arms,
        lambda_per_second=spawn_rate_per_second,
        seed=13,
    )
    counts = {arm: 0 for arm in arms}
    clear_entry = {arm: False for arm in arms}

    for _ in range(ticks):
        for arm in generator.advance_tick(entry_occupied_by_arm=clear_entry):
            counts[arm] += 1

    expected = spawn_rate_per_second * ticks / 60.0
    sigma = sqrt(expected)
    lower = floor(expected - 4 * sigma)
    upper = ceil(expected + 4 * sigma)

    for arm in arms:
        assert lower <= counts[arm] <= upper


def test_all_four_arms_receive_spawns_over_time():
    arms = ("N", "E", "S", "W")
    generator = TrafficGenerator(
        arm_names=arms,
        lambda_per_second=6.0,
        seed=21,
    )
    counts = {arm: 0 for arm in arms}
    clear_entry = {arm: False for arm in arms}

    for _ in range(1000):
        for arm in generator.advance_tick(entry_occupied_by_arm=clear_entry):
            counts[arm] += 1

    for arm in arms:
        assert counts[arm] > 0


def test_rejects_duplicate_arm_names():
    with pytest.raises(ValueError, match="arm_names must be unique"):
        TrafficGenerator(
            arm_names=("N", "N"),
            lambda_per_second=2.0,
        )


def test_rejects_non_finite_lambda_per_second():
    with pytest.raises(ValueError, match="lambda_per_second must be finite"):
        TrafficGenerator(
            arm_names=("N",),
            lambda_per_second=float("nan"),
        )
    with pytest.raises(ValueError, match="lambda_per_second must be finite"):
        TrafficGenerator(
            arm_names=("N",),
            lambda_per_second=float("inf"),
        )


def test_rejects_non_integer_ticks_per_second():
    with pytest.raises(ValueError, match="ticks_per_second must be an integer"):
        TrafficGenerator(
            arm_names=("N",),
            lambda_per_second=2.0,
            ticks_per_second=60.0,
        )


def test_rejects_unknown_arm_in_per_arm_lambda_config():
    with pytest.raises(ValueError, match="unknown arm in lambda_per_second_by_arm"):
        TrafficGenerator(
            arm_names=("N", "E"),
            lambda_per_second=2.0,
            lambda_per_second_by_arm={"S": 3.0},
        )

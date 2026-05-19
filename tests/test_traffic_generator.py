from crossroads.traffic_generator import TrafficGenerator
from math import ceil, floor, sqrt


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

"""Tests for TrafficLight state machine and TrafficLightController phasing."""
from crossroads.traffic_light import LightState, TrafficLight, TrafficLightController
from crossroads.traffic_phasing import ArmPhase


# ---------------------------------------------------------------------------
# TrafficLight – colour sequence at tick boundaries
# ---------------------------------------------------------------------------

class TestTrafficLightSequence:
    def test_starts_green(self):
        light = TrafficLight(green_ticks=3, yellow_ticks=2)
        assert light.state == LightState.GREEN

    def test_transitions_to_yellow_after_green_ticks(self):
        light = TrafficLight(green_ticks=3, yellow_ticks=2)
        for _ in range(3):
            light.advance_tick()
        assert light.state == LightState.YELLOW

    def test_transitions_to_red_after_yellow_ticks(self):
        light = TrafficLight(green_ticks=3, yellow_ticks=2)
        for _ in range(5):  # 3 green + 2 yellow
            light.advance_tick()
        assert light.state == LightState.RED

    def test_stays_red_until_externally_reset(self):
        light = TrafficLight(green_ticks=3, yellow_ticks=2)
        for _ in range(10):
            light.advance_tick()
        assert light.state == LightState.RED

    def test_reset_to_green(self):
        light = TrafficLight(green_ticks=3, yellow_ticks=2)
        for _ in range(6):
            light.advance_tick()
        light.reset_to_green()
        assert light.state == LightState.GREEN


# ---------------------------------------------------------------------------
# TrafficLightController – phasing / mutual exclusion
# ---------------------------------------------------------------------------

class TestTrafficLightControllerPhasing:
    def _make_controller(self, green_ticks=3, yellow_ticks=2):
        phases = [
            ArmPhase(arms=["N", "S"], name="NS"),
            ArmPhase(arms=["E", "W"], name="EW"),
        ]
        return TrafficLightController(
            arm_names=["N", "S", "E", "W"],
            phases=phases,
            green_ticks=green_ticks,
            yellow_ticks=yellow_ticks,
        )

    def test_initial_phase_ns_green_ew_red(self):
        ctrl = self._make_controller()
        assert ctrl.state("N") == LightState.GREEN
        assert ctrl.state("S") == LightState.GREEN
        assert ctrl.state("E") == LightState.RED
        assert ctrl.state("W") == LightState.RED

    def test_ns_and_ew_never_simultaneously_green(self):
        ctrl = self._make_controller(green_ticks=4, yellow_ticks=2)
        for _ in range(100):
            ctrl.advance_tick()
            ns_green = ctrl.state("N") == LightState.GREEN or ctrl.state("S") == LightState.GREEN
            ew_green = ctrl.state("E") == LightState.GREEN or ctrl.state("W") == LightState.GREEN
            assert not (ns_green and ew_green), "N/S and E/W were simultaneously green"

    def test_ew_phase_becomes_green_after_ns_completes(self):
        ctrl = self._make_controller(green_ticks=3, yellow_ticks=2)
        # 3 green + 2 yellow = 5 ticks for NS phase to go RED; next tick EW turns GREEN
        for _ in range(5):
            ctrl.advance_tick()
        assert ctrl.state("E") == LightState.GREEN
        assert ctrl.state("W") == LightState.GREEN
        assert ctrl.state("N") == LightState.RED
        assert ctrl.state("S") == LightState.RED

    def test_phases_alternate_back_to_ns(self):
        ctrl = self._make_controller(green_ticks=3, yellow_ticks=2)
        # One full NS cycle (5 ticks) + one full EW cycle (5 ticks) = 10 ticks
        for _ in range(10):
            ctrl.advance_tick()
        assert ctrl.state("N") == LightState.GREEN
        assert ctrl.state("S") == LightState.GREEN
        assert ctrl.state("E") == LightState.RED
        assert ctrl.state("W") == LightState.RED


class TestTrafficLightControllerConfiguration:
    def test_rejects_phases_missing_arms(self):
        phases = [
            ArmPhase(arms=["N", "S"], name="NS"),
            ArmPhase(arms=["E"], name="E-only"),
        ]

        try:
            TrafficLightController(
                arm_names=["N", "S", "E", "W"],
                phases=phases,
                green_ticks=3,
                yellow_ticks=2,
            )
        except ValueError as exc:
            assert "missing" in str(exc)
        else:
            raise AssertionError("Expected ValueError for missing phase arms")

    def test_rejects_phases_with_duplicate_arms(self):
        phases = [
            ArmPhase(arms=["N", "S"], name="NS"),
            ArmPhase(arms=["N", "E", "W"], name="NEW"),
        ]

        try:
            TrafficLightController(
                arm_names=["N", "S", "E", "W"],
                phases=phases,
                green_ticks=3,
                yellow_ticks=2,
            )
        except ValueError as exc:
            assert "duplicate" in str(exc)
        else:
            raise AssertionError("Expected ValueError for duplicate phase arms")


class TestArmPhaseInput:
    def test_accepts_tuple_arms(self):
        phase = ArmPhase(arms=("N", "S"), name="NS")
        assert phase.arms == ("N", "S")

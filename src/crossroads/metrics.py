from __future__ import annotations


class MetricsTracker:
    """Tracks metrics for the traffic intersection simulation."""

    def __init__(self) -> None:
        self._wait_times: list[int] = []

    def record_wait_time(self, wait_ticks: int) -> None:
        """Record the wait time (in ticks) for an exited vehicle."""
        self._wait_times.append(wait_ticks)

    def average_wait_time(self) -> float:
        """Return the average wait time in ticks across all exited vehicles.
        
        Returns 0.0 if no vehicles have exited yet.
        """
        if not self._wait_times:
            return 0.0
        return sum(self._wait_times) / len(self._wait_times)

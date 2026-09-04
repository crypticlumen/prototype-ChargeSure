from datetime import datetime, timedelta
from typing import Dict, Tuple


DEFAULT_HOURLY_LOAD_MULTIPLIER: Dict[int, float] = {
    0: 0.55,
    1: 0.50,
    2: 0.48,
    3: 0.47,
    4: 0.50,
    5: 0.60,
    6: 0.75,
    7: 0.85,
    8: 0.90,
    9: 0.88,
    10: 0.85,
    11: 0.83,
    12: 0.82,
    13: 0.80,
    14: 0.80,
    15: 0.82,
    16: 0.85,
    17: 0.92,
    18: 1.00,
    19: 1.00,
    20: 0.98,
    21: 0.90,
    22: 0.75,
    23: 0.62,
}

# At or below this multiplier, charging immediately is considered
# grid-friendly enough that waiting is unnecessary.
OFF_PEAK_THRESHOLD = 0.70

# Maximum amount of time the user should normally be asked to wait
# just to obtain a better grid period.
MAX_GRID_WAIT_MINUTES = 60

# Minimum improvement required before delaying charging.
#
# Example:
#   0.83 -> 0.82 is only a tiny improvement, so waiting is usually
#   not worth it.
#
#   0.88 -> 0.80 is a meaningful improvement and can justify waiting
#   when the wait is short enough.
MIN_LOAD_IMPROVEMENT = 0.03


class GridAwareSlotRecommender:
    """
    Practical grid-aware charging slot recommender.

    Design principle:

        User ETA
            ↓
        Check current grid load
            ↓
        Good grid?
          /   \
        YES    NO
         ↓      ↓
      Charge   Look ahead
      now      for a better
               period within
               a short wait
                  ↓
            Better period found?
               /        \
             YES         NO
              ↓           ↓
          Wait briefly   Charge now

    The scheduler deliberately avoids sending a user several hours
    into the future simply because electricity demand is lower there.
    """

    def __init__(
        self,
        hourly_load_multiplier: Dict[int, float] | None = None,
        max_grid_wait_minutes: int = MAX_GRID_WAIT_MINUTES,
        min_load_improvement: float = MIN_LOAD_IMPROVEMENT,
    ):
        self.hourly_load_multiplier = (
            hourly_load_multiplier
            or DEFAULT_HOURLY_LOAD_MULTIPLIER
        )

        if max_grid_wait_minutes < 0:
            raise ValueError(
                "max_grid_wait_minutes cannot be negative"
            )

        if min_load_improvement < 0:
            raise ValueError(
                "min_load_improvement cannot be negative"
            )

        self.max_grid_wait_minutes = max_grid_wait_minutes
        self.min_load_improvement = min_load_improvement

    def _load_for_time(
        self,
        value: datetime,
    ) -> float:
        """
        Return the grid-load multiplier for a datetime.
        """

        return self.hourly_load_multiplier[value.hour]

    def _immediate_slot(
        self,
        earliest_arrival: datetime,
        charge_duration_minutes: int,
    ) -> Tuple[datetime, datetime, bool]:
        """
        Create an immediate charging slot.
        """

        slot_start = earliest_arrival

        slot_end = (
            slot_start
            + timedelta(
                minutes=charge_duration_minutes
            )
        )

        return (
            slot_start,
            slot_end,
            False,
        )

    def recommend_slot(
        self,
        earliest_arrival: datetime,
        charge_duration_minutes: int = 30,
        search_window_hours: int = 6,
    ) -> Tuple[datetime, datetime, bool]:
        """
        Recommend a practical grid-aware charging slot.

        Rules:

        1. If the current arrival hour is already off-peak,
           charge immediately.

        2. If the current period is above the off-peak threshold,
           look ahead for a better grid period.

        3. A future slot is considered only when:
             - it occurs within max_grid_wait_minutes, and
             - it improves the load multiplier by at least
               min_load_improvement.

        4. If no worthwhile improvement is found,
           charge immediately.

        5. The scheduler never returns a slot before the vehicle ETA.
        """

        if charge_duration_minutes <= 0:
            raise ValueError(
                "charge_duration_minutes must be greater than 0"
            )

        if search_window_hours < 0:
            raise ValueError(
                "search_window_hours cannot be negative"
            )

        current_load = self._load_for_time(
            earliest_arrival
        )

        # --------------------------------------------------
        # Rule 1: Current period is already grid-friendly.
        # --------------------------------------------------

        if current_load <= OFF_PEAK_THRESHOLD:
            return self._immediate_slot(
                earliest_arrival=earliest_arrival,
                charge_duration_minutes=charge_duration_minutes,
            )

        # --------------------------------------------------
        # Rule 2:
        # Search only within a practical waiting window.
        #
        # We inspect the beginning of each future hour because
        # the configured grid multiplier represents an hourly
        # demand estimate.
        # --------------------------------------------------

        best_slot_start = earliest_arrival
        best_multiplier = current_load
        best_wait_minutes = 0

        max_search_minutes = min(
            search_window_hours * 60,
            self.max_grid_wait_minutes,
        )

        search_end = (
            earliest_arrival
            + timedelta(
                minutes=max_search_minutes
            )
        )

        # Start from the next whole hour after arrival.
        next_hour = (
            earliest_arrival
            + timedelta(hours=1)
        ).replace(
            minute=0,
            second=0,
            microsecond=0,
        )

        candidate_time = next_hour

        while candidate_time <= search_end:

            candidate_multiplier = self._load_for_time(
                candidate_time
            )

            wait_minutes = int(
                (
                    candidate_time
                    - earliest_arrival
                ).total_seconds()
                / 60
            )

            # Future candidate must actually be better.
            improvement = (
                current_load
                - candidate_multiplier
            )

            if improvement >= self.min_load_improvement:
                if candidate_multiplier < best_multiplier:
                    best_multiplier = candidate_multiplier
                    best_slot_start = candidate_time
                    best_wait_minutes = wait_minutes

            candidate_time += timedelta(hours=1)

        # --------------------------------------------------
        # Rule 3:
        # No worthwhile improvement.
        # Charge immediately.
        # --------------------------------------------------

        if best_slot_start == earliest_arrival:
            return self._immediate_slot(
                earliest_arrival=earliest_arrival,
                charge_duration_minutes=charge_duration_minutes,
            )

        # --------------------------------------------------
        # Rule 4:
        # Defensive safety check.
        # Never return a slot that starts before ETA.
        # --------------------------------------------------

        if best_slot_start < earliest_arrival:
            return self._immediate_slot(
                earliest_arrival=earliest_arrival,
                charge_duration_minutes=charge_duration_minutes,
            )

        # This should already be guaranteed by the search above,
        # but keep the check explicit for reliability.
        if best_wait_minutes > self.max_grid_wait_minutes:
            return self._immediate_slot(
                earliest_arrival=earliest_arrival,
                charge_duration_minutes=charge_duration_minutes,
            )

        slot_end = (
            best_slot_start
            + timedelta(
                minutes=charge_duration_minutes
            )
        )

        return (
            best_slot_start,
            slot_end,
            True,
        )


grid_slot_recommender = GridAwareSlotRecommender()
from datetime import datetime, timedelta
from typing import Tuple

# Placeholder grid-load curve until DISCOM feeds are integrated (Phase 3 roadmap).
# Values are illustrative relative load multipliers by hour-of-day, informed by
# typical Indian residential/commercial demand patterns (evening peak).
DEFAULT_HOURLY_LOAD_MULTIPLIER = {
    0: 0.55, 1: 0.50, 2: 0.48, 3: 0.47, 4: 0.50, 5: 0.60,
    6: 0.75, 7: 0.85, 8: 0.90, 9: 0.88, 10: 0.85, 11: 0.83,
    12: 0.82, 13: 0.80, 14: 0.80, 15: 0.82, 16: 0.85, 17: 0.92,
    18: 1.00, 19: 1.00, 20: 0.98, 21: 0.90, 22: 0.75, 23: 0.62,
}

OFF_PEAK_THRESHOLD = 0.70  # hours at/below this multiplier are considered off-peak


class GridAwareSlotRecommender:
    """
    Recommends the nearest off-peak charging window to reduce localized load spikes.
    V2G integration (Phase 3) will replace the static curve with live DISCOM telemetry —
    the interface is written so that swap-in requires no caller changes.
    """

    def __init__(self, hourly_load_multiplier: dict = None):
        self.hourly_load_multiplier = hourly_load_multiplier or DEFAULT_HOURLY_LOAD_MULTIPLIER

    def recommend_slot(
        self,
        earliest_arrival: datetime,
        charge_duration_minutes: int = 30,
        search_window_hours: int = 6,
    ) -> Tuple[datetime, datetime, bool]:
        """
        Returns (slot_start, slot_end, is_grid_aware_recommended).
        Searches forward from earliest_arrival for the lowest-load hour within the window;
        if the rider's own arrival hour is already off-peak, recommend it immediately.
        """
        arrival_hour = earliest_arrival.hour
        if self.hourly_load_multiplier[arrival_hour] <= OFF_PEAK_THRESHOLD:
            slot_start = earliest_arrival
            return slot_start, slot_start + timedelta(minutes=charge_duration_minutes), False

        best_hour_offset = 0
        best_multiplier = self.hourly_load_multiplier[arrival_hour]

        for offset in range(1, search_window_hours + 1):
            candidate_hour = (earliest_arrival + timedelta(hours=offset)).hour
            multiplier = self.hourly_load_multiplier[candidate_hour]
            if multiplier < best_multiplier:
                best_multiplier = multiplier
                best_hour_offset = offset

        slot_start = earliest_arrival + timedelta(hours=best_hour_offset)
        slot_start = slot_start.replace(minute=0, second=0, microsecond=0)
        slot_end = slot_start + timedelta(minutes=charge_duration_minutes)
        return slot_start, slot_end, best_hour_offset > 0


grid_slot_recommender = GridAwareSlotRecommender()

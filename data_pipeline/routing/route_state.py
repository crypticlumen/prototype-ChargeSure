from dataclasses import dataclass


@dataclass
class RouteState:
    route_progress_km: float
    total_route_km: float


def remaining_route_distance(
    state: RouteState,
) -> float:
    remaining = (
        state.total_route_km
        - state.route_progress_km
    )

    return max(remaining, 0.0)
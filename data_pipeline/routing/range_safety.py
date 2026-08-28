from dataclasses import dataclass


@dataclass
class VehicleProfile:
    vehicle_type: str
    battery_capacity_kwh: float
    efficiency_wh_per_km: float


@dataclass
class RangeResult:
    available_energy_kwh: float
    estimated_range_km: float
    safe_range_km: float


def calculate_range(
    vehicle: VehicleProfile,
    battery_percent: float,
    safety_reserve_percent: float = 20.0,
) -> RangeResult:

    if not 0 <= battery_percent <= 100:
        raise ValueError(
            "Battery percentage must be between 0 and 100."
        )

    if not 0 < vehicle.battery_capacity_kwh:
        raise ValueError(
            "Battery capacity must be greater than 0."
        )

    if not 0 < vehicle.efficiency_wh_per_km:
        raise ValueError(
            "Efficiency must be greater than 0."
        )

    if not 0 <= safety_reserve_percent < 100:
        raise ValueError(
            "Safety reserve must be between 0 and 100."
        )

    available_energy_kwh = (
        vehicle.battery_capacity_kwh
        * battery_percent
        / 100
    )

    available_energy_wh = (
        available_energy_kwh * 1000
    )

    estimated_range_km = (
        available_energy_wh
        / vehicle.efficiency_wh_per_km
    )

    safe_range_km = (
        estimated_range_km
        * (1 - safety_reserve_percent / 100)
    )

    return RangeResult(
        available_energy_kwh=available_energy_kwh,
        estimated_range_km=estimated_range_km,
        safe_range_km=safe_range_km,
    )


def is_charger_reachable(
    charger_distance_km: float,
    safe_range_km: float,
) -> bool:

    return charger_distance_km <= safe_range_km


if __name__ == "__main__":

    vehicle = VehicleProfile(
        vehicle_type="2W",
        battery_capacity_kwh=3.2,
        efficiency_wh_per_km=45,
    )

    battery_percent = 42

    result = calculate_range(
        vehicle,
        battery_percent,
        safety_reserve_percent=20,
    )

    print("RANGE SAFETY")
    print("=" * 50)

    print(
        f"Vehicle: "
        f"{vehicle.vehicle_type}"
    )

    print(
        f"Battery: "
        f"{battery_percent}%"
    )

    print(
        f"Available energy: "
        f"{result.available_energy_kwh:.2f} kWh"
    )

    print(
        f"Estimated range: "
        f"{result.estimated_range_km:.2f} km"
    )

    print(
        f"Safe range: "
        f"{result.safe_range_km:.2f} km"
    )
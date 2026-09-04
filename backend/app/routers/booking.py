from typing import Optional
from uuid import UUID

import psycopg2
from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.schemas.booking import BookingCreate, BookingOut, BookingCancelOut


router = APIRouter(prefix="/bookings", tags=["bookings"])

settings = get_settings()


def get_connection():
    return psycopg2.connect(settings.database_url)


def booking_from_row(row) -> BookingOut:
    return BookingOut(
        id=row[0],
        charger_id=row[1],
        charger_name=row[2],
        user_email=row[3],
        vehicle_registration=row[4],
        vehicle_connector_type=row[5],
        slot_start=row[6],
        slot_end=row[7],
        status=row[8],
        created_at=row[9],
    )


@router.post("", response_model=BookingOut, status_code=201)
def create_booking(payload: BookingCreate):
    conn = get_connection()

    try:
        with conn.cursor() as cur:

            # ---------------------------------------------------------
            # 1. Verify charger exists
            # ---------------------------------------------------------
            cur.execute(
                """
                SELECT charger_id, name
                FROM chargers
                WHERE charger_id = %s
                """,
                (payload.charger_id,),
            )

            charger = cur.fetchone()

            if not charger:
                raise HTTPException(
                    status_code=404,
                    detail="Charger not found",
                )

            charger_id, charger_name = charger

            # ---------------------------------------------------------
            # 2. Prevent overlapping bookings on the same charger
            # ---------------------------------------------------------
            cur.execute(
                """
                SELECT id, slot_start, slot_end
                FROM bookings
                WHERE charger_id = %s
                  AND status = 'CONFIRMED'
                  AND slot_start < %s
                  AND slot_end > %s
                LIMIT 1
                """,
                (
                    charger_id,
                    payload.slot_end,
                    payload.slot_start,
                ),
            )

            existing = cur.fetchone()

            if existing:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "This charging slot is already booked for this charger."
                    ),
                )

            # ---------------------------------------------------------
            # 3. Prevent duplicate future bookings by the same user
            #    on the same charger.
            #
            #    This prevents a user from accidentally creating:
            #    OCM-502309 -> 01:15-01:45
            #    OCM-502309 -> 01:46-02:16
            #    OCM-502309 -> 04:30-05:00
            #
            #    while still allowing different chargers to be booked.
            # ---------------------------------------------------------
            if payload.user_email:
                cur.execute(
                    """
                    SELECT id, slot_start, slot_end
                    FROM bookings
                    WHERE charger_id = %s
                      AND user_email = %s
                      AND status = 'CONFIRMED'
                      AND slot_end >= NOW()
                    ORDER BY slot_start ASC
                    LIMIT 1
                    """,
                    (
                        charger_id,
                        payload.user_email,
                    ),
                )

                user_existing = cur.fetchone()

                if user_existing:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "You already have an upcoming confirmed booking "
                            "for this charging station."
                        ),
                    )

            # ---------------------------------------------------------
            # 4. Prevent duplicate booking for the same vehicle and
            #    same charger as an additional safety check.
            #
            #    This works even when user_email is missing.
            # ---------------------------------------------------------
            if payload.vehicle_registration:
                cur.execute(
                    """
                    SELECT id, slot_start, slot_end
                    FROM bookings
                    WHERE charger_id = %s
                      AND vehicle_registration = %s
                      AND status = 'CONFIRMED'
                      AND slot_end >= NOW()
                    ORDER BY slot_start ASC
                    LIMIT 1
                    """,
                    (
                        charger_id,
                        payload.vehicle_registration,
                    ),
                )

                vehicle_existing = cur.fetchone()

                if vehicle_existing:
                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "This vehicle already has an upcoming confirmed "
                            "booking for this charging station."
                        ),
                    )

            # ---------------------------------------------------------
            # 5. Create booking
            # ---------------------------------------------------------
            cur.execute(
                """
                INSERT INTO bookings (
                    charger_id,
                    charger_name,
                    user_email,
                    vehicle_registration,
                    vehicle_connector_type,
                    slot_start,
                    slot_end,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'CONFIRMED')
                RETURNING
                    id,
                    charger_id,
                    charger_name,
                    user_email,
                    vehicle_registration,
                    vehicle_connector_type,
                    slot_start,
                    slot_end,
                    status,
                    created_at
                """,
                (
                    charger_id,
                    charger_name,
                    payload.user_email,
                    payload.vehicle_registration,
                    payload.vehicle_connector_type,
                    payload.slot_start,
                    payload.slot_end,
                ),
            )

            row = cur.fetchone()

            conn.commit()

            return booking_from_row(row)

    except HTTPException:
        conn.rollback()
        raise

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


@router.get("", response_model=list[BookingOut])
def list_bookings(
    user_email: Optional[str] = Query(default=None),
):
    conn = get_connection()

    try:
        with conn.cursor() as cur:

            if user_email:
                cur.execute(
                    """
                    SELECT
                        id,
                        charger_id,
                        charger_name,
                        user_email,
                        vehicle_registration,
                        vehicle_connector_type,
                        slot_start,
                        slot_end,
                        status,
                        created_at
                    FROM bookings
                    WHERE user_email = %s
                    ORDER BY slot_start DESC
                    """,
                    (user_email,),
                )
            else:
                cur.execute(
                    """
                    SELECT
                        id,
                        charger_id,
                        charger_name,
                        user_email,
                        vehicle_registration,
                        vehicle_connector_type,
                        slot_start,
                        slot_end,
                        status,
                        created_at
                    FROM bookings
                    ORDER BY slot_start DESC
                    """
                )

            rows = cur.fetchall()

            return [booking_from_row(row) for row in rows]

    finally:
        conn.close()


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: UUID):
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    id,
                    charger_id,
                    charger_name,
                    user_email,
                    vehicle_registration,
                    vehicle_connector_type,
                    slot_start,
                    slot_end,
                    status,
                    created_at
                FROM bookings
                WHERE id = %s
                """,
                (booking_id,),
            )

            row = cur.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail="Booking not found",
                )

            return booking_from_row(row)

    finally:
        conn.close()


@router.delete("/{booking_id}", response_model=BookingCancelOut)
def cancel_booking(booking_id: UUID):
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE bookings
                SET status = 'CANCELLED'
                WHERE id = %s
                  AND status = 'CONFIRMED'
                RETURNING id, status
                """,
                (booking_id,),
            )

            row = cur.fetchone()

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail="Active booking not found",
                )

            conn.commit()

            return BookingCancelOut(
                id=row[0],
                status=row[1],
            )

    except HTTPException:
        conn.rollback()
        raise

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()
from datetime import datetime
from typing import Optional

import psycopg2
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.config import get_settings


router = APIRouter(prefix="/reports", tags=["reports"])

settings = get_settings()


ALLOWED_STATUSES = {
    "working",
    "busy",
    "broken",
    "wrong_location",
}


STATUS_LABELS = {
    "working": "Working",
    "busy": "Busy / queue",
    "broken": "Broken / unavailable",
    "wrong_location": "Wrong location",
}


class ReportCreate(BaseModel):
    charger_id: str = Field(min_length=1, max_length=50)
    reported_status: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    user_email: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=1000)


class ReportOut(BaseModel):
    id: int
    charger_id: str
    reported_status: str
    status_label: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    user_email: Optional[str] = None
    notes: Optional[str] = None
    reporter_trust_score: float
    created_at: datetime


def get_connection():
    return psycopg2.connect(settings.database_url)


def ensure_reports_table():
    """
    Upgrade the existing crowd_reports table in place.

    The current ChargeSure database already has reliability views that depend
    on crowd_reports, so we must not drop/recreate the table.
    """
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                ALTER TABLE public.crowd_reports
                    ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION,
                    ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION,
                    ADD COLUMN IF NOT EXISTS user_email VARCHAR(255),
                    ADD COLUMN IF NOT EXISTS notes TEXT,
                    ADD COLUMN IF NOT EXISTS reporter_trust_score DOUBLE PRECISION
                        NOT NULL DEFAULT 0.50
                """
            )

            cur.execute(
                """
                UPDATE public.crowd_reports
                SET reporter_trust_score = CASE
                    WHEN user_trust_score IS NULL THEN 0.50
                    ELSE GREATEST(
                        0.0,
                        LEAST(1.0, user_trust_score::double precision / 100.0)
                    )
                END
                WHERE reporter_trust_score IS NULL
                   OR reporter_trust_score = 0.50
                """
            )

            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_crowd_reports_charger_created
                ON public.crowd_reports (charger_id, created_at DESC)
                """
            )

            conn.commit()

    finally:
        conn.close()


def report_from_row(row) -> ReportOut:
    return ReportOut(
        id=int(row[0]),
        charger_id=str(row[1]),
        reported_status=str(row[2]),
        status_label=STATUS_LABELS.get(
            str(row[2]),
            str(row[2]).replace("_", " ").title(),
        ),
        latitude=row[3],
        longitude=row[4],
        user_email=row[5],
        notes=row[6],
        reporter_trust_score=float(row[7] if row[7] is not None else 0.5),
        created_at=row[8],
    )


@router.post("", response_model=ReportOut, status_code=201)
def create_report(payload: ReportCreate):
    ensure_reports_table()

    status = str(payload.reported_status).strip().lower()

    if status not in ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid report status. Choose one of: "
                "working, busy, broken, wrong_location."
            ),
        )

    charger_id = str(payload.charger_id).strip()

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            # Current chargers schema:
            #   id         bigint primary key
            #   charger_id varchar(50) unique
            #
            # crowd_reports still stores the numeric chargers.id foreign key.
            # Resolve the public OCM-style charger ID to that numeric key first.
            cur.execute(
                """
                SELECT id, charger_id
                FROM public.chargers
                WHERE charger_id = %s
                LIMIT 1
                """,
                (charger_id,),
            )

            charger = cur.fetchone()

            if not charger:
                raise HTTPException(
                    status_code=404,
                    detail=f"Charger not found: {charger_id}",
                )

            charger_db_id = charger[0]
            canonical_charger_id = str(charger[1])

            # Hackathon trust prior. This can later be replaced with
            # geofence/session/user-history logic without changing the API.
            reporter_trust_score = 0.50
            user_trust_score = 50.0

            cur.execute(
                """
                INSERT INTO public.crowd_reports (
                    charger_id,
                    reported_at,
                    reported_status,
                    user_trust_score,
                    source,
                    created_at,
                    latitude,
                    longitude,
                    user_email,
                    notes,
                    reporter_trust_score
                )
                VALUES (
                    %s,
                    NOW(),
                    %s,
                    %s,
                    'web',
                    NOW(),
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
                RETURNING
                    id,
                    latitude,
                    longitude,
                    user_email,
                    notes,
                    reporter_trust_score,
                    created_at
                """,
                (
                    charger_db_id,
                    status,
                    user_trust_score,
                    payload.latitude,
                    payload.longitude,
                    payload.user_email,
                    payload.notes.strip() if payload.notes else None,
                    reporter_trust_score,
                ),
            )

            inserted = cur.fetchone()
            conn.commit()

            return ReportOut(
                id=int(inserted[0]),
                charger_id=canonical_charger_id,
                reported_status=status,
                status_label=STATUS_LABELS[status],
                latitude=inserted[1],
                longitude=inserted[2],
                user_email=inserted[3],
                notes=inserted[4],
                reporter_trust_score=float(inserted[5] or 0.5),
                created_at=inserted[6],
            )

    except HTTPException:
        conn.rollback()
        raise

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


@router.get("", response_model=list[ReportOut])
def list_reports(
    charger_id: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    ensure_reports_table()

    conn = get_connection()

    try:
        with conn.cursor() as cur:
            base_select = """
                SELECT
                    cr.id,
                    c.charger_id,
                    cr.reported_status,
                    cr.latitude,
                    cr.longitude,
                    cr.user_email,
                    cr.notes,
                    cr.reporter_trust_score,
                    cr.created_at
                FROM public.crowd_reports cr
                JOIN public.chargers c
                  ON c.id = cr.charger_id
            """

            if charger_id:
                cur.execute(
                    base_select
                    + """
                    WHERE c.charger_id = %s
                    ORDER BY cr.created_at DESC
                    LIMIT %s
                    """,
                    (str(charger_id).strip(), limit),
                )
            else:
                cur.execute(
                    base_select
                    + """
                    ORDER BY cr.created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )

            rows = cur.fetchall()

            return [
                report_from_row(row)
                for row in rows
            ]

    finally:
        conn.close()

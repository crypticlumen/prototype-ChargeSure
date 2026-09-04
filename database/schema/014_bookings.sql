CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    charger_id VARCHAR(50) NOT NULL
        REFERENCES chargers(charger_id)
        ON DELETE CASCADE,

    charger_name TEXT NOT NULL,

    user_email TEXT,

    vehicle_registration VARCHAR(50),

    vehicle_connector_type VARCHAR(100),

    slot_start TIMESTAMPTZ NOT NULL,
    slot_end TIMESTAMPTZ NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'CONFIRMED'
        CHECK (status IN ('CONFIRMED', 'CANCELLED')),

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_booking_slot
        CHECK (slot_end > slot_start)
);

CREATE INDEX IF NOT EXISTS idx_bookings_charger_slot
    ON bookings (charger_id, slot_start, slot_end);

CREATE INDEX IF NOT EXISTS idx_bookings_user_email
    ON bookings (user_email);

CREATE INDEX IF NOT EXISTS idx_bookings_status
    ON bookings (status);

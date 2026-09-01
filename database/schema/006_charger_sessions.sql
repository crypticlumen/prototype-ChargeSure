CREATE TABLE IF NOT EXISTS charger_sessions (
    id BIGSERIAL PRIMARY KEY,

    charger_id BIGINT NOT NULL
        REFERENCES chargers(id)
        ON DELETE CASCADE,

    started_at TIMESTAMPTZ NOT NULL,
    ended_at TIMESTAMPTZ,

    session_success BOOLEAN NOT NULL,

    energy_kwh NUMERIC,
    duration_minutes NUMERIC,

    failure_reason TEXT,

    source VARCHAR(30) NOT NULL DEFAULT 'simulated',

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_charger_sessions_charger
ON charger_sessions(charger_id);

CREATE INDEX IF NOT EXISTS idx_charger_sessions_started
ON charger_sessions(started_at);
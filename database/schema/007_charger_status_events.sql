CREATE TABLE IF NOT EXISTS charger_status_events (
    id BIGSERIAL PRIMARY KEY,

    charger_id BIGINT NOT NULL
        REFERENCES chargers(id)
        ON DELETE CASCADE,

    event_time TIMESTAMPTZ NOT NULL,

    status VARCHAR(20) NOT NULL,

    source VARCHAR(30) NOT NULL DEFAULT 'simulated',

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_status_events_charger
ON charger_status_events(charger_id);

CREATE INDEX IF NOT EXISTS idx_status_events_time
ON charger_status_events(event_time);
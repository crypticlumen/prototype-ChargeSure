CREATE TABLE IF NOT EXISTS crowd_reports (
    id BIGSERIAL PRIMARY KEY,

    charger_id BIGINT NOT NULL
        REFERENCES chargers(id)
        ON DELETE CASCADE,

    reported_at TIMESTAMPTZ NOT NULL,

    reported_status VARCHAR(20) NOT NULL,

    user_trust_score NUMERIC
        CHECK (
            user_trust_score >= 0
            AND user_trust_score <= 100
        ),

    source VARCHAR(30) NOT NULL DEFAULT 'simulated',

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crowd_reports_charger
ON crowd_reports(charger_id);

CREATE INDEX IF NOT EXISTS idx_crowd_reports_time
ON crowd_reports(reported_at);
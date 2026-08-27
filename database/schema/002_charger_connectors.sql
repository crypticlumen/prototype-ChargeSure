CREATE TABLE IF NOT EXISTS charger_connectors (
    id BIGSERIAL PRIMARY KEY,

    charger_id BIGINT NOT NULL
        REFERENCES chargers(id)
        ON DELETE CASCADE,

    connector_type VARCHAR(50) NOT NULL,

    power_kw NUMERIC,

    quantity INTEGER DEFAULT 1
);
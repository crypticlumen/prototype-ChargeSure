CREATE TABLE IF NOT EXISTS chargers (
    id BIGSERIAL PRIMARY KEY,

    charger_id VARCHAR(50) UNIQUE NOT NULL,

    source VARCHAR(50) NOT NULL,
    source_id VARCHAR(150),

    name TEXT,
    operator TEXT,

    address TEXT,
    city TEXT,
    state TEXT,
    country TEXT,

    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,

    location GEOGRAPHY(POINT, 4326) NOT NULL,

    power_kw NUMERIC,

    status VARCHAR(20) DEFAULT 'unknown',

    last_verified_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chargers_location
ON chargers
USING GIST(location);

CREATE INDEX IF NOT EXISTS idx_chargers_city
ON chargers(city);

CREATE INDEX IF NOT EXISTS idx_chargers_state
ON chargers(state);
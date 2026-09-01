CREATE TABLE IF NOT EXISTS routes (
    id BIGSERIAL PRIMARY KEY,

    start_lat DOUBLE PRECISION NOT NULL,
    start_lon DOUBLE PRECISION NOT NULL,

    end_lat DOUBLE PRECISION NOT NULL,
    end_lon DOUBLE PRECISION NOT NULL,

    distance_km NUMERIC NOT NULL,
    duration_minutes NUMERIC NOT NULL,

    geometry geometry(LineString, 4326) NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_routes_geometry
ON routes
USING GIST (geometry);
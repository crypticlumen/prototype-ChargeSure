CREATE TABLE IF NOT EXISTS connector_types (
    raw_connector_type VARCHAR(50) PRIMARY KEY,
    normalized_type VARCHAR(50) NOT NULL,
    description TEXT,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
INSERT INTO connector_types (
    raw_connector_type,
    normalized_type,
    description,
    verified
)
VALUES
    (
        'OCM_TYPE_0',
        'unknown',
        'OpenChargeMap ID 0: Unknown / Not Specified',
        FALSE
    ),
    (
        'OCM_TYPE_2',
        'CHAdeMO',
        'OpenChargeMap ID 2: CHAdeMO',
        TRUE
    ),
    (
        'OCM_TYPE_16',
        'CEE 3 Pin',
        'OpenChargeMap ID 16: CEE 3 Pin',
        TRUE
    ),
    (
        'OCM_TYPE_25',
        'Type 2',
        'OpenChargeMap ID 25: Type 2 (Socket Only)',
        TRUE
    ),
    (
        'OCM_TYPE_33',
        'CCS',
        'OpenChargeMap ID 33: CCS (Type 2)',
        TRUE
    ),
    (
        'OCM_TYPE_35',
        'IEC 60309 5-pin',
        'OpenChargeMap ID 35: IEC 60309 5-pin',
        TRUE
    ),
    (
        'OCM_TYPE_1036',
        'Type 2',
        'OpenChargeMap ID 1036: Type 2 (Tethered Connector)',
        TRUE
    ),
    (
        'OCM_TYPE_1041',
        'Three Phase 5-Pin',
        'OpenChargeMap ID 1041: Three Phase 5-Pin (AS/NZ 3123)',
        TRUE
    )
ON CONFLICT (raw_connector_type)
DO UPDATE SET
    normalized_type = EXCLUDED.normalized_type,
    description = EXCLUDED.description,
    verified = EXCLUDED.verified;
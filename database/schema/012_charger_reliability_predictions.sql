CREATE TABLE IF NOT EXISTS charger_reliability_predictions (
    id BIGSERIAL PRIMARY KEY,

    charger_id BIGINT NOT NULL
        REFERENCES chargers(id)
        ON DELETE CASCADE,

    reliability_score NUMERIC(5, 2) NOT NULL
        CHECK (
            reliability_score >= 0
            AND reliability_score <= 100
        ),

    prediction_probability NUMERIC(8, 6) NOT NULL
        CHECK (
            prediction_probability >= 0
            AND prediction_probability <= 1
        ),

    confidence VARCHAR(20) NOT NULL
        CHECK (
            confidence IN (
                'low',
                'medium',
                'high'
            )
        ),

    model_version VARCHAR(100) NOT NULL,

    prediction_source VARCHAR(30) NOT NULL
        DEFAULT 'xgboost',

    predicted_at TIMESTAMPTZ NOT NULL
        DEFAULT NOW(),

    created_at TIMESTAMPTZ NOT NULL
        DEFAULT NOW(),

    UNIQUE (
        charger_id,
        model_version
    )
);


CREATE INDEX IF NOT EXISTS
idx_reliability_predictions_charger
ON charger_reliability_predictions(charger_id);


CREATE INDEX IF NOT EXISTS
idx_reliability_predictions_score
ON charger_reliability_predictions(reliability_score);
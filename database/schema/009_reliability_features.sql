CREATE OR REPLACE VIEW reliability_features AS

WITH session_features AS (
    SELECT
        charger_id,

        COUNT(*) AS total_sessions,

        COUNT(*) FILTER (
            WHERE session_success = TRUE
        ) AS successful_sessions,

        COUNT(*) FILTER (
            WHERE session_success = FALSE
        ) AS failed_sessions,

        COALESCE(
            AVG(
                CASE
                    WHEN session_success = TRUE
                    THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS session_success_rate,

        COALESCE(
            AVG(energy_kwh),
            0.0
        ) AS avg_energy_kwh,

        COALESCE(
            AVG(duration_minutes),
            0.0
        ) AS avg_session_duration_minutes

    FROM charger_sessions

    GROUP BY charger_id
),

status_features AS (
    SELECT
        charger_id,

        COUNT(*) AS total_status_events,

        COUNT(*) FILTER (
            WHERE status = 'available'
        ) AS available_events,

        COUNT(*) FILTER (
            WHERE status = 'occupied'
        ) AS occupied_events,

        COUNT(*) FILTER (
            WHERE status = 'faulted'
        ) AS faulted_events,

        COUNT(*) FILTER (
            WHERE status = 'offline'
        ) AS offline_events,

        COALESCE(
            AVG(
                CASE
                    WHEN status = 'available'
                    THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS availability_ratio,

        COALESCE(
            AVG(
                CASE
                    WHEN status = 'faulted'
                    THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS fault_ratio,

        COALESCE(
            AVG(
                CASE
                    WHEN status = 'offline'
                    THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS offline_ratio,

        MAX(event_time) AS last_status_event_at

    FROM charger_status_events

    GROUP BY charger_id
),

crowd_features AS (
    SELECT
        charger_id,

        COUNT(*) AS crowd_report_count,

        COUNT(*) FILTER (
            WHERE reported_status IN (
                'available',
                'occupied'
            )
        ) AS positive_reports,

        COUNT(*) FILTER (
            WHERE reported_status IN (
                'faulted',
                'offline'
            )
        ) AS negative_reports,

        COALESCE(
            AVG(user_trust_score),
            0.0
        ) AS average_crowd_trust,

        COALESCE(
            AVG(
                CASE
                    WHEN reported_status IN (
                        'available',
                        'occupied'
                    )
                    THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS positive_report_ratio,

        COALESCE(
            AVG(
                CASE
                    WHEN reported_status IN (
                        'faulted',
                        'offline'
                    )
                    THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS negative_report_ratio,

        MAX(reported_at) AS last_crowd_report_at

    FROM crowd_reports

    GROUP BY charger_id
)

SELECT
    c.id AS charger_db_id,
    c.charger_id,

    c.name,
    c.city,
    c.state,

    c.power_kw,

    -- -------------------------------
    -- Session features
    -- -------------------------------

    COALESCE(
        s.total_sessions,
        0
    ) AS total_sessions,

    COALESCE(
        s.successful_sessions,
        0
    ) AS successful_sessions,

    COALESCE(
        s.failed_sessions,
        0
    ) AS failed_sessions,

    COALESCE(
        s.session_success_rate,
        0.0
    ) AS session_success_rate,

    COALESCE(
        s.avg_energy_kwh,
        0.0
    ) AS avg_energy_kwh,

    COALESCE(
        s.avg_session_duration_minutes,
        0.0
    ) AS avg_session_duration_minutes,

    -- -------------------------------
    -- Status features
    -- -------------------------------

    COALESCE(
        st.total_status_events,
        0
    ) AS total_status_events,

    COALESCE(
        st.available_events,
        0
    ) AS available_events,

    COALESCE(
        st.occupied_events,
        0
    ) AS occupied_events,

    COALESCE(
        st.faulted_events,
        0
    ) AS faulted_events,

    COALESCE(
        st.offline_events,
        0
    ) AS offline_events,

    COALESCE(
        st.availability_ratio,
        0.0
    ) AS availability_ratio,

    COALESCE(
        st.fault_ratio,
        0.0
    ) AS fault_ratio,

    COALESCE(
        st.offline_ratio,
        0.0
    ) AS offline_ratio,

    -- -------------------------------
    -- Crowd features
    -- -------------------------------

    COALESCE(
        cr.crowd_report_count,
        0
    ) AS crowd_report_count,

    COALESCE(
        cr.positive_reports,
        0
    ) AS positive_reports,

    COALESCE(
        cr.negative_reports,
        0
    ) AS negative_reports,

    COALESCE(
        cr.average_crowd_trust,
        0.0
    ) AS average_crowd_trust,

    COALESCE(
        cr.positive_report_ratio,
        0.0
    ) AS positive_report_ratio,

    COALESCE(
        cr.negative_report_ratio,
        0.0
    ) AS negative_report_ratio,

    -- -------------------------------
    -- Verification freshness
    -- -------------------------------

    CASE
        WHEN c.last_verified_at IS NULL
        THEN NULL
        ELSE EXTRACT(
            EPOCH FROM (
                NOW() - c.last_verified_at
            )
        ) / 86400.0
    END AS days_since_last_verified

FROM chargers c

LEFT JOIN session_features s
    ON s.charger_id = c.id

LEFT JOIN status_features st
    ON st.charger_id = c.id

LEFT JOIN crowd_features cr
    ON cr.charger_id = c.id;
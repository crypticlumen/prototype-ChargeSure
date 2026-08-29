CREATE OR REPLACE VIEW reliability_training AS

WITH simulation_window AS (
    SELECT
        LEAST(
            MIN(started_at),
            MIN(event_time),
            MIN(reported_at)
        ) AS history_start,

        GREATEST(
            MAX(started_at),
            MAX(event_time),
            MAX(reported_at)
        ) AS history_end

    FROM (
        SELECT
            started_at,
            NULL::timestamptz AS event_time,
            NULL::timestamptz AS reported_at
        FROM charger_sessions
        WHERE source = 'simulated'

        UNION ALL

        SELECT
            NULL::timestamptz,
            event_time,
            NULL::timestamptz
        FROM charger_status_events
        WHERE source = 'simulated'

        UNION ALL

        SELECT
            NULL::timestamptz,
            NULL::timestamptz,
            reported_at
        FROM crowd_reports
        WHERE source = 'simulated'
    ) events
),

cutoff AS (
    SELECT
        history_start,
        history_end,

        history_start
        + (
            history_end - history_start
        ) * 0.70 AS feature_end

    FROM simulation_window
),

session_features AS (
    SELECT
        cs.charger_id,

        COUNT(*) AS total_sessions,

        COUNT(*) FILTER (
            WHERE cs.session_success = TRUE
        ) AS successful_sessions,

        COUNT(*) FILTER (
            WHERE cs.session_success = FALSE
        ) AS failed_sessions,

        COALESCE(
            AVG(
                CASE
                    WHEN cs.session_success = TRUE
                    THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS session_success_rate,

        COALESCE(
            AVG(cs.energy_kwh),
            0.0
        ) AS avg_energy_kwh,

        COALESCE(
            AVG(cs.duration_minutes),
            0.0
        ) AS avg_session_duration_minutes

    FROM charger_sessions cs
    CROSS JOIN cutoff c

    WHERE cs.source = 'simulated'
      AND cs.started_at >= c.history_start
      AND cs.started_at < c.feature_end

    GROUP BY cs.charger_id
),

status_features AS (
    SELECT
        se.charger_id,

        COUNT(*) AS total_status_events,

        COUNT(*) FILTER (
            WHERE se.status = 'available'
        ) AS available_events,

        COUNT(*) FILTER (
            WHERE se.status = 'occupied'
        ) AS occupied_events,

        COUNT(*) FILTER (
            WHERE se.status = 'faulted'
        ) AS faulted_events,

        COUNT(*) FILTER (
            WHERE se.status = 'offline'
        ) AS offline_events,

        COALESCE(
            AVG(
                CASE
                    WHEN se.status = 'available'
                    THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS availability_ratio,

        COALESCE(
            AVG(
                CASE
                    WHEN se.status = 'faulted'
                    THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS fault_ratio,

        COALESCE(
            AVG(
                CASE
                    WHEN se.status = 'offline'
                    THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS offline_ratio

    FROM charger_status_events se
    CROSS JOIN cutoff c

    WHERE se.source = 'simulated'
      AND se.event_time >= c.history_start
      AND se.event_time < c.feature_end

    GROUP BY se.charger_id
),

crowd_features AS (
    SELECT
        cr.charger_id,

        COUNT(*) AS crowd_report_count,

        COALESCE(
            AVG(cr.user_trust_score),
            0.0
        ) AS average_crowd_trust,

        COALESCE(
            AVG(
                CASE
                    WHEN cr.reported_status IN (
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
                    WHEN cr.reported_status IN (
                        'faulted',
                        'offline'
                    )
                    THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS negative_report_ratio

    FROM crowd_reports cr
    CROSS JOIN cutoff c

    WHERE cr.source = 'simulated'
      AND cr.reported_at >= c.history_start
      AND cr.reported_at < c.feature_end

    GROUP BY cr.charger_id
),

future_sessions AS (
    SELECT
        cs.charger_id,

        COUNT(*) AS future_total_sessions,

        COUNT(*) FILTER (
            WHERE cs.session_success = TRUE
        ) AS future_successful_sessions,

        COALESCE(
            AVG(
                CASE
                    WHEN cs.session_success = TRUE
                    THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS future_success_rate

    FROM charger_sessions cs
    CROSS JOIN cutoff c

    WHERE cs.source = 'simulated'
      AND cs.started_at >= c.feature_end
      AND cs.started_at <= c.history_end

    GROUP BY cs.charger_id
)

SELECT
    ch.charger_id,

    -- -------------------------------
    -- Features
    -- -------------------------------

    COALESCE(
        sf.total_sessions,
        0
    ) AS total_sessions,

    COALESCE(
        sf.successful_sessions,
        0
    ) AS successful_sessions,

    COALESCE(
        sf.failed_sessions,
        0
    ) AS failed_sessions,

    COALESCE(
        sf.session_success_rate,
        0.0
    ) AS session_success_rate,

    COALESCE(
        sf.avg_energy_kwh,
        0.0
    ) AS avg_energy_kwh,

    COALESCE(
        sf.avg_session_duration_minutes,
        0.0
    ) AS avg_session_duration_minutes,

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

    COALESCE(
        cf.crowd_report_count,
        0
    ) AS crowd_report_count,

    COALESCE(
        cf.average_crowd_trust,
        0.0
    ) AS average_crowd_trust,

    COALESCE(
        cf.positive_report_ratio,
        0.0
    ) AS positive_report_ratio,

    COALESCE(
        cf.negative_report_ratio,
        0.0
    ) AS negative_report_ratio,

    -- -------------------------------
    -- Charger metadata
    -- -------------------------------

    ch.power_kw,

    CASE
        WHEN ch.last_verified_at IS NULL
        THEN NULL

        ELSE EXTRACT(
            EPOCH FROM (
                c.feature_end
                - ch.last_verified_at
            )
        ) / 86400.0
    END AS days_since_verification,

    -- -------------------------------
    -- FUTURE TARGET
    -- -------------------------------

    fs.future_total_sessions,

    fs.future_successful_sessions,

    COALESCE(
        fs.future_success_rate,
        0.0
    ) AS future_success_rate,

    CASE
        WHEN fs.future_total_sessions >= 5
         AND fs.future_success_rate >= 0.80
        THEN 1

        WHEN fs.future_total_sessions >= 5
        THEN 0

        ELSE NULL
    END AS reliable_label

FROM chargers ch

CROSS JOIN cutoff c

LEFT JOIN session_features sf
    ON sf.charger_id = ch.id

LEFT JOIN status_features st
    ON st.charger_id = ch.id

LEFT JOIN crowd_features cf
    ON cf.charger_id = ch.id

LEFT JOIN future_sessions fs
    ON fs.charger_id = ch.id;
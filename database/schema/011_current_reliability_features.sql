CREATE OR REPLACE VIEW current_reliability_features AS

WITH simulation_window AS (
    SELECT
        MIN(event_time) AS history_start,
        MAX(event_time) AS history_end
    FROM (
        SELECT started_at AS event_time
        FROM charger_sessions
        WHERE source = 'simulated'

        UNION ALL

        SELECT event_time
        FROM charger_status_events
        WHERE source = 'simulated'

        UNION ALL

        SELECT reported_at AS event_time
        FROM crowd_reports
        WHERE source = 'simulated'
    ) all_events
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
    CROSS JOIN simulation_window w

    WHERE cs.source = 'simulated'
      AND cs.started_at >= w.history_start
      AND cs.started_at <= w.history_end

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
    CROSS JOIN simulation_window w

    WHERE se.source = 'simulated'
      AND se.event_time >= w.history_start
      AND se.event_time <= w.history_end

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
    CROSS JOIN simulation_window w

    WHERE cr.source = 'simulated'
      AND cr.reported_at >= w.history_start
      AND cr.reported_at <= w.history_end

    GROUP BY cr.charger_id
)

SELECT
    c.id AS charger_db_id,
    c.charger_id,
    c.name,
    c.city,
    c.state,

    c.power_kw,

    -- Session features
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

    -- Status features
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

    -- Crowd features
    COALESCE(
        cr.crowd_report_count,
        0
    ) AS crowd_report_count,

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

    -- Verification freshness
    CASE
        WHEN c.last_verified_at IS NULL
        THEN NULL

        ELSE EXTRACT(
            EPOCH FROM (
                w.history_end
                - c.last_verified_at
            )
        ) / 86400.0
    END AS days_since_verification

FROM chargers c

CROSS JOIN simulation_window w

LEFT JOIN session_features sf
    ON sf.charger_id = c.id

LEFT JOIN status_features st
    ON st.charger_id = c.id

LEFT JOIN crowd_features cr
    ON cr.charger_id = c.id;
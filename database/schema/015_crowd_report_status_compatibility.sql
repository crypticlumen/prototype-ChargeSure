-- ChargeSure migration 015
-- Make current reliability features understand both the legacy simulated
-- crowd-report vocabulary and the new web-report vocabulary.
--
-- Legacy statuses:
--   available, occupied, faulted, offline
-- Web statuses:
--   working, busy, broken, wrong_location
--
-- Positive / operational:
--   available, occupied, working
-- Negative / degraded:
--   faulted, offline, busy, broken, wrong_location
--
-- IMPORTANT:
--   * Do NOT drop crowd_reports.
--   * Do NOT modify reliability_training here.
--   * Existing crowd_reports rows are preserved.

BEGIN;

CREATE OR REPLACE VIEW public.current_reliability_features AS
WITH session_features AS (
    SELECT
        charger_sessions.charger_id,
        count(*) AS total_sessions,
        count(*) FILTER (
            WHERE charger_sessions.session_success = true
        ) AS successful_sessions,
        count(*) FILTER (
            WHERE charger_sessions.session_success = false
        ) AS failed_sessions,
        COALESCE(
            avg(
                CASE
                    WHEN charger_sessions.session_success = true THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS session_success_rate,
        COALESCE(avg(charger_sessions.energy_kwh), 0.0) AS avg_energy_kwh,
        COALESCE(avg(charger_sessions.duration_minutes), 0.0) AS avg_session_duration_minutes
    FROM public.charger_sessions
    GROUP BY charger_sessions.charger_id
),
status_features AS (
    SELECT
        charger_status_events.charger_id,
        count(*) AS total_status_events,
        count(*) FILTER (
            WHERE charger_status_events.status::text = 'available'
        ) AS available_events,
        count(*) FILTER (
            WHERE charger_status_events.status::text = 'occupied'
        ) AS occupied_events,
        count(*) FILTER (
            WHERE charger_status_events.status::text = 'faulted'
        ) AS faulted_events,
        count(*) FILTER (
            WHERE charger_status_events.status::text = 'offline'
        ) AS offline_events,
        COALESCE(
            avg(
                CASE
                    WHEN charger_status_events.status::text = 'available' THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS availability_ratio,
        COALESCE(
            avg(
                CASE
                    WHEN charger_status_events.status::text = 'faulted' THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS fault_ratio,
        COALESCE(
            avg(
                CASE
                    WHEN charger_status_events.status::text = 'offline' THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS offline_ratio
    FROM public.charger_status_events
    GROUP BY charger_status_events.charger_id
),
crowd_features AS (
    SELECT
        crowd_reports.charger_id,
        count(*) AS crowd_report_count,
        count(*) FILTER (
            WHERE crowd_reports.reported_status::text = ANY (
                ARRAY[
                    'available',
                    'occupied',
                    'working'
                ]::text[]
            )
        ) AS positive_reports,
        count(*) FILTER (
            WHERE crowd_reports.reported_status::text = ANY (
                ARRAY[
                    'faulted',
                    'offline',
                    'busy',
                    'broken',
                    'wrong_location'
                ]::text[]
            )
        ) AS negative_reports,
        COALESCE(avg(crowd_reports.user_trust_score), 0.0) AS average_crowd_trust,
        COALESCE(
            avg(
                CASE
                    WHEN crowd_reports.reported_status::text = ANY (
                        ARRAY[
                            'available',
                            'occupied',
                            'working'
                        ]::text[]
                    ) THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS positive_report_ratio,
        COALESCE(
            avg(
                CASE
                    WHEN crowd_reports.reported_status::text = ANY (
                        ARRAY[
                            'faulted',
                            'offline',
                            'busy',
                            'broken',
                            'wrong_location'
                        ]::text[]
                    ) THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS negative_report_ratio,
        max(crowd_reports.reported_at) AS last_crowd_report_at
    FROM public.crowd_reports
    GROUP BY crowd_reports.charger_id
)
SELECT
    c.id AS charger_db_id,
    c.charger_id,
    c.name,
    c.city,
    c.state,
    c.power_kw,
    COALESCE(sf.total_sessions, 0::bigint) AS total_sessions,
    COALESCE(sf.successful_sessions, 0::bigint) AS successful_sessions,
    COALESCE(sf.failed_sessions, 0::bigint) AS failed_sessions,
    COALESCE(sf.session_success_rate, 0.0) AS session_success_rate,
    COALESCE(sf.avg_energy_kwh, 0.0) AS avg_energy_kwh,
    COALESCE(sf.avg_session_duration_minutes, 0.0) AS avg_session_duration_minutes,
    COALESCE(st.total_status_events, 0::bigint) AS total_status_events,
    COALESCE(st.available_events, 0::bigint) AS available_events,
    COALESCE(st.occupied_events, 0::bigint) AS occupied_events,
    COALESCE(st.faulted_events, 0::bigint) AS faulted_events,
    COALESCE(st.offline_events, 0::bigint) AS offline_events,
    COALESCE(st.availability_ratio, 0.0) AS availability_ratio,
    COALESCE(st.fault_ratio, 0.0) AS fault_ratio,
    COALESCE(st.offline_ratio, 0.0) AS offline_ratio,
    COALESCE(cr.crowd_report_count, 0::bigint) AS crowd_report_count,
    COALESCE(cr.average_crowd_trust, 0.0) AS average_crowd_trust,
    COALESCE(cr.positive_report_ratio, 0.0) AS positive_report_ratio,
    COALESCE(cr.negative_report_ratio, 0.0) AS negative_report_ratio,
    CASE
        WHEN c.last_verified_at IS NULL THEN NULL::numeric
        ELSE EXTRACT(epoch FROM (now() - c.last_verified_at)) / 86400.0
    END AS days_since_verification
FROM public.chargers c
LEFT JOIN session_features sf ON sf.charger_id = c.id
LEFT JOIN status_features st ON st.charger_id = c.id
LEFT JOIN crowd_features cr ON cr.charger_id = c.id;

CREATE OR REPLACE VIEW public.reliability_features AS
WITH session_features AS (
    SELECT
        charger_sessions.charger_id,
        count(*) AS total_sessions,
        count(*) FILTER (
            WHERE charger_sessions.session_success = true
        ) AS successful_sessions,
        count(*) FILTER (
            WHERE charger_sessions.session_success = false
        ) AS failed_sessions,
        COALESCE(
            avg(
                CASE
                    WHEN charger_sessions.session_success = true THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS session_success_rate,
        COALESCE(avg(charger_sessions.energy_kwh), 0.0) AS avg_energy_kwh,
        COALESCE(avg(charger_sessions.duration_minutes), 0.0) AS avg_session_duration_minutes
    FROM public.charger_sessions
    GROUP BY charger_sessions.charger_id
),
status_features AS (
    SELECT
        charger_status_events.charger_id,
        count(*) AS total_status_events,
        count(*) FILTER (
            WHERE charger_status_events.status::text = 'available'
        ) AS available_events,
        count(*) FILTER (
            WHERE charger_status_events.status::text = 'occupied'
        ) AS occupied_events,
        count(*) FILTER (
            WHERE charger_status_events.status::text = 'faulted'
        ) AS faulted_events,
        count(*) FILTER (
            WHERE charger_status_events.status::text = 'offline'
        ) AS offline_events,
        COALESCE(
            avg(
                CASE
                    WHEN charger_status_events.status::text = 'available' THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS availability_ratio,
        COALESCE(
            avg(
                CASE
                    WHEN charger_status_events.status::text = 'faulted' THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS fault_ratio,
        COALESCE(
            avg(
                CASE
                    WHEN charger_status_events.status::text = 'offline' THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS offline_ratio,
        max(charger_status_events.event_time) AS last_status_event_at
    FROM public.charger_status_events
    GROUP BY charger_status_events.charger_id
),
crowd_features AS (
    SELECT
        crowd_reports.charger_id,
        count(*) AS crowd_report_count,
        count(*) FILTER (
            WHERE crowd_reports.reported_status::text = ANY (
                ARRAY[
                    'available',
                    'occupied',
                    'working'
                ]::text[]
            )
        ) AS positive_reports,
        count(*) FILTER (
            WHERE crowd_reports.reported_status::text = ANY (
                ARRAY[
                    'faulted',
                    'offline',
                    'busy',
                    'broken',
                    'wrong_location'
                ]::text[]
            )
        ) AS negative_reports,
        COALESCE(avg(crowd_reports.user_trust_score), 0.0) AS average_crowd_trust,
        COALESCE(
            avg(
                CASE
                    WHEN crowd_reports.reported_status::text = ANY (
                        ARRAY[
                            'available',
                            'occupied',
                            'working'
                        ]::text[]
                    ) THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS positive_report_ratio,
        COALESCE(
            avg(
                CASE
                    WHEN crowd_reports.reported_status::text = ANY (
                        ARRAY[
                            'faulted',
                            'offline',
                            'busy',
                            'broken',
                            'wrong_location'
                        ]::text[]
                    ) THEN 1.0
                    ELSE 0.0
                END
            ),
            0.0
        ) AS negative_report_ratio,
        max(crowd_reports.reported_at) AS last_crowd_report_at
    FROM public.crowd_reports
    GROUP BY crowd_reports.charger_id
)
SELECT
    c.id AS charger_db_id,
    c.charger_id,
    c.name,
    c.city,
    c.state,
    c.power_kw,
    COALESCE(s.total_sessions, 0::bigint) AS total_sessions,
    COALESCE(s.successful_sessions, 0::bigint) AS successful_sessions,
    COALESCE(s.failed_sessions, 0::bigint) AS failed_sessions,
    COALESCE(s.session_success_rate, 0.0) AS session_success_rate,
    COALESCE(s.avg_energy_kwh, 0.0) AS avg_energy_kwh,
    COALESCE(s.avg_session_duration_minutes, 0.0) AS avg_session_duration_minutes,
    COALESCE(st.total_status_events, 0::bigint) AS total_status_events,
    COALESCE(st.available_events, 0::bigint) AS available_events,
    COALESCE(st.occupied_events, 0::bigint) AS occupied_events,
    COALESCE(st.faulted_events, 0::bigint) AS faulted_events,
    COALESCE(st.offline_events, 0::bigint) AS offline_events,
    COALESCE(st.availability_ratio, 0.0) AS availability_ratio,
    COALESCE(st.fault_ratio, 0.0) AS fault_ratio,
    COALESCE(st.offline_ratio, 0.0) AS offline_ratio,
    COALESCE(cr.crowd_report_count, 0::bigint) AS crowd_report_count,
    COALESCE(cr.positive_reports, 0::bigint) AS positive_reports,
    COALESCE(cr.negative_reports, 0::bigint) AS negative_reports,
    COALESCE(cr.average_crowd_trust, 0.0) AS average_crowd_trust,
    COALESCE(cr.positive_report_ratio, 0.0) AS positive_report_ratio,
    COALESCE(cr.negative_report_ratio, 0.0) AS negative_report_ratio,
    CASE
        WHEN c.last_verified_at IS NULL THEN NULL::numeric
        ELSE EXTRACT(epoch FROM (now() - c.last_verified_at)) / 86400.0
    END AS days_since_last_verified
FROM public.chargers c
LEFT JOIN session_features s ON s.charger_id = c.id
LEFT JOIN status_features st ON st.charger_id = c.id
LEFT JOIN crowd_features cr ON cr.charger_id = c.id;

COMMIT;

{{ config(materialized='view') }}

WITH events AS (
    SELECT * FROM {{ ref('stg_ga4_events') }}
),

id_map AS (
    SELECT
        identifier_value,
        canonical_customer_id
    FROM {{ ref('int_identity_graph') }}
    WHERE identifier_type = 'user_pseudo_id'
),

sessions_aggregated AS (
    SELECT
        e.session_id,
        e.user_pseudo_id,
        COALESCE(
            MAX(e.user_id),
            MAX(m.canonical_customer_id),
            CONCAT('ANON_', e.user_pseudo_id)
        ) AS canonical_customer_id,

        MIN(e.event_timestamp) AS session_start_timestamp,
        MAX(e.event_timestamp) AS session_end_timestamp,
        DATE(MIN(e.event_date)) AS session_date,

        -- Channel and Campaign (taken from session start event)
        ARRAY_AGG(e.default_channel_grouping ORDER BY e.event_timestamp ASC LIMIT 1)[OFFSET(0)] AS channel_grouping,
        ARRAY_AGG(e.utm_source ORDER BY e.event_timestamp ASC LIMIT 1)[OFFSET(0)] AS utm_source,
        ARRAY_AGG(e.utm_medium ORDER BY e.event_timestamp ASC LIMIT 1)[OFFSET(0)] AS utm_medium,
        ARRAY_AGG(e.utm_campaign ORDER BY e.event_timestamp ASC LIMIT 1)[OFFSET(0)] AS utm_campaign,
        ARRAY_AGG(e.page_location ORDER BY e.event_timestamp ASC LIMIT 1)[OFFSET(0)] AS landing_page,

        -- Device & Location
        ARRAY_AGG(e.device_category ORDER BY e.event_timestamp ASC LIMIT 1)[OFFSET(0)] AS device_category,
        ARRAY_AGG(e.operating_system ORDER BY e.event_timestamp ASC LIMIT 1)[OFFSET(0)] AS operating_system,
        ARRAY_AGG(e.country ORDER BY e.event_timestamp ASC LIMIT 1)[OFFSET(0)] AS country,
        ARRAY_AGG(e.city ORDER BY e.event_timestamp ASC LIMIT 1)[OFFSET(0)] AS city,

        -- Session metrics
        COUNT(1) AS event_count,
        COUNTIF(e.event_name = 'page_view') AS pageviews_count,
        COUNTIF(e.event_name = 'view_item') AS item_views_count,
        COUNTIF(e.event_name = 'add_to_cart') AS add_to_cart_count,
        COUNTIF(e.event_name = 'purchase') AS purchase_count,
        MAX(e.transaction_id) AS transaction_id,
        SUM(e.event_value_usd) AS session_revenue_usd

    FROM events e
    LEFT JOIN id_map m
        ON e.user_pseudo_id = m.identifier_value
    GROUP BY
        e.session_id,
        e.user_pseudo_id
)

SELECT
    *,
    TIMESTAMP_DIFF(session_end_timestamp, session_start_timestamp, SECOND) AS session_duration_seconds
FROM sessions_aggregated

{{ config(materialized='view') }}

WITH orders AS (
    SELECT * FROM {{ ref('stg_crm_orders') }}
),

sessions AS (
    SELECT * FROM {{ ref('int_web_sessions') }}
),

joined_touchpoints AS (
    SELECT
        o.order_id,
        o.customer_id,
        o.order_timestamp,
        o.total_revenue_usd,
        s.session_id,
        s.session_start_timestamp,
        s.channel_grouping,
        s.utm_source,
        s.utm_medium,
        s.utm_campaign,
        s.device_category,
        
        -- Time difference between touchpoint and conversion
        TIMESTAMP_DIFF(o.order_timestamp, s.session_start_timestamp, MINUTE) / (60.0 * 24.0) AS days_before_order

    FROM orders o
    INNER JOIN sessions s
        ON o.customer_id = s.canonical_customer_id
        AND s.session_start_timestamp <= o.order_timestamp
        -- 30-Day Attribution Lookback Window
        AND s.session_start_timestamp >= TIMESTAMP_SUB(o.order_timestamp, INTERVAL 30 DAY)
),

ordered_touchpoints AS (
    SELECT
        *,
        {{ dbt_utils.generate_surrogate_key(['order_id', 'session_id']) }} AS touchpoint_id,
        ROW_NUMBER() OVER(PARTITION BY order_id ORDER BY session_start_timestamp ASC) AS touchpoint_order_asc,
        ROW_NUMBER() OVER(PARTITION BY order_id ORDER BY session_start_timestamp DESC) AS touchpoint_order_desc,
        COUNT(1) OVER(PARTITION BY order_id) AS total_journey_touchpoints
    FROM joined_touchpoints
)

SELECT * FROM ordered_touchpoints

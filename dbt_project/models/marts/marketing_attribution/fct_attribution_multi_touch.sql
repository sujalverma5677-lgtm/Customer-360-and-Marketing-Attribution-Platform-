{{ config(materialized='table') }}

WITH touchpoints AS (
    SELECT * FROM {{ ref('int_customer_touchpoints') }}
),

-- Compute raw decay and position-based weights
weight_calculations AS (
    SELECT
        *,
        -- First-Touch Weight (100% to first recorded interaction)
        CASE WHEN touchpoint_order_asc = 1 THEN 1.0 ELSE 0.0 END AS weight_first_touch,

        -- Last-Touch Weight (100% to last interaction before conversion)
        CASE WHEN touchpoint_order_desc = 1 THEN 1.0 ELSE 0.0 END AS weight_last_touch,

        -- Linear Weight (equal distribution across all touchpoints)
        1.0 / total_journey_touchpoints AS weight_linear,

        -- Time-Decay Raw Exponential Weight (7-day half-life: 2^(-delta_t / 7))
        POW(2.0, -1.0 * (days_before_order / 7.0)) AS raw_weight_time_decay,

        -- Position-Based (U-Shaped 40% First, 40% Last, 20% Middle)
        CASE
            WHEN total_journey_touchpoints = 1 THEN 1.0
            WHEN total_journey_touchpoints = 2 THEN 0.5
            WHEN touchpoint_order_asc = 1 THEN 0.4
            WHEN touchpoint_order_desc = 1 THEN 0.4
            ELSE 0.2 / (total_journey_touchpoints - 2)
        END AS weight_position_based

    FROM touchpoints
),

-- Normalize Time-Decay weights so they sum to 1.0 per order
normalized_weights AS (
    SELECT
        *,
        raw_weight_time_decay / SUM(raw_weight_time_decay) OVER (PARTITION BY order_id) AS weight_time_decay
    FROM weight_calculations
),

-- Allocate Attributed Revenues and Conversion Counts
final_attribution AS (
    SELECT
        touchpoint_id,
        order_id,
        customer_id,
        session_id,
        session_start_timestamp,
        order_timestamp,
        channel_grouping,
        utm_source,
        utm_medium,
        utm_campaign,
        device_category,
        days_before_order,
        touchpoint_order_asc,
        touchpoint_order_desc,
        total_journey_touchpoints,
        total_revenue_usd,

        -- Weights
        ROUND(weight_first_touch, 4) AS weight_first_touch,
        ROUND(weight_last_touch, 4) AS weight_last_touch,
        ROUND(weight_linear, 4) AS weight_linear,
        ROUND(weight_time_decay, 4) AS weight_time_decay,
        ROUND(weight_position_based, 4) AS weight_position_based,

        -- Attributed Revenue USD
        ROUND(total_revenue_usd * weight_first_touch, 2) AS revenue_first_touch,
        ROUND(total_revenue_usd * weight_last_touch, 2) AS revenue_last_touch,
        ROUND(total_revenue_usd * weight_linear, 2) AS revenue_linear,
        ROUND(total_revenue_usd * weight_time_decay, 2) AS revenue_time_decay,
        ROUND(total_revenue_usd * weight_position_based, 2) AS revenue_position_based,

        -- Attributed Conversions (Fractional Orders)
        ROUND(1.0 * weight_first_touch, 4) AS conversions_first_touch,
        ROUND(1.0 * weight_last_touch, 4) AS conversions_last_touch,
        ROUND(1.0 * weight_linear, 4) AS conversions_linear,
        ROUND(1.0 * weight_time_decay, 4) AS conversions_time_decay,
        ROUND(1.0 * weight_position_based, 4) AS conversions_position_based

    FROM normalized_weights
)

SELECT * FROM final_attribution

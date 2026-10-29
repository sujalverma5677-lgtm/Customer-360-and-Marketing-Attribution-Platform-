{{ config(materialized='table') }}

WITH customers AS (
    SELECT * FROM {{ ref('stg_crm_customers') }}
),

orders AS (
    SELECT * FROM {{ ref('stg_crm_orders') }}
),

sessions AS (
    SELECT * FROM {{ ref('int_web_sessions') }}
),

-- Aggregate orders per customer
customer_orders AS (
    SELECT
        customer_id,
        MIN(order_timestamp) AS first_order_timestamp,
        MAX(order_timestamp) AS last_order_timestamp,
        DATE(MIN(order_date)) AS first_order_date,
        DATE(MAX(order_date)) AS last_order_date,
        COUNT(order_id) AS lifetime_orders_count,
        ROUND(SUM(total_revenue_usd), 2) AS lifetime_revenue_usd,
        ROUND(AVG(total_revenue_usd), 2) AS avg_order_value_usd,
        ROUND(SUM(discount_usd), 2) AS lifetime_discount_usd
    FROM orders
    GROUP BY customer_id
),

-- Aggregate web session activity & acquisition touchpoint
customer_web AS (
    SELECT
        canonical_customer_id,
        MIN(session_start_timestamp) AS first_seen_timestamp,
        MAX(session_start_timestamp) AS last_seen_timestamp,
        COUNT(session_id) AS lifetime_sessions_count,
        ARRAY_AGG(channel_grouping ORDER BY session_start_timestamp ASC LIMIT 1)[OFFSET(0)] AS first_acquisition_channel,
        ARRAY_AGG(channel_grouping ORDER BY session_start_timestamp DESC LIMIT 1)[OFFSET(0)] AS last_active_channel
    FROM sessions
    GROUP BY canonical_customer_id
),

-- Reference analysis date (for deterministic reproducible scoring)
scoring_base AS (
    SELECT
        c.customer_id AS canonical_customer_id,
        c.email,
        c.first_name,
        c.last_name,
        c.full_name,
        c.phone,
        c.country,
        c.region,
        c.city,
        c.signup_timestamp,
        w.first_seen_timestamp,
        w.last_seen_timestamp,
        COALESCE(w.lifetime_sessions_count, 0) AS lifetime_sessions_count,
        w.first_acquisition_channel,
        w.last_active_channel,

        COALESCE(o.lifetime_orders_count, 0) AS lifetime_orders_count,
        COALESCE(o.lifetime_revenue_usd, 0.0) AS lifetime_revenue_usd,
        COALESCE(o.avg_order_value_usd, 0.0) AS avg_order_value_usd,
        o.first_order_timestamp,
        o.last_order_timestamp,

        -- Recency: Days since last order (using reference date 2026-10-28)
        DATE_DIFF(DATE('2026-10-28'), COALESCE(o.last_order_date, DATE('2026-08-01')), DAY) AS recency_days,
        COALESCE(o.lifetime_orders_count, 0) AS frequency_orders,
        COALESCE(o.lifetime_revenue_usd, 0.0) AS monetary_usd

    FROM customers c
    LEFT JOIN customer_orders o
        ON c.customer_id = o.customer_id
    LEFT JOIN customer_web w
        ON c.customer_id = w.canonical_customer_id
),

-- Quintile Scoring for RFM
rfm_scored AS (
    SELECT
        *,
        -- R Score: 5 is best (most recent / lowest recency days)
        6 - NTILE(5) OVER(ORDER BY recency_days ASC) AS r_score,
        -- F Score: 5 is best (highest order frequency)
        NTILE(5) OVER(ORDER BY frequency_orders ASC) AS f_score,
        -- M Score: 5 is best (highest total spend)
        NTILE(5) OVER(ORDER BY monetary_usd ASC) AS m_score
    FROM scoring_base
),

-- Final Segment Assignment & Predictive CLV
final_segmented AS (
    SELECT
        *,
        CONCAT(CAST(r_score AS STRING), CAST(f_score AS STRING), CAST(m_score AS STRING)) AS rfm_score_combined,
        ROUND((r_score + f_score + m_score) / 3.0, 2) AS rfm_score_average,

        -- Standard Industry RFM Segmentation Matrix
        CASE
            WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
            WHEN r_score >= 4 AND f_score <= 2 THEN 'Recent Customers'
            WHEN r_score >= 3 AND f_score <= 2 THEN 'Potential Loyalists'
            WHEN r_score = 3 AND f_score = 3 THEN 'Promising'
            WHEN r_score = 2 AND f_score >= 3 THEN 'Customers Needing Attention'
            WHEN r_score = 2 AND f_score <= 2 THEN 'About to Sleep'
            WHEN r_score = 1 AND f_score >= 4 THEN 'Can\'t Lose Them'
            WHEN r_score = 1 AND f_score >= 2 THEN 'At Risk'
            WHEN r_score = 1 AND f_score = 1 AND monetary_usd > 200 THEN 'Hibernating'
            ELSE 'Lost'
        END AS rfm_segment,

        -- Predictive CLV (12-Month forward projection):
        -- CLV = Historical Revenue + [AOV * Projected Purchases in 12M * (1 - Churn Risk)]
        ROUND(
            monetary_usd + (
                avg_order_value_usd * (frequency_orders * 1.5) * (
                    CASE
                        WHEN r_score >= 4 THEN 0.85  -- 85% retention likelihood
                        WHEN r_score = 3 THEN 0.65
                        WHEN r_score = 2 THEN 0.40
                        ELSE 0.15                    -- 15% retention likelihood for dormant
                    END
                )
            ),
            2
        ) AS clv_predicted_12m

    FROM rfm_scored
)

SELECT * FROM final_segmented

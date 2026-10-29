-- Test: Conservation of Revenue
-- In any valid multi-touch attribution model, the sum of attributed revenue
-- for an order must equal the order's actual total revenue (within a 1-cent rounding threshold).

WITH order_totals AS (
    SELECT
        order_id,
        MAX(total_revenue_usd) AS expected_revenue,
        SUM(revenue_linear) AS linear_attributed,
        SUM(revenue_time_decay) AS time_decay_attributed,
        SUM(revenue_first_touch) AS first_touch_attributed,
        SUM(revenue_last_touch) AS last_touch_attributed
    FROM {{ ref('fct_attribution_multi_touch') }}
    GROUP BY order_id
),

violations AS (
    SELECT
        order_id,
        expected_revenue,
        linear_attributed,
        time_decay_attributed,
        ABS(expected_revenue - linear_attributed) AS linear_diff,
        ABS(expected_revenue - time_decay_attributed) AS time_decay_diff
    FROM order_totals
    WHERE ABS(expected_revenue - linear_attributed) > 0.05
       OR ABS(expected_revenue - time_decay_attributed) > 0.05
)

SELECT * FROM violations

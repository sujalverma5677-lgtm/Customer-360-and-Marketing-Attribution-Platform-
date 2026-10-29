{{ config(materialized='table') }}

WITH spend AS (
    SELECT
        channel_name,
        ROUND(SUM(spend_usd), 2) AS total_spend_usd,
        SUM(clicks) AS total_clicks,
        SUM(impressions) AS total_impressions,
        ROUND(AVG(cost_per_click), 2) AS avg_cpc,
        ROUND(SUM(clicks) * 100.0 / NULLIF(SUM(impressions), 0), 2) AS blended_ctr_pct
    FROM {{ ref('stg_ad_spend') }}
    GROUP BY channel_name
),

attribution AS (
    SELECT
        channel_grouping AS channel_name,
        
        -- Attributed Revenues
        ROUND(SUM(revenue_first_touch), 2) AS revenue_first_touch,
        ROUND(SUM(revenue_last_touch), 2) AS revenue_last_touch,
        ROUND(SUM(revenue_linear), 2) AS revenue_linear,
        ROUND(SUM(revenue_time_decay), 2) AS revenue_time_decay,
        ROUND(SUM(revenue_position_based), 2) AS revenue_position_based,

        -- Attributed Conversions
        ROUND(SUM(conversions_first_touch), 2) AS conversions_first_touch,
        ROUND(SUM(conversions_last_touch), 2) AS conversions_last_touch,
        ROUND(SUM(conversions_linear), 2) AS conversions_linear,
        ROUND(SUM(conversions_time_decay), 2) AS conversions_time_decay,
        ROUND(SUM(conversions_position_based), 2) AS conversions_position_based

    FROM {{ ref('fct_attribution_multi_touch') }}
    GROUP BY channel_grouping
),

joined AS (
    SELECT
        COALESCE(s.channel_name, a.channel_name) AS channel_name,
        COALESCE(s.total_spend_usd, 0.0) AS total_spend_usd,
        COALESCE(s.total_clicks, 0) AS total_clicks,
        COALESCE(s.total_impressions, 0) AS total_impressions,
        COALESCE(s.avg_cpc, 0.0) AS avg_cpc,
        COALESCE(s.blended_ctr_pct, 0.0) AS blended_ctr_pct,

        -- Revenues
        COALESCE(a.revenue_first_touch, 0.0) AS revenue_first_touch,
        COALESCE(a.revenue_last_touch, 0.0) AS revenue_last_touch,
        COALESCE(a.revenue_linear, 0.0) AS revenue_linear,
        COALESCE(a.revenue_time_decay, 0.0) AS revenue_time_decay,
        COALESCE(a.revenue_position_based, 0.0) AS revenue_position_based,

        -- Conversions
        COALESCE(a.conversions_first_touch, 0.0) AS conversions_first_touch,
        COALESCE(a.conversions_last_touch, 0.0) AS conversions_last_touch,
        COALESCE(a.conversions_linear, 0.0) AS conversions_linear,
        COALESCE(a.conversions_time_decay, 0.0) AS conversions_time_decay,
        COALESCE(a.conversions_position_based, 0.0) AS conversions_position_based

    FROM spend s
    FULL OUTER JOIN attribution a
        ON s.channel_name = a.channel_name
),

metrics_calculated AS (
    SELECT
        *,
        -- ROAS Calculations (Revenue / Spend)
        ROUND(revenue_first_touch / NULLIF(total_spend_usd, 0), 2) AS roas_first_touch,
        ROUND(revenue_last_touch / NULLIF(total_spend_usd, 0), 2) AS roas_last_touch,
        ROUND(revenue_linear / NULLIF(total_spend_usd, 0), 2) AS roas_linear,
        ROUND(revenue_time_decay / NULLIF(total_spend_usd, 0), 2) AS roas_time_decay,
        ROUND(revenue_position_based / NULLIF(total_spend_usd, 0), 2) AS roas_position_based,

        -- CPA / CAC Calculations (Spend / Conversions)
        ROUND(total_spend_usd / NULLIF(conversions_first_touch, 0), 2) AS cpa_first_touch,
        ROUND(total_spend_usd / NULLIF(conversions_last_touch, 0), 2) AS cpa_last_touch,
        ROUND(total_spend_usd / NULLIF(conversions_linear, 0), 2) AS cpa_linear,
        ROUND(total_spend_usd / NULLIF(conversions_time_decay, 0), 2) AS cpa_time_decay,

        -- Net ROI % under Time-Decay Attribution
        ROUND(((revenue_time_decay - total_spend_usd) / NULLIF(total_spend_usd, 0)) * 100.0, 1) AS net_roi_pct_time_decay,

        -- Executive Decision Recommendation
        CASE
            WHEN total_spend_usd = 0 THEN 'Earned / Zero-Spend Engine (Maintain SEO/Email Flows)'
            -- High First-Touch, Low Last-Touch: Discovery engine undervalued by Last-Touch!
            WHEN (revenue_first_touch / NULLIF(total_spend_usd, 0)) >= 3.0 AND (revenue_last_touch / NULLIF(total_spend_usd, 0)) < 2.0 THEN
                'SCALE BUDGET (+25% to +40%): Top-of-Funnel Driver. Defunding causes pipeline collapse.'
            -- High ROAS across all models
            WHEN (revenue_time_decay / NULLIF(total_spend_usd, 0)) >= 4.0 THEN
                'SCALE AGGRESSIVELY (+35%): High-margin profitable channel.'
            -- Moderate ROAS (2.0 - 4.0)
            WHEN (revenue_time_decay / NULLIF(total_spend_usd, 0)) >= 2.0 THEN
                'MAINTAIN / OPTIMIZE CREATIVE: Steady profitable performance.'
            -- Underperforming ROAS (< 2.0)
            ELSE
                'TRIM BUDGET (-20% to -35%): Reallocate budget to high-yield discovery channels.'
        END AS executive_budget_recommendation

    FROM joined
)

SELECT * FROM metrics_calculated
ORDER BY total_spend_usd DESC

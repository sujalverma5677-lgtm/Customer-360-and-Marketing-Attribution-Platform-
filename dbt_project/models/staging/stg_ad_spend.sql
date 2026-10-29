{{ config(materialized='view') }}

WITH raw_source AS (
    SELECT * FROM {{ source('raw_ecommerce', 'raw_ad_spend') }}
),

transformed AS (
    SELECT
        DATE(date) AS spend_date,
        TRIM(channel_name) AS channel_name,
        LOWER(TRIM(utm_source)) AS utm_source,
        LOWER(TRIM(utm_medium)) AS utm_medium,
        LOWER(TRIM(utm_campaign)) AS utm_campaign,
        CAST(daily_spend AS FLOAT64) AS spend_usd,
        CAST(clicks AS INT64) AS clicks,
        CAST(impressions AS INT64) AS impressions,
        CAST(cpc AS FLOAT64) AS cost_per_click,
        CAST(ctr_percent AS FLOAT64) AS click_through_rate_pct
    FROM raw_source
)

SELECT * FROM transformed

{{ config(materialized='view') }}

WITH raw_source AS (
    SELECT * FROM {{ source('raw_ecommerce', 'raw_ga4_events') }}
),

transformed AS (
    SELECT
        -- Surrogate Key
        {{ dbt_utils.generate_surrogate_key(['user_pseudo_id', 'event_timestamp', 'event_name']) }} AS event_id,
        
        -- Event Metadata
        PARSE_DATE('%Y%m%d', CAST(event_date AS STRING)) AS event_date,
        TIMESTAMP_MICROS(CAST(event_timestamp AS INT64)) AS event_timestamp,
        LOWER(TRIM(event_name)) AS event_name,
        
        -- Identifiers
        TRIM(user_pseudo_id) AS user_pseudo_id,
        NULLIF(TRIM(user_id), '') AS user_id,
        NULLIF(TRIM(email_hash), '') AS email_hash,
        
        -- Session Info
        TRIM(ga_session_id) AS session_id,
        CAST(ga_session_number AS INT64) AS session_number,
        
        -- Traffic Attribution Context
        COALESCE(LOWER(NULLIF(TRIM(source), '')), '(direct)') AS utm_source,
        COALESCE(LOWER(NULLIF(TRIM(medium), '')), '(none)') AS utm_medium,
        COALESCE(LOWER(NULLIF(TRIM(campaign), '')), '(direct)') AS utm_campaign,
        
        -- Channel Grouping Logic (GA4 Default Channel Grouping Standard)
        CASE
            WHEN LOWER(source) = '(direct)' AND (LOWER(medium) IN ('(none)', '(not set)', '')) THEN 'Direct'
            WHEN LOWER(medium) = 'organic' OR LOWER(source) LIKE '%google%' AND LOWER(medium) = 'organic' THEN 'Organic Search'
            WHEN LOWER(medium) IN ('cpc', 'ppc', 'paidsearch') AND LOWER(campaign) LIKE '%brand%' AND LOWER(campaign) NOT LIKE '%nonbrand%' THEN 'Paid Search - Brand'
            WHEN LOWER(medium) IN ('cpc', 'ppc', 'paidsearch') THEN 'Paid Search - Generic'
            WHEN LOWER(medium) IN ('paid_social', 'paidsocial') AND LOWER(source) = 'tiktok' THEN 'Paid Video - TikTok Ads'
            WHEN LOWER(medium) IN ('paid_social', 'paidsocial') AND LOWER(source) = 'facebook' AND LOWER(campaign) LIKE '%retargeting%' THEN 'Paid Social - Meta Retargeting'
            WHEN LOWER(medium) IN ('paid_social', 'paidsocial') AND LOWER(source) = 'facebook' THEN 'Paid Social - Meta Prospecting'
            WHEN LOWER(medium) = 'email' OR LOWER(source) IN ('klaviyo', 'mailchimp') THEN 'Email Marketing'
            ELSE 'Other / Referral'
        END AS default_channel_grouping,

        -- Page Context
        page_location,
        page_title,

        -- Geography & Technology
        country,
        region,
        city,
        device_category,
        operating_system,
        browser,

        -- E-Commerce Value
        NULLIF(TRIM(transaction_id), '') AS transaction_id,
        CAST(COALESCE(event_value_usd, 0.0) AS FLOAT64) AS event_value_usd

    FROM raw_source
)

SELECT * FROM transformed

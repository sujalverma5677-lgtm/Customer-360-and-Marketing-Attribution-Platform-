{{ config(materialized='view') }}

WITH raw_source AS (
    SELECT * FROM {{ source('raw_ecommerce', 'raw_crm_orders') }}
),

transformed AS (
    SELECT
        TRIM(order_id) AS order_id,
        TRIM(customer_id) AS customer_id,
        TIMESTAMP(order_timestamp) AS order_timestamp,
        DATE(order_date) AS order_date,
        CAST(subtotal AS FLOAT64) AS subtotal_usd,
        CAST(discount_amount AS FLOAT64) AS discount_usd,
        CAST(tax_amount AS FLOAT64) AS tax_usd,
        CAST(shipping_amount AS FLOAT64) AS shipping_usd,
        CAST(total_revenue AS FLOAT64) AS total_revenue_usd,
        LOWER(TRIM(order_status)) AS order_status,
        LOWER(TRIM(payment_method)) AS payment_method,
        TRIM(conversion_session_id) AS conversion_session_id,
        LOWER(TRIM(last_touch_source)) AS last_touch_source,
        LOWER(TRIM(last_touch_medium)) AS last_touch_medium,
        LOWER(TRIM(last_touch_campaign)) AS last_touch_campaign
    FROM raw_source
    WHERE LOWER(TRIM(order_status)) = 'completed'
)

SELECT * FROM transformed

{{ config(materialized='view') }}

WITH raw_source AS (
    SELECT * FROM {{ source('raw_ecommerce', 'raw_crm_customers') }}
),

transformed AS (
    SELECT
        TRIM(customer_id) AS customer_id,
        LOWER(TRIM(email)) AS email,
        LOWER(TRIM(email_hash)) AS email_hash,
        TRIM(first_name) AS first_name,
        TRIM(last_name) AS last_name,
        CONCAT(TRIM(first_name), ' ', TRIM(last_name)) AS full_name,
        TRIM(phone) AS phone,
        TIMESTAMP(signup_timestamp) AS signup_timestamp,
        DATE(signup_date) AS signup_date,
        country,
        region,
        city,
        LOWER(lifecycle_stage) AS lifecycle_stage
    FROM raw_source
)

SELECT * FROM transformed

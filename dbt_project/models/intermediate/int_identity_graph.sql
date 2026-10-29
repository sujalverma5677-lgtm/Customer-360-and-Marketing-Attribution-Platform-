{{ config(materialized='view') }}

-- Reads from the resolved identity cluster mapping table
WITH identity_nodes AS (
    SELECT
        identifier_type,
        identifier_value,
        canonical_customer_id,
        resolution_type,
        confidence_score,
        total_devices_linked,
        is_known_customer
    FROM {{ ref('int_identity_mapping_seed') }}
)

SELECT * FROM identity_nodes

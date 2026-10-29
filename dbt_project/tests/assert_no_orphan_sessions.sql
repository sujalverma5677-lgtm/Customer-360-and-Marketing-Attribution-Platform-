-- Test: Referential Integrity of Touchpoint Journeys
-- Every touchpoint linked to an order must have a valid customer_id and order_id.

SELECT
    touchpoint_id,
    order_id,
    customer_id
FROM {{ ref('fct_attribution_multi_touch') }}
WHERE order_id IS NULL
   OR customer_id IS NULL
   OR customer_id = ''

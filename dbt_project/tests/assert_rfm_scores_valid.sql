-- Test: RFM Scoring Boundary Check
-- R, F, and M quintile scores must strictly be integers between 1 and 5.

SELECT
    canonical_customer_id,
    r_score,
    f_score,
    m_score
FROM {{ ref('dim_customers_360') }}
WHERE r_score NOT BETWEEN 1 AND 5
   OR f_score NOT BETWEEN 1 AND 5
   OR m_score NOT BETWEEN 1 AND 5

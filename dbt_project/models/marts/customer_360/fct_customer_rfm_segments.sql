{{ config(materialized='table') }}

WITH dim_customers AS (
    SELECT * FROM {{ ref('dim_customers_360') }}
),

segment_summary AS (
    SELECT
        rfm_segment,
        COUNT(canonical_customer_id) AS customer_count,
        ROUND(COUNT(canonical_customer_id) * 100.0 / SUM(COUNT(canonical_customer_id)) OVER(), 2) AS pct_of_customers,
        ROUND(SUM(lifetime_revenue_usd), 2) AS total_segment_revenue_usd,
        ROUND(SUM(lifetime_revenue_usd) * 100.0 / SUM(SUM(lifetime_revenue_usd)) OVER(), 2) AS pct_of_revenue,
        ROUND(AVG(recency_days), 1) AS avg_recency_days,
        ROUND(AVG(frequency_orders), 2) AS avg_frequency_orders,
        ROUND(AVG(monetary_usd), 2) AS avg_monetary_spend_usd,
        ROUND(AVG(clv_predicted_12m), 2) AS avg_clv_predicted_12m,
        
        -- Recommended Marketing Strategy per Segment
        CASE rfm_segment
            WHEN 'Champions' THEN 'VIP Rewards, Early Access, Ambassador Referral Program'
            WHEN 'Loyal Customers' THEN 'Upsell Premium Tiers, Loyalty Points, Product Feedback'
            WHEN 'Potential Loyalists' THEN 'Cross-sell complementary gear, recommend bundles'
            WHEN 'Recent Customers' THEN 'Onboarding email sequence, post-purchase delight, brand storytelling'
            WHEN 'Promising' THEN 'Time-limited discounts, personalized recommendations'
            WHEN 'Customers Needing Attention' THEN 'Reactivation offer, customer support check-in'
            WHEN 'About to Sleep' THEN 'Aggressive win-back discount, surveys to diagnose friction'
            WHEN 'At Risk' THEN 'High-touch outreach, personalized 20% discount code, re-engagement ads'
            WHEN 'Can\'t Lose Them' THEN 'White-glove executive reachout, win them back before churn is permanent'
            WHEN 'Hibernating' THEN 'Standard automated low-cost email reactivation campaign'
            ELSE 'Sunset email list, suppress from paid ad retargeting to save budget'
        END AS recommended_action

    FROM dim_customers
    GROUP BY rfm_segment
)

SELECT * FROM segment_summary
ORDER BY total_segment_revenue_usd DESC

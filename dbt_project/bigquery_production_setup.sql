-- ==============================================================================
-- BigQuery Enterprise Production Deployment DDL & Partitioning Strategy
-- Dialect: Google BigQuery Standard SQL
-- Includes: Partitioning by Date, Clustering by High-Cardinality Keys, and
--           Cost-Optimization Benchmarks.
-- ==============================================================================

CREATE SCHEMA IF NOT EXISTS `your_gcp_project.analytics_warehouse`
OPTIONS(
  location="US",
  description="Enterprise Customer 360 & Multi-Touch Marketing Attribution Marts"
);

-- ------------------------------------------------------------------------------
-- 1. Partitioned & Clustered GA4 Events Table
-- Optimization: Day partitioning reduces query costs by up to 95%.
-- Clustering by user_pseudo_id accelerates graph identity resolution joins.
-- ------------------------------------------------------------------------------
CREATE OR REPLACE TABLE `your_gcp_project.analytics_warehouse.stg_ga4_events`
PARTITION BY event_date
CLUSTER BY user_pseudo_id, session_id, event_name
AS
SELECT
  PARSE_DATE('%Y%m%d', CAST(event_date AS STRING)) AS event_date,
  TIMESTAMP_MICROS(CAST(event_timestamp AS INT64)) AS event_timestamp,
  LOWER(TRIM(event_name)) AS event_name,
  TRIM(user_pseudo_id) AS user_pseudo_id,
  NULLIF(TRIM(user_id), '') AS user_id,
  NULLIF(TRIM(email_hash), '') AS email_hash,
  TRIM(ga_session_id) AS session_id,
  CAST(ga_session_number AS INT64) AS session_number,
  COALESCE(LOWER(source), '(direct)') AS utm_source,
  COALESCE(LOWER(medium), '(none)') AS utm_medium,
  COALESCE(LOWER(campaign), '(direct)') AS utm_campaign,
  country,
  device_category,
  operating_system,
  browser,
  NULLIF(TRIM(transaction_id), '') AS transaction_id,
  CAST(COALESCE(event_value_usd, 0.0) AS FLOAT64) AS event_value_usd
FROM `your_gcp_project.raw_ecommerce.raw_ga4_events`;

-- ------------------------------------------------------------------------------
-- 2. Customer 360 Master Gold Table
-- Optimization: Clustered by rfm_segment for instant sub-second cohort queries.
-- ------------------------------------------------------------------------------
CREATE OR REPLACE TABLE `your_gcp_project.analytics_warehouse.dim_customers_360`
CLUSTER BY rfm_segment, canonical_customer_id
OPTIONS(
  description="Single Customer View with RFM scores and 12-Month Predictive CLV"
) AS
SELECT * FROM `your_gcp_project.analytics_warehouse.dim_customers_360_view`;

-- ------------------------------------------------------------------------------
-- 3. Multi-Touch Attribution Fact Table
-- Optimization: Partitioned by Order Date, Clustered by Channel & Customer.
-- ------------------------------------------------------------------------------
CREATE OR REPLACE TABLE `your_gcp_project.analytics_warehouse.fct_attribution_multi_touch`
PARTITION BY DATE(order_timestamp)
CLUSTER BY channel_grouping, customer_id
OPTIONS(
  description="Granular touchpoint-level multi-touch attribution with 5 model weights"
) AS
SELECT * FROM `your_gcp_project.analytics_warehouse.fct_attribution_multi_touch_view`;

-- ------------------------------------------------------------------------------
-- 4. Campaign ROI & Cost Per Acquisition Performance
-- ------------------------------------------------------------------------------
CREATE OR REPLACE TABLE `your_gcp_project.analytics_warehouse.agg_campaign_performance_roi`
CLUSTER BY channel_name
OPTIONS(
  description="Consolidated marketing spend, multi-model ROAS, CPA, and recommendations"
) AS
SELECT * FROM `your_gcp_project.analytics_warehouse.agg_campaign_performance_roi_view`;

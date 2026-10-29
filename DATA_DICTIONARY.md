# Enterprise Data Dictionary & Schema Documentation
## Customer 360 & Marketing Attribution Platform

This document outlines the data contracts, primary keys, foreign keys, and column definitions across all layers of the warehouse.

---

### Warehouse Layer Overview
| Layer | Namespace | Materialization | Description |
|---|---|---|---|
| **Raw Ingestion** | `raw_ecommerce.*` | Tables (CSV/Streaming) | Direct event ingestion from GA4, CRM extracts, and Ad APIs |
| **Staging** | `staging.stg_*` | Views | Standardized schemas, unnested JSON/structs, type casting |
| **Intermediate** | `intermediate.int_*` | Views / Ephemeral | Identity resolution graph stitching, session aggregations |
| **Gold Marts** | `customer_360.*` | Tables | Customer 360 profiles, RFM segments, predictive CLV |
| **Gold Marts** | `marketing_attribution.*` | Tables | Multi-touch attribution allocations, campaign ROI & CPA |
| **Reporting** | `tableau_exports.*` | CSV / Hyper | Production-ready reporting data sources for Tableau |

---

### 1. Customer 360: `dim_customers_360`
**Primary Key**: `canonical_customer_id`  
**Description**: Single customer view uniting behavioral web history, CRM profiles, and predictive lifetime value.

| Column Name | Data Type | Nullable | Description | Example |
|---|---|---|---|---|
| `canonical_customer_id` | STRING | No | Unique unified enterprise identifier | `CUST-10042` |
| `email` | STRING | No | Verified primary customer email | `jane.doe@gmail.com` |
| `first_name` | STRING | Yes | Customer given name | `Jane` |
| `last_name` | STRING | Yes | Customer family name | `Doe` |
| `phone` | STRING | Yes | Customer phone number | `+1-555-482-1984` |
| `country` | STRING | Yes | Primary country of residence | `United States` |
| `region` | STRING | Yes | State / province | `New York` |
| `city` | STRING | Yes | City | `New York` |
| `signup_timestamp` | TIMESTAMP | No | Date and time customer registered | `2026-08-14 14:22:10` |
| `first_seen_timestamp` | TIMESTAMP | Yes | Timestamp of very first recorded web touchpoint | `2026-08-02 09:12:00` |
| `last_seen_timestamp` | TIMESTAMP | Yes | Timestamp of most recent web session | `2026-10-25 18:40:00` |
| `lifetime_sessions_count` | INT64 | No | Cumulative number of web browsing sessions | `14` |
| `first_acquisition_channel`| STRING | No | Channel that drove first brand interaction | `Paid Video - TikTok Ads` |
| `last_active_channel` | STRING | No | Channel that drove the most recent visit | `Email Marketing` |
| `lifetime_orders_count` | INT64 | No | Total number of completed orders | `4` |
| `lifetime_revenue_usd` | FLOAT64 | No | Cumulative net revenue generated in USD | `1240.50` |
| `avg_order_value_usd` | FLOAT64 | No | Average order value (AOV) | `310.13` |
| `recency_days` | INT64 | No | Days elapsed between last purchase and analysis date | `3` |
| `frequency_orders` | INT64 | No | Order count used for RFM scoring | `4` |
| `monetary_usd` | FLOAT64 | No | Total spend used for RFM scoring | `1240.50` |
| `r_score` | INT64 | No | Recency quintile score (1 to 5, 5 is best) | `5` |
| `f_score` | INT64 | No | Frequency quintile score (1 to 5, 5 is best) | `5` |
| `m_score` | INT64 | No | Monetary quintile score (1 to 5, 5 is best) | `5` |
| `rfm_score_combined` | STRING | No | Concatenated RFM code | `555` |
| `rfm_score_average` | FLOAT64 | No | Unweighted average score | `5.0` |
| `rfm_segment` | STRING | No | Cohort classification | `Champions` |
| `clv_predicted_12m` | FLOAT64 | No | Projected 12-month forward customer lifetime value | `2950.80` |

---

### 2. Multi-Touch Attribution: `fct_attribution_multi_touch`
**Primary Key**: `touchpoint_id` (`order_id` + `session_id`)  
**Foreign Keys**: `order_id` (`stg_crm_orders.order_id`), `customer_id` (`dim_customers_360.canonical_customer_id`)  
**Description**: Granular touchpoint conversion table allocating credit across five distinct attribution models within a 30-day lookback window.

| Column Name | Data Type | Nullable | Description | Example |
|---|---|---|---|---|
| `touchpoint_id` | STRING | No | Surrogate key for order-session touchpoint | `ORD-1045_sess_173000` |
| `order_id` | STRING | No | Completed order identifier | `ORD-1045` |
| `customer_id` | STRING | No | Canonical customer identifier | `CUST-10042` |
| `session_id` | STRING | No | Web session identifier | `sess_173000` |
| `session_start_timestamp`| TIMESTAMP | No | Timestamp of web session start | `2026-10-14 11:20:00` |
| `order_timestamp` | TIMESTAMP | No | Timestamp when order was placed | `2026-10-21 16:45:00` |
| `channel_grouping` | STRING | No | Standardized marketing channel grouping | `Paid Video - TikTok Ads`|
| `utm_source` | STRING | Yes | Tracking source parameter | `tiktok` |
| `utm_medium` | STRING | Yes | Tracking medium parameter | `paid_social` |
| `utm_campaign` | STRING | Yes | Tracking campaign name | `tiktok_ugc_viral_spring`|
| `device_category` | STRING | Yes | Device category (`mobile`, `desktop`, `tablet`)| `mobile` |
| `days_before_order` | FLOAT64 | No | Time lag between touchpoint and checkout (days) | `7.2` |
| `touchpoint_order_asc` | INT64 | No | Chronological order of touchpoint (1 = First Touch)| `1` |
| `touchpoint_order_desc`| INT64 | No | Reverse chronological order (1 = Last Touch) | `3` |
| `total_journey_touchpoints`| INT64 | No | Total touchpoints in this conversion journey | `3` |
| `total_revenue` | FLOAT64 | No | Total order transaction revenue in USD | `380.00` |
| `weight_first_touch` | FLOAT64 | No | Credit weight under First-Touch Attribution | `1.0` |
| `weight_last_touch` | FLOAT64 | No | Credit weight under Last-Touch Attribution | `0.0` |
| `weight_linear` | FLOAT64 | No | Credit weight under Linear Attribution ($1/N$) | `0.3333` |
| `weight_time_decay` | FLOAT64 | No | Normalized exponential decay weight ($2^{-\Delta t / 7}$) | `0.1982` |
| `weight_position_based`| FLOAT64 | No | U-Shaped weight (40% first, 40% last, 20% middle) | `0.40` |
| `revenue_first_touch` | FLOAT64 | No | Attributed revenue under First-Touch ($) | `380.00` |
| `revenue_last_touch` | FLOAT64 | No | Attributed revenue under Last-Touch ($) | `0.00` |
| `revenue_linear` | FLOAT64 | No | Attributed revenue under Linear ($) | `126.67` |
| `revenue_time_decay` | FLOAT64 | No | Attributed revenue under Time-Decay ($) | `75.32` |
| `revenue_position_based`| FLOAT64 | No | Attributed revenue under Position-Based ($) | `152.00` |

---

### 3. Campaign Performance & ROI: `agg_campaign_performance_roi`
**Primary Key**: `channel_name`  
**Description**: Consolidated channel economics synthesizing ad spend, clicks, impressions, multi-model attributed revenue, ROAS, and Cost Per Acquisition.

| Column Name | Data Type | Nullable | Description | Example |
|---|---|---|---|---|
| `channel_name` | STRING | No | Unified channel name | `Paid Video - TikTok Ads`|
| `total_spend_usd` | FLOAT64 | No | Total marketing spend in USD | `29562.68` |
| `total_clicks` | INT64 | No | Total ad clicks delivered | `31250` |
| `total_impressions` | INT64 | No | Total ad impressions | `984000` |
| `avg_cpc` | FLOAT64 | No | Average cost per click ($) | `0.95` |
| `blended_ctr_pct` | FLOAT64 | No | Click-through rate percentage (%) | `3.18` |
| `revenue_first_touch` | FLOAT64 | No | First-Touch attributed revenue ($) | `168679.01` |
| `revenue_last_touch` | FLOAT64 | No | Last-Touch attributed revenue ($) | `24295.56` |
| `revenue_linear` | FLOAT64 | No | Linear attributed revenue ($) | `97525.96` |
| `revenue_time_decay` | FLOAT64 | No | Time-Decay attributed revenue ($) | `87931.74` |
| `revenue_position_based`| FLOAT64 | No | Position-Based attributed revenue ($) | `105120.40` |
| `roas_first_touch` | FLOAT64 | Yes | First-Touch Return on Ad Spend ($Rev / Spend$) | `5.71` |
| `roas_last_touch` | FLOAT64 | Yes | Last-Touch Return on Ad Spend ($Rev / Spend$) | `0.82` |
| `roas_time_decay` | FLOAT64 | Yes | Time-Decay Return on Ad Spend ($Rev / Spend$) | `2.97` |
| `cpa_last_touch` | FLOAT64 | Yes | Cost Per Acquisition under Last Touch ($) | `434.75` |
| `cpa_time_decay` | FLOAT64 | Yes | Cost Per Acquisition under Time Decay ($) | `131.83` |
| `net_roi_pct_time_decay`| FLOAT64 | Yes | Net ROI %: $((Rev - Spend) / Spend) \times 100$ | `197.4` |
| `executive_budget_recommendation` | STRING | No | Prescriptive action for capital allocation | `SCALE UP (+35%): Key Discovery Driver...` |

---

### 4. Identity Mapping: `int_identity_mapping`
**Primary Key**: `identifier_value`  
**Description**: Disjoint Set Union mapping connecting disparate cookies and emails to canonical customer IDs.

| Column Name | Data Type | Nullable | Description | Example |
|---|---|---|---|---|
| `identifier_type` | STRING | No | Type of identifier (`user_pseudo_id`, `email_hash`, `customer_id`)| `user_pseudo_id` |
| `identifier_value` | STRING | No | Raw identifier string or hash | `598124912.172401829` |
| `canonical_customer_id`| STRING | No | Resolved master customer ID | `CUST-10042` |
| `resolution_type` | STRING | No | `AUTHENTICATED_CRM`, `PROBABILISTIC_EMAIL`, `ANONYMOUS_COOKIE` | `AUTHENTICATED_CRM` |
| `confidence_score` | FLOAT64 | No | Cluster linkage confidence (0.0 to 1.0) | `1.0` |
| `cluster_size` | INT64 | No | Number of identifiers merged into this entity | `3` |
| `total_devices_linked` | INT64 | No | Distinct device cookies linked to this customer | `2` |
| `is_known_customer` | INT64 | No | 1 if resolved to known CRM record, 0 if anonymous | `1` |

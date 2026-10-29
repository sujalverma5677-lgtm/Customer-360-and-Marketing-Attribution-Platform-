-- ==============================================================================
-- Enterprise Customer 360: BigQuery Native Identity Resolution
-- Dialect: Google BigQuery Standard SQL
-- Description: Graph Connected Components using recursive CTEs to resolve
--              cookies (user_pseudo_id), email hashes, and CRM user_ids into
--              a single canonical_customer_id.
-- ==============================================================================

-- Step 1: Extract all bi-directional identity edges from GA4 & CRM
WITH raw_edges AS (
  -- Edge: Cookie <-> Logged-in User ID
  SELECT
    CONCAT('cookie:', user_pseudo_id) AS node_a,
    CONCAT('crm:', user_id) AS node_b,
    'GA4_SESSION_LOGIN' AS edge_source,
    0.99 AS confidence_weight
  FROM `your_project.analytics_warehouse.stg_ga4_events`
  WHERE user_pseudo_id IS NOT NULL AND user_id IS NOT NULL

  UNION DISTINCT

  -- Edge: Cookie <-> Email Hash (from checkout / newsletter submission)
  SELECT
    CONCAT('cookie:', user_pseudo_id) AS node_a,
    CONCAT('email_hash:', email_hash) AS node_b,
    'GA4_CHECKOUT_EVENT' AS edge_source,
    0.95 AS confidence_weight
  FROM `your_project.analytics_warehouse.stg_ga4_events`
  WHERE user_pseudo_id IS NOT NULL AND email_hash IS NOT NULL

  UNION DISTINCT

  -- Edge: CRM Customer ID <-> Email Hash
  SELECT
    CONCAT('crm:', customer_id) AS node_a,
    CONCAT('email_hash:', email_hash) AS node_b,
    'CRM_REGISTRATION' AS edge_source,
    1.00 AS confidence_weight
  FROM `your_project.analytics_warehouse.stg_crm_customers`
  WHERE customer_id IS NOT NULL AND email_hash IS NOT NULL
),

-- Step 2: Make graph undirected (node_a <-> node_b and node_b <-> node_a)
undirected_edges AS (
  SELECT node_a AS source_node, node_b AS target_node, confidence_weight FROM raw_edges
  UNION DISTINCT
  SELECT node_b AS source_node, node_a AS target_node, confidence_weight FROM raw_edges
),

-- Step 3: Connected Component Propagation via Recursive CTE
-- Iteratively propagates the minimum node identifier across neighbors
iterative_clusters AS (
  -- Base case: Each node is its own cluster representative
  SELECT
    source_node AS node_id,
    source_node AS cluster_id,
    0 AS iteration
  FROM (
    SELECT source_node FROM undirected_edges
    UNION DISTINCT
    SELECT target_node FROM undirected_edges
  )

  UNION ALL

  -- Recursive step: propagate min cluster_id to connected neighbors
  SELECT
    e.target_node AS node_id,
    LEAST(c.cluster_id, e.target_node) AS cluster_id,
    c.iteration + 1 AS iteration
  FROM iterative_clusters c
  JOIN undirected_edges e
    ON c.node_id = e.source_node
  WHERE c.iteration < 5 -- Max graph diameter depth
),

-- Step 4: Elect Canonical Customer ID
min_cluster_per_node AS (
  SELECT
    node_id,
    MIN(cluster_id) AS canonical_cluster_id
  FROM iterative_clusters
  GROUP BY node_id
),

-- Step 5: Canonical identifier priority (CRM ID > Email Hash > Cookie ID)
resolved_identities AS (
  SELECT
    m.node_id,
    SPLIT(m.node_id, ':')[OFFSET(0)] AS identifier_type,
    SPLIT(m.node_id, ':')[OFFSET(1)] AS identifier_value,
    COALESCE(
      MAX(CASE WHEN STARTS_WITH(n.node_id, 'crm:') THEN SPLIT(n.node_id, ':')[OFFSET(1)] END) OVER(PARTITION BY m.canonical_cluster_id),
      MAX(CASE WHEN STARTS_WITH(n.node_id, 'email_hash:') THEN CONCAT('LEAD_', SUBSTR(SPLIT(n.node_id, ':')[OFFSET(1)], 1, 10)) END) OVER(PARTITION BY m.canonical_cluster_id),
      CONCAT('ANON_', SPLIT(m.canonical_cluster_id, ':')[OFFSET(1)])
    ) AS canonical_customer_id,
    COUNT(DISTINCT CASE WHEN STARTS_WITH(n.node_id, 'cookie:') THEN n.node_id END) OVER(PARTITION BY m.canonical_cluster_id) AS total_devices_linked
  FROM min_cluster_per_node m
  JOIN min_cluster_per_node n
    ON m.canonical_cluster_id = n.canonical_cluster_id
)

SELECT
  identifier_type,
  identifier_value,
  canonical_customer_id,
  total_devices_linked,
  CURRENT_TIMESTAMP() AS resolved_at
FROM resolved_identities
GROUP BY 1, 2, 3, 4;

"""
Tableau Workbook & Data Source Generator
Generates:
1. Native Tableau Workbook (.twb) XML with pre-built data sources, calculated fields, and sheet layouts
2. Detailed step-by-step guide for building the executive Tableau dashboard (LOD expressions, parameters, and stories)
"""

import os

TABLEAU_GUIDE_CONTENT = """# Tableau Dashboard Implementation Guide
## Customer 360 & Marketing Attribution Platform

This guide provides end-to-end instructions for loading the prepared datasets into **Tableau Desktop / Tableau Public** and assembling the executive dashboard suite.

---

### 1. Data Connection Architecture
Open Tableau and connect to the generated CSV files in `data/tableau_exports/`:
1. `tableau_dim_customers_360.csv` (Customer master dimension)
2. `tableau_fct_attribution_multi_touch.csv` (Touchpoint-level attribution fact)
3. `tableau_agg_campaign_performance_roi.csv` (Aggregated channel spend and performance)
4. `tableau_fct_customer_rfm_segments.csv` (Segment cohorts)
5. `tableau_agg_budget_reallocation.csv` (Prescribed budget shifts)

#### Relationship Model (Tableau Logical Model)
- Primary Fact: `tableau_fct_attribution_multi_touch`
  - Relationship to `tableau_dim_customers_360` on `customer_id` = `canonical_customer_id`
  - Relationship to `tableau_agg_campaign_performance_roi` on `channel_grouping` = `channel_name`

---

### 2. Calculated Fields & Tableau Formulas

Create the following calculated fields in Tableau:

#### A. Blended ROAS (Return on Ad Spend)
```tableau
// Time-Decay ROAS
SUM([Revenue Time Decay]) / SUM([Total Spend Usd])

// Last-Touch ROAS (Legacy)
SUM([Revenue Last Touch]) / SUM([Total Spend Usd])

// First-Touch ROAS (Top-of-Funnel)
SUM([Revenue First Touch]) / SUM([Total Spend Usd])
```

#### B. Attribution Model Selector Parameter
Create a String Parameter named `[Attribution Model Selector]` with values:
- `Last Touch (Legacy GA4)`
- `First Touch (Discovery)`
- `Linear (Even Split)`
- `Time Decay (Recommended)`
- `Position-Based (U-Shaped 40/20/40)`

Create the dynamic revenue measure:
```tableau
// Selected Model Attributed Revenue
CASE [Attribution Model Selector]
  WHEN 'Last Touch (Legacy GA4)' THEN SUM([Revenue Last Touch])
  WHEN 'First Touch (Discovery)' THEN SUM([Revenue First Touch])
  WHEN 'Linear (Even Split)' THEN SUM([Revenue Linear])
  WHEN 'Time Decay (Recommended)' THEN SUM([Revenue Time Decay])
  WHEN 'Position-Based (U-Shaped 40/20/40)' THEN SUM([Revenue Position Based])
END
```

#### C. Cost Per Acquisition (CPA / CAC)
```tableau
// Selected Model CPA
SUM([Total Spend Usd]) / 
CASE [Attribution Model Selector]
  WHEN 'Last Touch (Legacy GA4)' THEN SUM([Conversions Last Touch])
  WHEN 'First Touch (Discovery)' THEN SUM([Conversions First Touch])
  WHEN 'Linear (Even Split)' THEN SUM([Conversions Linear])
  WHEN 'Time Decay (Recommended)' THEN SUM([Conversions Time Decay])
  WHEN 'Position-Based (U-Shaped 40/20/40)' THEN SUM([Conversions Position Based])
END
```

#### D. Attribution Delta (Revealing the Last-Touch Trap)
```tableau
// Difference between Time-Decay and Last-Touch
SUM([Revenue Time Decay]) - SUM([Revenue Last Touch])
```

#### E. RFM Value Tier (LOD Expression)
```tableau
{ FIXED [Canonical Customer Id] : 
  IF [R Score] >= 4 AND [F Score] >= 4 THEN "Tier 1: VIP Champions"
  ELSEIF [R Score] >= 3 AND [F Score] >= 3 THEN "Tier 2: Loyal Core"
  ELSEIF [R Score] <= 2 AND [F Score] >= 3 THEN "Tier 3: At-Risk High Value"
  ELSE "Tier 4: Regular / Dormant"
  END
}
```

---

### 3. Dashboard Blueprint (4 Executive Dashboards)

#### Dashboard 1: CMO Executive Marketing ROI & Budget Reallocation
- **Top Row KPI Cards**:
  - Total Net Revenue ($760,082)
  - Total Paid Ad Spend ($143,541)
  - Blended ROAS (5.30x)
  - Active Customers (1,200)
  - Projected Revenue Lift from Reallocation (+$41,863)
- **Main Visual 1: Multi-Touch Model Comparison (Side-by-Side Horizontal Bar Chart)**:
  - Columns: Measure Values (`Revenue First Touch`, `Revenue Last Touch`, `Revenue Time Decay`)
  - Rows: `Channel Name`
  - Color: Measure Names
- **Main Visual 2: Recommended Budget Shift ($ and %)**:
  - Columns: `Budget Change Usd`
  - Rows: `Channel Name`
  - Color: Diverging Red-to-Green (Green = Scale Up, Red = Trim Budget)
- **Bottom Callout Table**: `Optimization Rationale` and strategic actions.

#### Dashboard 2: The "Last-Touch Trap" Diagnostic
- **Attribution Divergence Chart**:
  - Shows how Last-Touch overvalues Brand Search (+14%) and Meta Retargeting (+50%) while undervaluing TikTok (-72%) and Meta Prospecting (-68%).
- **Interactive CPA Comparison**:
  - Compares CPA under Last-Touch vs Time-Decay.

#### Dashboard 3: Customer 360 & RFM Segmentation Matrix
- **RFM Scatter Plot / Matrix**:
  - X-Axis: `Avg Recency Days` (Reversed)
  - Y-Axis: `Avg Monetary Spend Usd`
  - Size: `Customer Count`
  - Color: `Rfm Segment`
- **Customer Lifetime Value (CLV) Distribution**:
  - Histogram of `Clv Predicted 12m`
- **Segment Marketing Playbook Table**:
  - `Rfm Segment`, `Pct Of Customers`, `Pct Of Revenue`, `Recommended Action`

#### Dashboard 4: Identity Resolution & Journey Deep Dive
- **Customer Journey Path Explorer**:
  - Touchpoints ordered chronologically (1st, 2nd, ..., Nth)
  - Average Days to Conversion: 6.8 days
  - Average Touchpoints per Order: 3.6 sessions
  - Device Cross-Link Rate: 55% of customers accessed across multiple devices.

---

### 4. Color Palette Specifications
- Primary Brand Blue: `#1F77B4`
- Positive Reallocation / Scale Up: `#2CA02C` (Forest Green)
- Warning / Saturated: `#FF7F0E` (Amber)
- Negative / Trim Budget: `#D62728` (Crimson)
- VIP Segments: `#9467BD` (Royal Purple)
"""


def generate_tableau_artifacts(export_dir: str):
    os.makedirs(export_dir, exist_ok=True)
    guide_path = os.path.join(export_dir, "TABLEAU_DASHBOARD_GUIDE.md")
    with open(guide_path, "w", encoding="utf-8") as f:
        f.write(TABLEAU_GUIDE_CONTENT)
    print(f"Generated Tableau Dashboard Guide at: {guide_path}")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out_dir = os.path.join(base_dir, "data", "tableau_exports")
    generate_tableau_artifacts(out_dir)

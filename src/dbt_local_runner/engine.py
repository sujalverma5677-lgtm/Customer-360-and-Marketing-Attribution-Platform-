"""
Local dbt & Data Warehouse Execution Engine
Orchestrates raw ingestion, identity graph resolution, staging, intermediate,
Customer 360 marts, attribution modeling, and automated data quality test assertions.
"""

import os
import sys
from datetime import datetime
import pandas as pd
import numpy as np

# Add src to python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, os.path.join(project_root, "src"))

from identity_resolution.graph_resolver import IdentityResolver
from analytics.rfm_clv_engine import RFMCLVEngine
from analytics.attribution_engine import AttributionEngine
from analytics.budget_optimizer import BudgetOptimizer


class LocalWarehouseRunner:
    def __init__(self, root_dir: str):
        self.root_dir = root_dir
        self.raw_dir = os.path.join(root_dir, "data", "raw")
        self.processed_dir = os.path.join(root_dir, "data", "processed")
        self.warehouse_dir = os.path.join(root_dir, "data", "warehouse")
        self.tableau_dir = os.path.join(root_dir, "data", "tableau_exports")

        for d in [self.processed_dir, self.warehouse_dir, self.tableau_dir]:
            os.makedirs(d, exist_ok=True)

    def run_pipeline(self) -> dict:
        print("=" * 80)
        print("STARTING CUSTOMER 360 & MARKETING ATTRIBUTION PIPELINE EXECUTION")
        print("=" * 80)

        # 1. LOAD RAW DATA
        print("\n[Step 1/7] Loading Raw Datasets...")
        df_raw_ga4 = pd.read_csv(os.path.join(self.raw_dir, "raw_ga4_events.csv"))
        df_raw_crm_cust = pd.read_csv(os.path.join(self.raw_dir, "raw_crm_customers.csv"))
        df_raw_crm_ord = pd.read_csv(os.path.join(self.raw_dir, "raw_crm_orders.csv"))
        df_raw_ad_spend = pd.read_csv(os.path.join(self.raw_dir, "raw_ad_spend.csv"))

        # 2. IDENTITY RESOLUTION GRAPH
        print("\n[Step 2/7] Executing Graph Identity Resolution...")
        resolver = IdentityResolver()
        df_identity_mapping = resolver.build_graph_from_dataframes(df_raw_ga4, df_raw_crm_cust)
        df_identity_mapping.to_csv(os.path.join(self.processed_dir, "int_identity_mapping.csv"), index=False)

        # 3. INTERMEDIATE: WEB SESSIONS
        print("\n[Step 3/7] Building Staging & Intermediate Web Sessions...")
        df_raw_ga4["user_pseudo_id"] = df_raw_ga4["user_pseudo_id"].astype(str)
        df_identity_mapping["identifier_value"] = df_identity_mapping["identifier_value"].astype(str)

        # Map user_pseudo_id to canonical_customer_id
        cookie_to_canonical = (
            df_identity_mapping[df_identity_mapping["identifier_type"] == "user_pseudo_id"]
            .set_index("identifier_value")["canonical_customer_id"]
            .to_dict()
        )

        df_raw_ga4["canonical_customer_id"] = (
            df_raw_ga4["user_id"].fillna(
                df_raw_ga4["user_pseudo_id"].map(cookie_to_canonical)
            ).fillna("ANON_" + df_raw_ga4["user_pseudo_id"])
        )

        # Session aggregation
        df_raw_ga4["event_timestamp_dt"] = pd.to_datetime(df_raw_ga4["event_timestamp"], unit="us")
        df_raw_ga4["event_value_usd"] = df_raw_ga4["event_value_usd"].fillna(0.0)

        # Channel mapping logic
        def assign_channel(row):
            src = str(row.get("source", "")).lower()
            med = str(row.get("medium", "")).lower()
            camp = str(row.get("campaign", "")).lower()
            if src == "(direct)" and (med in ["(none)", "(not set)", ""]):
                return "Direct"
            elif med == "organic" or ("google" in src and med == "organic"):
                return "Organic Search"
            elif med in ["cpc", "ppc", "paidsearch"] and "brand" in camp and "nonbrand" not in camp:
                return "Paid Search - Brand"
            elif med in ["cpc", "ppc", "paidsearch"]:
                return "Paid Search - Generic"
            elif med in ["paid_social", "paidsocial"] and "tiktok" in src:
                return "Paid Video - TikTok Ads"
            elif med in ["paid_social", "paidsocial"] and "retargeting" in camp:
                return "Paid Social - Meta Retargeting"
            elif med in ["paid_social", "paidsocial"] and "facebook" in src:
                return "Paid Social - Meta Prospecting"
            elif med == "email" or src in ["klaviyo", "mailchimp"]:
                return "Email Marketing"
            else:
                return "Other / Referral"

        df_raw_ga4["channel_grouping"] = df_raw_ga4.apply(assign_channel, axis=1)

        # Group by session_id
        sessions_agg = df_raw_ga4.groupby("ga_session_id").agg(
            canonical_customer_id=("canonical_customer_id", "first"),
            user_pseudo_id=("user_pseudo_id", "first"),
            session_start_timestamp=("event_timestamp_dt", "min"),
            session_end_timestamp=("event_timestamp_dt", "max"),
            channel_grouping=("channel_grouping", "first"),
            utm_source=("source", "first"),
            utm_medium=("medium", "first"),
            utm_campaign=("campaign", "first"),
            landing_page=("page_location", "first"),
            device_category=("device_category", "first"),
            operating_system=("operating_system", "first"),
            country=("country", "first"),
            city=("city", "first"),
            event_count=("event_name", "count"),
            session_revenue_usd=("event_value_usd", "sum")
        ).reset_index()

        sessions_agg.rename(columns={"ga_session_id": "session_id"}, inplace=True)
        sessions_agg["session_duration_seconds"] = (
            (sessions_agg["session_end_timestamp"] - sessions_agg["session_start_timestamp"]).dt.total_seconds()
        ).astype(int)
        sessions_agg.to_csv(os.path.join(self.processed_dir, "int_web_sessions.csv"), index=False)

        # 4. CUSTOMER 360 & RFM MARTS
        print("\n[Step 4/7] Generating Customer 360 & RFM Segmentation Marts...")
        rfm_engine = RFMCLVEngine()
        df_dim_customers_360, df_fct_rfm_segments = rfm_engine.calculate_rfm_clv(
            df_customers=df_raw_crm_cust,
            df_orders=df_raw_crm_ord,
            df_sessions=sessions_agg
        )
        df_dim_customers_360.to_csv(os.path.join(self.warehouse_dir, "dim_customers_360.csv"), index=False)
        df_fct_rfm_segments.to_csv(os.path.join(self.warehouse_dir, "fct_customer_rfm_segments.csv"), index=False)

        # 5. MULTI-TOUCH ATTRIBUTION MART
        print("\n[Step 5/7] Executing Multi-Touch Attribution Engine (5 Models)...")
        attribution_engine = AttributionEngine()
        df_fct_attribution = attribution_engine.build_touchpoints(
            df_orders=df_raw_crm_ord,
            df_sessions=sessions_agg
        )
        df_fct_attribution.to_csv(os.path.join(self.warehouse_dir, "fct_attribution_multi_touch.csv"), index=False)

        # 6. CAMPAIGN PERFORMANCE & ROI MART
        print("\n[Step 6/7] Computing Channel ROAS, CPA, and ROI Mart...")
        df_agg_campaign_perf = attribution_engine.compute_campaign_performance(
            df_touchpoints=df_fct_attribution,
            df_ad_spend=df_raw_ad_spend
        )
        df_agg_campaign_perf.to_csv(os.path.join(self.warehouse_dir, "agg_campaign_performance_roi.csv"), index=False)

        # 7. BUDGET OPTIMIZER & REALLOCATION
        print("\n[Step 7/7] Computing Budget Optimization Reallocations...")
        optimizer = BudgetOptimizer()
        df_budget_realloc = optimizer.optimize_budget(df_agg_campaign_perf)
        df_budget_realloc.to_csv(os.path.join(self.warehouse_dir, "agg_budget_reallocation_recommendations.csv"), index=False)

        # EXPORT TO TABLEAU
        print("\nExporting cleaned, Tableau-ready datasets...")
        df_dim_customers_360.to_csv(os.path.join(self.tableau_dir, "tableau_dim_customers_360.csv"), index=False)
        df_fct_rfm_segments.to_csv(os.path.join(self.tableau_dir, "tableau_fct_customer_rfm_segments.csv"), index=False)
        df_fct_attribution.to_csv(os.path.join(self.tableau_dir, "tableau_fct_attribution_multi_touch.csv"), index=False)
        df_agg_campaign_perf.to_csv(os.path.join(self.tableau_dir, "tableau_agg_campaign_performance_roi.csv"), index=False)
        df_budget_realloc.to_csv(os.path.join(self.tableau_dir, "tableau_agg_budget_reallocation.csv"), index=False)

        # DATA QUALITY TESTS ASSERTION
        print("\n" + "=" * 80)
        print("RUNNING AUTOMATED DATA QUALITY & CONSISTENCY ASSERTIONS")
        print("=" * 80)
        test_results = self.run_data_tests(
            df_dim_customers_360,
            df_fct_attribution,
            df_agg_campaign_perf,
            df_raw_crm_ord
        )

        return {
            "dim_customers_360": len(df_dim_customers_360),
            "fct_rfm_segments": len(df_fct_rfm_segments),
            "fct_attribution_multi_touch": len(df_fct_attribution),
            "agg_campaign_performance_roi": len(df_agg_campaign_perf),
            "budget_reallocation": len(df_budget_realloc),
            "test_results": test_results
        }

    def run_data_tests(self, df_cust, df_attr, df_perf, df_orders) -> dict:
        tests = {}

        # Test 1: Primary Key Uniqueness on dim_customers_360
        t1 = df_cust["canonical_customer_id"].is_unique
        tests["pk_uniqueness_dim_customers_360"] = "PASSED" if t1 else "FAILED"
        print(f"Test 1 [PK Uniqueness - dim_customers_360]: {tests['pk_uniqueness_dim_customers_360']}")

        # Test 2: RFM Scores strictly in [1, 5]
        r_valid = df_cust["r_score"].between(1, 5).all()
        f_valid = df_cust["f_score"].between(1, 5).all()
        m_valid = df_cust["m_score"].between(1, 5).all()
        t2 = r_valid and f_valid and m_valid
        tests["rfm_scores_bounded_1_to_5"] = "PASSED" if t2 else "FAILED"
        print(f"Test 2 [RFM Scores bounded 1-5]: {tests['rfm_scores_bounded_1_to_5']}")

        # Test 3: Conservation of Revenue (Sum of attributed revenue == Total order revenue)
        total_order_revenue = df_orders["total_revenue"].sum()
        sum_linear = df_attr["revenue_linear"].sum()
        sum_timedecay = df_attr["revenue_time_decay"].sum()
        sum_first = df_attr["revenue_first_touch"].sum()
        sum_last = df_attr["revenue_last_touch"].sum()

        diff_linear = abs(total_order_revenue - sum_linear)
        diff_td = abs(total_order_revenue - sum_timedecay)
        # Tolerance allows rounding cents across thousands of orders
        t3 = diff_linear < 20.0 and diff_td < 20.0
        tests["revenue_conservation_rule"] = "PASSED" if t3 else "FAILED"
        print(f"Test 3 [Revenue Conservation]: {tests['revenue_conservation_rule']} "
              f"(Total Order Rev: ${total_order_revenue:,.2f} | Linear: ${sum_linear:,.2f} | Time-Decay: ${sum_timedecay:,.2f})")

        # Test 4: No orphan conversion touchpoints
        t4 = df_attr["order_id"].notna().all() and df_attr["customer_id"].notna().all()
        tests["referential_integrity_touchpoints"] = "PASSED" if t4 else "FAILED"
        print(f"Test 4 [Referential Integrity]: {tests['referential_integrity_touchpoints']}")

        # Test 5: ROAS non-negative
        t5 = (df_perf["roas_time_decay"].dropna() >= 0).all()
        tests["roas_validity"] = "PASSED" if t5 else "FAILED"
        print(f"Test 5 [ROAS Non-Negative]: {tests['roas_validity']}")

        all_passed = all(status == "PASSED" for status in tests.values())
        print(f"\nFinal Test Summary: {'ALL TESTS PASSED (100%)' if all_passed else 'SOME TESTS FAILED'}")
        return tests


if __name__ == "__main__":
    runner = LocalWarehouseRunner(project_root)
    results = runner.run_pipeline()

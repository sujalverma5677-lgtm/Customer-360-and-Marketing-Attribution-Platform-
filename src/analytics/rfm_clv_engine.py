"""
RFM Scoring & Customer Lifetime Value (CLV) Engine
Computes Recency, Frequency, Monetary quintiles, RFM segments, and 12-month predictive CLV.
"""

from typing import Tuple
from datetime import datetime
import pandas as pd
import numpy as np


class RFMCLVEngine:
    def __init__(self, reference_date: str = "2026-10-28"):
        self.reference_date = pd.to_datetime(reference_date)

    def calculate_rfm_clv(
        self,
        df_customers: pd.DataFrame,
        df_orders: pd.DataFrame,
        df_sessions: pd.DataFrame
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Computes dim_customers_360 and fct_customer_rfm_segments.
        """
        print("Computing RFM metrics and Predictive CLV...")
        orders = df_orders.copy()
        orders["order_timestamp"] = pd.to_datetime(orders["order_timestamp"])
        orders["order_date"] = pd.to_datetime(orders["order_date"])

        # Aggregate orders per customer
        agg_orders = orders.groupby("customer_id").agg(
            first_order_timestamp=("order_timestamp", "min"),
            last_order_timestamp=("order_timestamp", "max"),
            first_order_date=("order_date", "min"),
            last_order_date=("order_date", "max"),
            lifetime_orders_count=("order_id", "count"),
            lifetime_revenue_usd=("total_revenue", "sum"),
            avg_order_value_usd=("total_revenue", "mean"),
            lifetime_discount_usd=("discount_amount", "sum")
        ).reset_index()

        agg_orders["lifetime_revenue_usd"] = agg_orders["lifetime_revenue_usd"].round(2)
        agg_orders["avg_order_value_usd"] = agg_orders["avg_order_value_usd"].round(2)
        agg_orders["lifetime_discount_usd"] = agg_orders["lifetime_discount_usd"].round(2)

        # Aggregate sessions per customer
        sess = df_sessions.copy()
        sess["session_start_timestamp"] = pd.to_datetime(sess["session_start_timestamp"])
        sess_sorted = sess.sort_values(by="session_start_timestamp")

        first_ch = sess_sorted.groupby("canonical_customer_id").first()["channel_grouping"].to_dict()
        last_ch = sess_sorted.groupby("canonical_customer_id").last()["channel_grouping"].to_dict()
        sess_count = sess.groupby("canonical_customer_id")["session_id"].count().to_dict()
        first_seen = sess.groupby("canonical_customer_id")["session_start_timestamp"].min().to_dict()
        last_seen = sess.groupby("canonical_customer_id")["session_start_timestamp"].max().to_dict()

        # Merge with CRM customers
        dim = df_customers.copy()
        dim = dim.merge(agg_orders, on="customer_id", how="left")

        dim["first_seen_timestamp"] = dim["customer_id"].map(first_seen)
        dim["last_seen_timestamp"] = dim["customer_id"].map(last_seen)
        dim["lifetime_sessions_count"] = dim["customer_id"].map(sess_count).fillna(0).astype(int)
        dim["first_acquisition_channel"] = dim["customer_id"].map(first_ch).fillna("Direct")
        dim["last_active_channel"] = dim["customer_id"].map(last_ch).fillna("Direct")

        dim["lifetime_orders_count"] = dim["lifetime_orders_count"].fillna(0).astype(int)
        dim["lifetime_revenue_usd"] = dim["lifetime_revenue_usd"].fillna(0.0)
        dim["avg_order_value_usd"] = dim["avg_order_value_usd"].fillna(0.0)
        dim["frequency_orders"] = dim["lifetime_orders_count"]
        dim["monetary_usd"] = dim["lifetime_revenue_usd"]

        # Recency calculation
        fallback_date = pd.to_datetime("2026-08-01")
        dim["last_order_dt"] = pd.to_datetime(dim["last_order_date"]).fillna(fallback_date)
        dim["recency_days"] = (self.reference_date - dim["last_order_dt"]).dt.days.clip(lower=0)

        # Quintile Scoring (1 to 5)
        # R score: Lower recency_days = Higher score (5 is best)
        # We use rank with method='first' for clean quantile binning
        dim["r_score"] = 6 - pd.qcut(dim["recency_days"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
        dim["f_score"] = pd.qcut(dim["frequency_orders"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
        dim["m_score"] = pd.qcut(dim["monetary_usd"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)

        dim["rfm_score_combined"] = dim["r_score"].astype(str) + dim["f_score"].astype(str) + dim["m_score"].astype(str)
        dim["rfm_score_average"] = ((dim["r_score"] + dim["f_score"] + dim["m_score"]) / 3.0).round(2)

        # Segment Assignment
        def assign_segment(row):
            r = row["r_score"]
            f = row["f_score"]
            m = row["monetary_usd"]
            if r >= 4 and f >= 4:
                return "Champions"
            elif r >= 3 and f >= 3:
                return "Loyal Customers"
            elif r >= 4 and f <= 2:
                return "Recent Customers"
            elif r >= 3 and f <= 2:
                return "Potential Loyalists"
            elif r == 3 and f == 3:
                return "Promising"
            elif r == 2 and f >= 3:
                return "Customers Needing Attention"
            elif r == 2 and f <= 2:
                return "About to Sleep"
            elif r == 1 and f >= 4:
                return "Can't Lose Them"
            elif r == 1 and f >= 2:
                return "At Risk"
            elif r == 1 and f == 1 and m > 200:
                return "Hibernating"
            else:
                return "Lost"

        dim["rfm_segment"] = dim.apply(assign_segment, axis=1)

        # 12-Month Predictive CLV
        retention_weights = {5: 0.90, 4: 0.80, 3: 0.65, 2: 0.40, 1: 0.15}
        dim["retention_prob"] = dim["r_score"].map(retention_weights)
        
        # CLV = Historical Monetary + (AOV * Projected Orders (Freq * 1.5) * Retention Prob)
        dim["clv_predicted_12m"] = (
            dim["monetary_usd"] + (dim["avg_order_value_usd"] * (dim["frequency_orders"] * 1.5) * dim["retention_prob"])
        ).round(2)

        dim.rename(columns={"customer_id": "canonical_customer_id"}, inplace=True)

        cols_dim = [
            "canonical_customer_id", "email", "first_name", "last_name", "phone",
            "country", "region", "city", "signup_timestamp", "first_seen_timestamp",
            "last_seen_timestamp", "lifetime_sessions_count", "first_acquisition_channel",
            "last_active_channel", "lifetime_orders_count", "lifetime_revenue_usd",
            "avg_order_value_usd", "recency_days", "frequency_orders", "monetary_usd",
            "r_score", "f_score", "m_score", "rfm_score_combined", "rfm_score_average",
            "rfm_segment", "clv_predicted_12m"
        ]
        df_dim_customers_360 = dim[cols_dim]

        # Aggregate Segments Table
        action_map = {
            "Champions": "VIP Rewards, Early Access, Ambassador Referral Program",
            "Loyal Customers": "Upsell Premium Tiers, Loyalty Points, Product Feedback",
            "Potential Loyalists": "Cross-sell complementary gear, recommend bundles",
            "Recent Customers": "Onboarding email sequence, post-purchase delight, brand storytelling",
            "Promising": "Time-limited discounts, personalized recommendations",
            "Customers Needing Attention": "Reactivation offer, customer support check-in",
            "About to Sleep": "Aggressive win-back discount, surveys to diagnose friction",
            "At Risk": "High-touch outreach, personalized 20% discount code, re-engagement ads",
            "Can't Lose Them": "White-glove executive reachout, win them back before churn is permanent",
            "Hibernating": "Standard automated low-cost email reactivation campaign",
            "Lost": "Sunset email list, suppress from paid ad retargeting to save budget"
        }

        seg_agg = df_dim_customers_360.groupby("rfm_segment").agg(
            customer_count=("canonical_customer_id", "count"),
            total_segment_revenue_usd=("lifetime_revenue_usd", "sum"),
            avg_recency_days=("recency_days", "mean"),
            avg_frequency_orders=("frequency_orders", "mean"),
            avg_monetary_spend_usd=("monetary_usd", "mean"),
            avg_clv_predicted_12m=("clv_predicted_12m", "mean")
        ).reset_index()

        total_custs = len(df_dim_customers_360)
        total_rev = df_dim_customers_360["lifetime_revenue_usd"].sum()

        seg_agg["pct_of_customers"] = (seg_agg["customer_count"] * 100.0 / total_custs).round(2)
        seg_agg["pct_of_revenue"] = (seg_agg["total_segment_revenue_usd"] * 100.0 / total_rev).round(2)
        seg_agg["total_segment_revenue_usd"] = seg_agg["total_segment_revenue_usd"].round(2)
        seg_agg["avg_recency_days"] = seg_agg["avg_recency_days"].round(1)
        seg_agg["avg_frequency_orders"] = seg_agg["avg_frequency_orders"].round(2)
        seg_agg["avg_monetary_spend_usd"] = seg_agg["avg_monetary_spend_usd"].round(2)
        seg_agg["avg_clv_predicted_12m"] = seg_agg["avg_clv_predicted_12m"].round(2)
        seg_agg["recommended_action"] = seg_agg["rfm_segment"].map(action_map)

        df_fct_rfm_segments = seg_agg.sort_values(by="total_segment_revenue_usd", ascending=False).reset_index(drop=True)

        return df_dim_customers_360, df_fct_rfm_segments




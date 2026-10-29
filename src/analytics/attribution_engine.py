"""
Multi-Touch Marketing Attribution Engine
Implements and evaluates:
1. First-Touch Attribution (FTA)
2. Last-Touch Attribution (LTA)
3. Linear Attribution
4. Time-Decay Attribution (7-day exponential half-life)
5. Position-Based Attribution (U-Shaped 40/20/40)

Computes Channel ROI, ROAS, and Cost Per Acquisition (CPA / CAC).
"""

import pandas as pd
import numpy as np


class AttributionEngine:
    def __init__(self, half_life_days: float = 7.0, lookback_window_days: int = 30):
        self.half_life_days = half_life_days
        self.lookback_window_days = lookback_window_days

    def build_touchpoints(
        self,
        df_orders: pd.DataFrame,
        df_sessions: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Joins orders with customer web sessions within the 30-day lookback window
        and computes attribution weights for all 5 models.
        """
        print("Constructing conversion customer touchpoint journeys...")
        orders = df_orders.copy()
        orders["order_timestamp"] = pd.to_datetime(orders["order_timestamp"])
        orders["total_revenue"] = orders["total_revenue"].astype(float)

        sessions = df_sessions.copy()
        sessions["session_start_timestamp"] = pd.to_datetime(sessions["session_start_timestamp"])

        # Merge orders with sessions on canonical_customer_id
        merged = orders.merge(
            sessions,
            left_on="customer_id",
            right_on="canonical_customer_id",
            how="inner"
        )

        # Filter to sessions strictly before or at order timestamp, within lookback window
        merged = merged[
            (merged["session_start_timestamp"] <= merged["order_timestamp"]) &
            (merged["session_start_timestamp"] >= (merged["order_timestamp"] - pd.Timedelta(days=self.lookback_window_days)))
        ].copy()

        # Days before order
        merged["days_before_order"] = (
            (merged["order_timestamp"] - merged["session_start_timestamp"]).dt.total_seconds() / 86400.0
        ).clip(lower=0.0)

        # Sort and rank touchpoints per order
        merged = merged.sort_values(by=["order_id", "session_start_timestamp"]).reset_index(drop=True)
        merged["touchpoint_order_asc"] = merged.groupby("order_id").cumcount() + 1
        merged["touchpoint_order_desc"] = merged.groupby("order_id").cumcount(ascending=False) + 1
        merged["total_journey_touchpoints"] = merged.groupby("order_id")["session_id"].transform("count")

        # 1. First-Touch Weight
        merged["weight_first_touch"] = np.where(merged["touchpoint_order_asc"] == 1, 1.0, 0.0)

        # 2. Last-Touch Weight
        merged["weight_last_touch"] = np.where(merged["touchpoint_order_desc"] == 1, 1.0, 0.0)

        # 3. Linear Weight
        merged["weight_linear"] = 1.0 / merged["total_journey_touchpoints"]

        # 4. Time-Decay Weight (exponential half-life)
        # raw_weight = 2 ^ (-days_before_order / half_life)
        merged["raw_decay"] = np.power(2.0, -1.0 * (merged["days_before_order"] / self.half_life_days))
        sum_decay = merged.groupby("order_id")["raw_decay"].transform("sum")
        merged["weight_time_decay"] = merged["raw_decay"] / sum_decay

        # 5. Position-Based (U-Shaped 40/20/40)
        def position_weight(row):
            n = row["total_journey_touchpoints"]
            asc = row["touchpoint_order_asc"]
            desc = row["touchpoint_order_desc"]
            if n == 1:
                return 1.0
            elif n == 2:
                return 0.5
            elif asc == 1:
                return 0.40
            elif desc == 1:
                return 0.40
            else:
                return 0.20 / (n - 2)

        merged["weight_position_based"] = merged.apply(position_weight, axis=1)

        # Surrogate touchpoint_id
        merged["touchpoint_id"] = merged["order_id"] + "_" + merged["session_id"]

        # Attributed Revenues
        rev = merged["total_revenue"]
        merged["revenue_first_touch"] = (rev * merged["weight_first_touch"]).round(2)
        merged["revenue_last_touch"] = (rev * merged["weight_last_touch"]).round(2)
        merged["revenue_linear"] = (rev * merged["weight_linear"]).round(2)
        merged["revenue_time_decay"] = (rev * merged["weight_time_decay"]).round(2)
        merged["revenue_position_based"] = (rev * merged["weight_position_based"]).round(2)

        # Attributed Conversions
        merged["conversions_first_touch"] = merged["weight_first_touch"].round(4)
        merged["conversions_last_touch"] = merged["weight_last_touch"].round(4)
        merged["conversions_linear"] = merged["weight_linear"].round(4)
        merged["conversions_time_decay"] = merged["weight_time_decay"].round(4)
        merged["conversions_position_based"] = merged["weight_position_based"].round(4)

        cols = [
            "touchpoint_id", "order_id", "customer_id", "session_id",
            "session_start_timestamp", "order_timestamp", "channel_grouping",
            "utm_source", "utm_medium", "utm_campaign", "device_category",
            "days_before_order", "touchpoint_order_asc", "touchpoint_order_desc",
            "total_journey_touchpoints", "total_revenue",
            "weight_first_touch", "weight_last_touch", "weight_linear",
            "weight_time_decay", "weight_position_based",
            "revenue_first_touch", "revenue_last_touch", "revenue_linear",
            "revenue_time_decay", "revenue_position_based",
            "conversions_first_touch", "conversions_last_touch",
            "conversions_linear", "conversions_time_decay", "conversions_position_based"
        ]

        df_touchpoints = merged[cols].reset_index(drop=True)
        print(f"Generated {len(df_touchpoints):,} attributed touchpoints across {merged['order_id'].nunique():,} orders.")
        return df_touchpoints

    def compute_campaign_performance(
        self,
        df_touchpoints: pd.DataFrame,
        df_ad_spend: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Combines marketing spend with attributed revenue & conversions to compute
        ROAS, CPA, and Budget Recommendations.
        """
        print("Computing Campaign Performance, ROAS, and CPA across attribution models...")
        # Aggregate Ad Spend
        spend_agg = df_ad_spend.groupby("channel_name").agg(
            total_spend_usd=("daily_spend", "sum"),
            total_clicks=("clicks", "sum"),
            total_impressions=("impressions", "sum"),
            avg_cpc=("cpc", "mean")
        ).reset_index()

        spend_agg["blended_ctr_pct"] = (
            (spend_agg["total_clicks"] * 100.0) / spend_agg["total_impressions"].replace(0, np.nan)
        ).round(2)
        spend_agg["total_spend_usd"] = spend_agg["total_spend_usd"].round(2)
        spend_agg["avg_cpc"] = spend_agg["avg_cpc"].round(2)

        # Aggregate Attributed Metrics by Channel
        attr_agg = df_touchpoints.groupby("channel_grouping").agg(
            revenue_first_touch=("revenue_first_touch", "sum"),
            revenue_last_touch=("revenue_last_touch", "sum"),
            revenue_linear=("revenue_linear", "sum"),
            revenue_time_decay=("revenue_time_decay", "sum"),
            revenue_position_based=("revenue_position_based", "sum"),
            conversions_first_touch=("conversions_first_touch", "sum"),
            conversions_last_touch=("conversions_last_touch", "sum"),
            conversions_linear=("conversions_linear", "sum"),
            conversions_time_decay=("conversions_time_decay", "sum"),
            conversions_position_based=("conversions_position_based", "sum")
        ).reset_index()

        # Merge spend and attribution
        perf = spend_agg.merge(
            attr_agg,
            left_on="channel_name",
            right_on="channel_grouping",
            how="outer"
        )
        perf["channel_name"] = perf["channel_name"].fillna(perf["channel_grouping"])
        perf.drop(columns=["channel_grouping"], inplace=True)

        for col in [
            "total_spend_usd", "total_clicks", "total_impressions", "avg_cpc", "blended_ctr_pct",
            "revenue_first_touch", "revenue_last_touch", "revenue_linear", "revenue_time_decay", "revenue_position_based",
            "conversions_first_touch", "conversions_last_touch", "conversions_linear", "conversions_time_decay", "conversions_position_based"
        ]:
            perf[col] = perf[col].fillna(0.0).round(2)

        # ROAS Calculations
        for model in ["first_touch", "last_touch", "linear", "time_decay", "position_based"]:
            perf[f"roas_{model}"] = np.where(
                perf["total_spend_usd"] > 0,
                (perf[f"revenue_{model}"] / perf["total_spend_usd"]).round(2),
                np.nan
            )

        # CPA Calculations
        for model in ["first_touch", "last_touch", "linear", "time_decay"]:
            perf[f"cpa_{model}"] = np.where(
                perf[f"conversions_{model}"] > 0,
                (perf["total_spend_usd"] / perf[f"conversions_{model}"]).round(2),
                np.nan
            )

        # Net ROI %
        perf["net_roi_pct_time_decay"] = np.where(
            perf["total_spend_usd"] > 0,
            (((perf["revenue_time_decay"] - perf["total_spend_usd"]) / perf["total_spend_usd"]) * 100.0).round(1),
            np.nan
        )

        # Executive Recommendation Logic
        def recommend_action(row):
            spend = row["total_spend_usd"]
            roas_ft = row["roas_first_touch"]
            roas_lt = row["roas_last_touch"]
            roas_td = row["roas_time_decay"]

            if spend == 0:
                return "Earned / Zero-Spend Engine (Maintain SEO/Direct flows)"
            # Discovery / Top of Funnel Driver: High First Touch ROAS, Low Last Touch ROAS
            if roas_ft >= 3.0 and roas_lt < 2.0:
                return "SCALE BUDGET (+35%): Key Discovery Driver. Last-Touch severely undervalues it!"
            if roas_td >= 4.0:
                return "SCALE AGGRESSIVELY (+40%): Highly profitable channel across touchpoints."
            elif roas_td >= 2.0:
                return "MAINTAIN / OPTIMIZE (+10%): Steady profitable performance."
            else:
                return "TRIM BUDGET (-30%): Sub-par ROAS. Shift capital to discovery channels."

        perf["executive_budget_recommendation"] = perf.apply(recommend_action, axis=1)
        perf = perf.sort_values(by="total_spend_usd", ascending=False).reset_index(drop=True)
        return perf

"""
Unit Tests for Multi-Touch Attribution Engine
Validates Mathematical Integrity: Revenue Conservation, Weight Normalization, and Monotonicity.
"""

import os
import sys
import unittest
import pandas as pd
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analytics.attribution_engine import AttributionEngine


class TestAttributionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AttributionEngine(half_life_days=7.0, lookback_window_days=30)

        # Mock Orders
        self.mock_orders = pd.DataFrame([
            {
                "order_id": "ORD-1",
                "customer_id": "CUST-A",
                "order_timestamp": "2026-10-10 12:00:00",
                "total_revenue": 300.0
            },
            {
                "order_id": "ORD-2",
                "customer_id": "CUST-B",
                "order_timestamp": "2026-10-12 15:00:00",
                "total_revenue": 100.0
            }
        ])

        # Mock Sessions:
        # CUST-A has 3 touchpoints (Day -10, Day -3, Day 0)
        # CUST-B has 1 touchpoint (Day 0)
        self.mock_sessions = pd.DataFrame([
            {
                "session_id": "SESS-1",
                "canonical_customer_id": "CUST-A",
                "session_start_timestamp": "2026-09-30 12:00:00", # 10 days before
                "channel_grouping": "Paid Video - TikTok Ads",
                "utm_source": "tiktok",
                "utm_medium": "paid_social",
                "utm_campaign": "spring_viral",
                "device_category": "mobile"
            },
            {
                "session_id": "SESS-2",
                "canonical_customer_id": "CUST-A",
                "session_start_timestamp": "2026-10-07 12:00:00", # 3 days before
                "channel_grouping": "Paid Social - Meta Retargeting",
                "utm_source": "facebook",
                "utm_medium": "paid_social",
                "utm_campaign": "cart_retargeting",
                "device_category": "desktop"
            },
            {
                "session_id": "SESS-3",
                "canonical_customer_id": "CUST-A",
                "session_start_timestamp": "2026-10-10 11:30:00", # 0.5 hours before
                "channel_grouping": "Email Marketing",
                "utm_source": "klaviyo",
                "utm_medium": "email",
                "utm_campaign": "cart_reminder",
                "device_category": "mobile"
            },
            {
                "session_id": "SESS-4",
                "canonical_customer_id": "CUST-B",
                "session_start_timestamp": "2026-10-12 14:00:00",
                "channel_grouping": "Paid Search - Brand",
                "utm_source": "google",
                "utm_medium": "cpc",
                "utm_campaign": "brand_exact",
                "device_category": "desktop"
            }
        ])

    def test_weight_normalization_sums_to_one(self):
        df_tp = self.engine.build_touchpoints(self.mock_orders, self.mock_sessions)
        
        for ord_id in ["ORD-1", "ORD-2"]:
            ord_tp = df_tp[df_tp["order_id"] == ord_id]
            self.assertAlmostEqual(ord_tp["weight_first_touch"].sum(), 1.0, places=4)
            self.assertAlmostEqual(ord_tp["weight_last_touch"].sum(), 1.0, places=4)
            self.assertAlmostEqual(ord_tp["weight_linear"].sum(), 1.0, places=4)
            self.assertAlmostEqual(ord_tp["weight_time_decay"].sum(), 1.0, places=4)
            self.assertAlmostEqual(ord_tp["weight_position_based"].sum(), 1.0, places=4)

    def test_revenue_conservation(self):
        df_tp = self.engine.build_touchpoints(self.mock_orders, self.mock_sessions)
        
        ord1_tp = df_tp[df_tp["order_id"] == "ORD-1"]
        self.assertAlmostEqual(ord1_tp["revenue_linear"].sum(), 300.0, places=2)
        self.assertAlmostEqual(ord1_tp["revenue_time_decay"].sum(), 300.0, places=2)
        self.assertAlmostEqual(ord1_tp["revenue_position_based"].sum(), 300.0, places=2)

    def test_time_decay_monotonicity(self):
        df_tp = self.engine.build_touchpoints(self.mock_orders, self.mock_sessions)
        ord1_tp = df_tp[df_tp["order_id"] == "ORD-1"].sort_values(by="session_start_timestamp")
        
        # Touchpoint 3 (most recent) must have higher decay weight than Touchpoint 2, which is higher than Touchpoint 1
        w1 = ord1_tp.iloc[0]["weight_time_decay"]
        w2 = ord1_tp.iloc[1]["weight_time_decay"]
        w3 = ord1_tp.iloc[2]["weight_time_decay"]
        self.assertGreater(w3, w2)
        self.assertGreater(w2, w1)

    def test_single_touchpoint_order(self):
        df_tp = self.engine.build_touchpoints(self.mock_orders, self.mock_sessions)
        ord2_tp = df_tp[df_tp["order_id"] == "ORD-2"]
        self.assertEqual(len(ord2_tp), 1)
        self.assertEqual(ord2_tp.iloc[0]["weight_first_touch"], 1.0)
        self.assertEqual(ord2_tp.iloc[0]["weight_last_touch"], 1.0)
        self.assertEqual(ord2_tp.iloc[0]["weight_linear"], 1.0)
        self.assertEqual(ord2_tp.iloc[0]["weight_time_decay"], 1.0)
        self.assertEqual(ord2_tp.iloc[0]["revenue_time_decay"], 100.0)


if __name__ == "__main__":
    unittest.main()

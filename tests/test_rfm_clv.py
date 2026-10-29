"""
Unit Tests for RFM Scoring and Predictive CLV Engine
Validates Quintile Scoring, Segment Assignment, and 12-Month Predictive CLV logic.
"""

import os
import sys
import unittest
import pandas as pd

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.analytics.rfm_clv_engine import RFMCLVEngine


class TestRFMCLVEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RFMCLVEngine(reference_date="2026-10-28")

        self.mock_customers = pd.DataFrame([
            {"customer_id": "CUST-1", "email": "champ@example.com", "first_name": "Alice", "last_name": "VIP", "phone": "555-01", "country": "US", "region": "NY", "city": "NYC", "signup_timestamp": "2026-08-01 00:00:00"},
            {"customer_id": "CUST-2", "email": "dormant@example.com", "first_name": "Bob", "last_name": "Sleep", "phone": "555-02", "country": "US", "region": "CA", "city": "SF", "signup_timestamp": "2026-08-01 00:00:00"},
            {"customer_id": "CUST-3", "email": "recent@example.com", "first_name": "Charlie", "last_name": "New", "phone": "555-03", "country": "US", "region": "TX", "city": "Austin", "signup_timestamp": "2026-08-01 00:00:00"},
            {"customer_id": "CUST-4", "email": "loyal@example.com", "first_name": "Diana", "last_name": "Mid", "phone": "555-04", "country": "US", "region": "IL", "city": "Chicago", "signup_timestamp": "2026-08-01 00:00:00"},
            {"customer_id": "CUST-5", "email": "lost@example.com", "first_name": "Evan", "last_name": "Old", "phone": "555-05", "country": "US", "region": "WA", "city": "Seattle", "signup_timestamp": "2026-08-01 00:00:00"}
        ])

        self.mock_orders = pd.DataFrame([
            # CUST-1: Very recent, 5 orders, high monetary
            {"order_id": "O-1", "customer_id": "CUST-1", "order_timestamp": "2026-10-27 10:00:00", "order_date": "2026-10-27", "total_revenue": 500.0, "discount_amount": 0.0},
            {"order_id": "O-2", "customer_id": "CUST-1", "order_timestamp": "2026-10-25 10:00:00", "order_date": "2026-10-25", "total_revenue": 400.0, "discount_amount": 0.0},
            {"order_id": "O-3", "customer_id": "CUST-1", "order_timestamp": "2026-10-20 10:00:00", "order_date": "2026-10-20", "total_revenue": 300.0, "discount_amount": 0.0},
            {"order_id": "O-4", "customer_id": "CUST-1", "order_timestamp": "2026-10-15 10:00:00", "order_date": "2026-10-15", "total_revenue": 200.0, "discount_amount": 0.0},
            {"order_id": "O-5", "customer_id": "CUST-1", "order_timestamp": "2026-10-10 10:00:00", "order_date": "2026-10-10", "total_revenue": 100.0, "discount_amount": 0.0},

            # CUST-2: Old (Aug 5), 1 order, low monetary
            {"order_id": "O-6", "customer_id": "CUST-2", "order_timestamp": "2026-08-05 10:00:00", "order_date": "2026-08-05", "total_revenue": 50.0, "discount_amount": 0.0},

            # CUST-3: Recent (Oct 26), 1 order
            {"order_id": "O-7", "customer_id": "CUST-3", "order_timestamp": "2026-10-26 10:00:00", "order_date": "2026-10-26", "total_revenue": 150.0, "discount_amount": 0.0},

            # CUST-4: Mid (Sep 15), 3 orders
            {"order_id": "O-8", "customer_id": "CUST-4", "order_timestamp": "2026-09-15 10:00:00", "order_date": "2026-09-15", "total_revenue": 200.0, "discount_amount": 0.0},
            {"order_id": "O-9", "customer_id": "CUST-4", "order_timestamp": "2026-09-10 10:00:00", "order_date": "2026-09-10", "total_revenue": 200.0, "discount_amount": 0.0},
            {"order_id": "O-10", "customer_id": "CUST-4", "order_timestamp": "2026-09-01 10:00:00", "order_date": "2026-09-01", "total_revenue": 200.0, "discount_amount": 0.0},

            # CUST-5: Old (Aug 1), 1 order
            {"order_id": "O-11", "customer_id": "CUST-5", "order_timestamp": "2026-08-02 10:00:00", "order_date": "2026-08-02", "total_revenue": 40.0, "discount_amount": 0.0}
        ])

        self.mock_sessions = pd.DataFrame([
            {"session_id": f"s-{i}", "canonical_customer_id": f"CUST-{(i % 5) + 1}", "session_start_timestamp": "2026-09-01 10:00:00", "channel_grouping": "Paid Video - TikTok Ads"}
            for i in range(10)
        ])

    def test_scores_within_valid_bounds(self):
        df_dim, df_seg = self.engine.calculate_rfm_clv(self.mock_customers, self.mock_orders, self.mock_sessions)
        self.assertTrue(df_dim["r_score"].between(1, 5).all())
        self.assertTrue(df_dim["f_score"].between(1, 5).all())
        self.assertTrue(df_dim["m_score"].between(1, 5).all())

    def test_vip_champion_highest_clv(self):
        df_dim, _ = self.engine.calculate_rfm_clv(self.mock_customers, self.mock_orders, self.mock_sessions)
        c1 = df_dim[df_dim["canonical_customer_id"] == "CUST-1"].iloc[0]
        c2 = df_dim[df_dim["canonical_customer_id"] == "CUST-2"].iloc[0]
        
        # CUST-1 should have higher predicted CLV than dormant CUST-2
        self.assertGreater(c1["clv_predicted_12m"], c2["clv_predicted_12m"])
        self.assertEqual(c1["r_score"], 5)


if __name__ == "__main__":
    unittest.main()

"""
End-to-End Pipeline Integration Test
Executes the full warehouse runner and validates output schemas, row counts, and data contracts.
"""

import os
import sys
import unittest
import pandas as pd

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.dbt_local_runner.engine import LocalWarehouseRunner


class TestEndToEndPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.runner = LocalWarehouseRunner(project_root)
        cls.results = cls.runner.run_pipeline()
        cls.warehouse_dir = os.path.join(project_root, "data", "warehouse")

    def test_pipeline_executed_successfully(self):
        self.assertGreater(self.results["dim_customers_360"], 0)
        self.assertGreater(self.results["fct_attribution_multi_touch"], 0)
        self.assertGreater(self.results["agg_campaign_performance_roi"], 0)

    def test_all_quality_assertions_passed(self):
        test_results = self.results["test_results"]
        for test_name, status in test_results.items():
            self.assertEqual(status, "PASSED", f"Assertion failed for {test_name}")

    def test_warehouse_files_exist_on_disk(self):
        expected_files = [
            "dim_customers_360.csv",
            "fct_customer_rfm_segments.csv",
            "fct_attribution_multi_touch.csv",
            "agg_campaign_performance_roi.csv",
            "agg_budget_reallocation_recommendations.csv"
        ]
        for f in expected_files:
            file_path = os.path.join(self.warehouse_dir, f)
            self.assertTrue(os.path.exists(file_path), f"Missing warehouse file: {f}")
            df = pd.read_csv(file_path)
            self.assertGreater(len(df), 0, f"Warehouse file {f} is empty")


if __name__ == "__main__":
    unittest.main()

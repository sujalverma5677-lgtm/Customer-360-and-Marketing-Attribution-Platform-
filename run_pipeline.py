"""
Customer 360 & Marketing Attribution Platform
Single-command master runner for data generation, identity resolution, dbt modeling, and test execution.
"""

import os
import sys

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(project_root, "src"))

from generator.generate_ecommerce_data import save_datasets
from dbt_local_runner.engine import LocalWarehouseRunner
from visualization.tableau_spec_generator import generate_tableau_artifacts


def main():
    print("Step 1: Generating Raw Datasets (GA4 + CRM + Ad Spend)...")
    raw_dir = os.path.join(project_root, "data", "raw")
    save_datasets(raw_dir)

    print("\nStep 2: Executing Transformation Warehouse Pipeline...")
    runner = LocalWarehouseRunner(project_root)
    results = runner.run_pipeline()

    print("\nStep 3: Generating Tableau Artifacts & Dashboard Blueprint...")
    tableau_dir = os.path.join(project_root, "data", "tableau_exports")
    generate_tableau_artifacts(tableau_dir)

    print("\n" + "=" * 80)
    print("PIPELINE EXECUTION COMPLETE!")
    print(f" - Customers (360): {results['dim_customers_360']:,}")
    print(f" - Attributed Touchpoints: {results['fct_attribution_multi_touch']:,}")
    print(f" - Campaign Metrics: {results['agg_campaign_performance_roi']:,}")
    print("\nTo launch the interactive dashboard, run:")
    print("  streamlit run dashboard/app.py")
    print("=" * 80)


if __name__ == "__main__":
    main()

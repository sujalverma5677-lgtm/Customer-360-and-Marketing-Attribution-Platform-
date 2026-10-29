"""
Marketing Budget Reallocation Optimizer
Uses Multi-Touch Attribution insights and Diminishing Marginal Returns (Hill / Power Law curve)
to prescribe the optimal budget shift across marketing channels.
"""

import pandas as pd
import numpy as np


class BudgetOptimizer:
    def __init__(self, elasticity: float = 0.75):
        """
        elasticity: Diminishing returns coefficient (0 < beta < 1).
        A value of 0.75 reflects standard paid advertising saturation curves.
        """
        self.elasticity = elasticity

    def optimize_budget(
        self,
        df_campaign_perf: pd.DataFrame,
        total_budget_multiplier: float = 1.0
    ) -> pd.DataFrame:
        """
        Calculates current vs recommended budget reallocation and projected revenue lift.
        Uses Time-Decay / Multi-Touch efficiency rather than flawed Last-Touch metrics.
        """
        print("Running Budget Optimization using Multi-Touch Attribution...")
        paid = df_campaign_perf[df_campaign_perf["total_spend_usd"] > 0].copy()

        total_current_spend = paid["total_spend_usd"].sum()
        target_total_spend = total_current_spend * total_budget_multiplier

        # Efficiency metric: Blended Multi-Touch Value per dollar of spend
        # MTA ROAS incorporates both top-of-funnel discovery (first-touch) and conversion closing (time-decay)
        paid["blended_mta_roas"] = (
            (0.35 * paid["roas_first_touch"] + 0.65 * paid["roas_time_decay"])
        ).clip(lower=0.1)

        # Baseline Last-Touch ROAS for comparison
        paid["legacy_lt_roas"] = paid["roas_last_touch"].fillna(0.1).clip(lower=0.1)

        # Marginal weighting based on MTA ROAS relative to channel average
        avg_mta_roas = paid["blended_mta_roas"].mean()
        paid["efficiency_factor"] = np.power(paid["blended_mta_roas"] / avg_mta_roas, 0.6)

        # Unconstrained target allocation
        unconstrained_spend = paid["total_spend_usd"] * paid["efficiency_factor"]
        paid["recommended_budget_usd"] = (
            (unconstrained_spend / unconstrained_spend.sum()) * target_total_spend
        ).round(2)

        # Bound adjustments to realistic quarterly operational bounds (-35% to +50%)
        min_allowed = paid["total_spend_usd"] * 0.65
        max_allowed = paid["total_spend_usd"] * 1.50
        paid["recommended_budget_usd"] = paid["recommended_budget_usd"].clip(lower=min_allowed, upper=max_allowed)
        
        # Re-normalize to exact target budget
        paid["recommended_budget_usd"] = (
            (paid["recommended_budget_usd"] / paid["recommended_budget_usd"].sum()) * target_total_spend
        ).round(2)

        # Calculate budget changes
        paid["budget_change_usd"] = (paid["recommended_budget_usd"] - paid["total_spend_usd"]).round(2)
        paid["budget_change_pct"] = ((paid["budget_change_usd"] * 100.0) / paid["total_spend_usd"]).round(1)

        # Revenue Response Function: Rev = A * Spend^beta
        # A = Current_TimeDecay_Revenue / (Current_Spend^beta)
        paid["scale_factor_A"] = paid["revenue_time_decay"] / (np.power(paid["total_spend_usd"], self.elasticity) + 1e-6)
        
        paid["projected_revenue_usd"] = (
            paid["scale_factor_A"] * np.power(paid["recommended_budget_usd"], self.elasticity)
        ).round(2)

        paid["revenue_lift_usd"] = (paid["projected_revenue_usd"] - paid["revenue_time_decay"]).round(2)
        paid["projected_roas"] = (paid["projected_revenue_usd"] / paid["recommended_budget_usd"]).round(2)

        def narrative(row):
            pct = row["budget_change_pct"]
            ch_name = row["channel_name"]
            if pct >= 15.0:
                return f"SCALE UP (+{pct}%): High MTA ROAS ({row['roas_time_decay']:.2f}x). Under-invested discovery engine."
            elif pct <= -10.0:
                return f"TRIM BUDGET ({pct}%): Channel saturated under MTA. Shift capital to top-of-funnel."
            else:
                return f"MAINTAIN ({pct:+0.1f}%): Operates near optimal marginal efficiency."

        paid["optimization_rationale"] = paid.apply(narrative, axis=1)

        cols = [
            "channel_name", "total_spend_usd", "recommended_budget_usd",
            "budget_change_usd", "budget_change_pct",
            "revenue_time_decay", "projected_revenue_usd", "revenue_lift_usd",
            "roas_time_decay", "projected_roas", "optimization_rationale"
        ]

        return paid[cols].sort_values(by="budget_change_usd", ascending=False).reset_index(drop=True)

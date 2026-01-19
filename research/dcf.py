"""
DCF Calculator - Discounted Cash Flow valuation model
"""

from typing import Dict, List, Any
from dataclasses import dataclass
import json


@dataclass
class DCFAssumptions:
    """Assumptions for DCF model"""
    # Growth rates by phase
    growth_1_5: float  # Years 1-5 growth rate
    growth_5_10: float  # Years 5-10 growth rate
    terminal_growth: float  # Terminal growth rate

    # Margins
    operating_margin: float
    tax_rate: float

    # Investment
    capex_to_revenue: float
    depreciation_to_revenue: float
    nwc_change_to_revenue: float

    # Starting values
    current_revenue: float
    current_fcf: float
    shares_outstanding: float


class DCFCalculator:
    """Calculates intrinsic value using DCF methodology"""

    def __init__(self):
        self.projection_years = 10

    def calculate_intrinsic_value(
        self,
        assumptions: DCFAssumptions,
        discount_rate: float
    ) -> Dict[str, Any]:
        """Calculate intrinsic value per share"""

        # Project cash flows
        cash_flows = []
        revenue = assumptions.current_revenue

        for year in range(1, self.projection_years + 1):
            # Determine growth rate based on phase
            if year <= 5:
                growth = assumptions.growth_1_5
            else:
                growth = assumptions.growth_5_10

            revenue = revenue * (1 + growth)

            # Calculate FCF
            operating_income = revenue * assumptions.operating_margin
            taxes = operating_income * assumptions.tax_rate
            nopat = operating_income - taxes

            capex = revenue * assumptions.capex_to_revenue
            depreciation = revenue * assumptions.depreciation_to_revenue
            nwc_change = revenue * assumptions.nwc_change_to_revenue

            fcf = nopat + depreciation - capex - nwc_change
            cash_flows.append({
                "year": year,
                "revenue": revenue,
                "fcf": fcf
            })

        # Terminal value
        final_fcf = cash_flows[-1]["fcf"]
        terminal_value = final_fcf * (1 + assumptions.terminal_growth) / (discount_rate - assumptions.terminal_growth)

        # Discount cash flows
        pv_cash_flows = 0
        for i, cf in enumerate(cash_flows):
            discount_factor = (1 + discount_rate) ** (i + 1)
            pv_cash_flows += cf["fcf"] / discount_factor

        # Discount terminal value
        terminal_discount_factor = (1 + discount_rate) ** self.projection_years
        pv_terminal = terminal_value / terminal_discount_factor

        # Total enterprise value
        enterprise_value = pv_cash_flows + pv_terminal

        # Equity value per share (simplified - ignoring debt/cash for now)
        equity_value_per_share = enterprise_value / assumptions.shares_outstanding

        return {
            "enterprise_value": enterprise_value,
            "equity_value_per_share": equity_value_per_share,
            "pv_cash_flows": pv_cash_flows,
            "pv_terminal": pv_terminal,
            "terminal_value": terminal_value,
            "projected_cash_flows": cash_flows
        }

    def calculate_scenario_matrix(
        self,
        scenarios: Dict[str, DCFAssumptions],
        discount_rates: List[float]
    ) -> Dict[str, Dict[str, float]]:
        """Calculate intrinsic values for all scenario/discount rate combinations"""

        matrix = {}
        for rate in discount_rates:
            rate_key = f"{int(rate*100)}%"
            matrix[rate_key] = {}

            for scenario_name, assumptions in scenarios.items():
                result = self.calculate_intrinsic_value(assumptions, rate)
                matrix[rate_key][scenario_name] = round(result["equity_value_per_share"], 2)

        return matrix

    def calculate_probability_weighted_value(
        self,
        scenario_values: Dict[str, float],
        probabilities: Dict[str, float]
    ) -> float:
        """Calculate probability-weighted expected value"""

        weighted_sum = 0
        for scenario, value in scenario_values.items():
            prob = probabilities.get(scenario, 0)
            weighted_sum += value * prob

        return round(weighted_sum, 2)


def create_scenarios_from_analysis(analysis_text: str) -> Dict[str, DCFAssumptions]:
    """Parse analysis text to create scenario assumptions (helper function)"""
    # This would be enhanced with actual parsing logic
    # For now, return placeholder scenarios

    base_revenue = 10000  # Would be parsed from analysis
    base_fcf = 1000
    shares = 1000

    scenarios = {
        "super_bear": DCFAssumptions(
            growth_1_5=0.02, growth_5_10=0.01, terminal_growth=0.01,
            operating_margin=0.08, tax_rate=0.25,
            capex_to_revenue=0.05, depreciation_to_revenue=0.04, nwc_change_to_revenue=0.02,
            current_revenue=base_revenue, current_fcf=base_fcf, shares_outstanding=shares
        ),
        "bear": DCFAssumptions(
            growth_1_5=0.05, growth_5_10=0.03, terminal_growth=0.02,
            operating_margin=0.10, tax_rate=0.25,
            capex_to_revenue=0.05, depreciation_to_revenue=0.04, nwc_change_to_revenue=0.02,
            current_revenue=base_revenue, current_fcf=base_fcf, shares_outstanding=shares
        ),
        "base": DCFAssumptions(
            growth_1_5=0.10, growth_5_10=0.05, terminal_growth=0.025,
            operating_margin=0.12, tax_rate=0.25,
            capex_to_revenue=0.05, depreciation_to_revenue=0.04, nwc_change_to_revenue=0.02,
            current_revenue=base_revenue, current_fcf=base_fcf, shares_outstanding=shares
        ),
        "bull": DCFAssumptions(
            growth_1_5=0.15, growth_5_10=0.08, terminal_growth=0.03,
            operating_margin=0.15, tax_rate=0.25,
            capex_to_revenue=0.05, depreciation_to_revenue=0.04, nwc_change_to_revenue=0.02,
            current_revenue=base_revenue, current_fcf=base_fcf, shares_outstanding=shares
        ),
        "super_bull": DCFAssumptions(
            growth_1_5=0.25, growth_5_10=0.12, terminal_growth=0.035,
            operating_margin=0.18, tax_rate=0.25,
            capex_to_revenue=0.05, depreciation_to_revenue=0.04, nwc_change_to_revenue=0.02,
            current_revenue=base_revenue, current_fcf=base_fcf, shares_outstanding=shares
        ),
    }

    return scenarios

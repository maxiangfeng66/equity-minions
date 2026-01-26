"""
Reverse DCF Engine - What growth rate does the current price imply?

This engine works backwards from market price to determine what growth
assumptions the market is pricing in. This is a powerful sanity check:

If our DCF assumes 20% growth and the market is pricing in 25% growth,
either:
1. The market is too optimistic (sell signal)
2. We're missing something (investigate)

Formula:
Given: Market Price, WACC, Terminal Growth, Current FCF
Solve for: Implied Revenue Growth Rate
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import math

from ..assumption_extractor import ValuationInputs


@dataclass
class ReverseDCFResult:
    """Result of Reverse DCF analysis"""
    ticker: str
    current_price: float
    market_cap: float
    currency: str

    # Implied assumptions
    implied_growth_rate: float
    implied_growth_description: str

    # Context
    wacc_used: float
    terminal_growth_used: float

    # Comparison with our assumptions
    our_base_growth: float
    growth_difference: float
    market_view: str  # "MORE_OPTIMISTIC", "MORE_PESSIMISTIC", "ALIGNED"

    # Calculation
    calculation: str

    # Validation
    is_valid: bool
    warnings: List[str]


class ReverseDCFEngine:
    """
    Reverse DCF Engine - Derive implied growth from market price.

    This engine iteratively solves for the growth rate that would
    produce the current market valuation, given fixed WACC and
    terminal assumptions.

    This is extremely useful for understanding market expectations.
    """

    def __init__(self, projection_years: int = 10):
        self.projection_years = projection_years

    def calculate(self, inputs: ValuationInputs) -> ReverseDCFResult:
        """
        Calculate implied growth rate from current market price.

        Args:
            inputs: Complete valuation inputs

        Returns:
            ReverseDCFResult with implied growth analysis
        """
        warnings = []
        md = inputs.market_data
        wi = inputs.wacc_inputs

        # Calculate WACC
        cost_of_equity = (
            wi.risk_free_rate +
            wi.beta * wi.equity_risk_premium +
            wi.country_risk_premium
        )
        wacc = (
            (1 - wi.debt_to_total_capital) * cost_of_equity +
            wi.debt_to_total_capital * wi.cost_of_debt * (1 - wi.tax_rate)
        )

        # Get terminal growth from base scenario
        base_scenario = inputs.scenarios.get('base')
        terminal_growth = base_scenario.terminal_growth if base_scenario else 0.025

        # Target: Current Enterprise Value
        target_ev = md.market_cap + md.net_debt

        # Current FCF estimate
        if md.ebit_ttm > 0:
            current_fcf = md.ebit_ttm * (1 - wi.tax_rate) * 0.9  # 90% FCF conversion
        else:
            current_fcf = md.revenue_ttm * 0.05  # 5% FCF margin assumption
            warnings.append("Using estimated FCF margin (5%)")

        # Binary search for implied growth rate
        implied_growth = self._solve_for_growth(
            target_ev=target_ev,
            current_fcf=current_fcf,
            wacc=wacc,
            terminal_growth=terminal_growth,
            years=self.projection_years
        )

        # Get our base case growth for comparison
        our_base_growth = base_scenario.revenue_growth_y1_3 if base_scenario else 0.15

        # Calculate difference
        growth_difference = implied_growth - our_base_growth

        # Determine market view
        if growth_difference > 0.05:
            market_view = "MORE_OPTIMISTIC"
            description = f"Market expects {implied_growth:.1%} growth, {growth_difference:.1%} higher than our base case"
        elif growth_difference < -0.05:
            market_view = "MORE_PESSIMISTIC"
            description = f"Market expects {implied_growth:.1%} growth, {abs(growth_difference):.1%} lower than our base case"
        else:
            market_view = "ALIGNED"
            description = f"Market expectations ({implied_growth:.1%}) aligned with our base case ({our_base_growth:.1%})"

        # Build calculation string
        calculation = f"""Reverse DCF Analysis:
Target EV (from market): {md.currency} {target_ev/1000:.1f}B
Current FCF (estimated): {md.currency} {current_fcf:.0f}M
WACC: {wacc:.2%}
Terminal Growth: {terminal_growth:.2%}

Solving for growth rate that produces target EV...
Implied Growth Rate: {implied_growth:.2%}

Our Base Case Growth: {our_base_growth:.2%}
Difference: {growth_difference:+.2%}
Market View: {market_view}"""

        return ReverseDCFResult(
            ticker=inputs.ticker,
            current_price=md.current_price,
            market_cap=md.market_cap,
            currency=md.currency,
            implied_growth_rate=implied_growth,
            implied_growth_description=description,
            wacc_used=wacc,
            terminal_growth_used=terminal_growth,
            our_base_growth=our_base_growth,
            growth_difference=growth_difference,
            market_view=market_view,
            calculation=calculation,
            is_valid=True,
            warnings=warnings
        )

    def _solve_for_growth(
        self,
        target_ev: float,
        current_fcf: float,
        wacc: float,
        terminal_growth: float,
        years: int
    ) -> float:
        """
        Binary search to find growth rate that produces target EV.
        """
        low = -0.10  # -10% decline
        high = 0.50   # 50% growth
        tolerance = 0.001

        for _ in range(50):  # Max iterations
            mid = (low + high) / 2
            ev = self._calculate_ev(current_fcf, mid, wacc, terminal_growth, years)

            if abs(ev - target_ev) / target_ev < tolerance:
                return mid

            if ev < target_ev:
                low = mid
            else:
                high = mid

        return mid

    def _calculate_ev(
        self,
        current_fcf: float,
        growth_rate: float,
        wacc: float,
        terminal_growth: float,
        years: int
    ) -> float:
        """
        Calculate EV given growth assumptions.
        Simplified: assumes constant growth throughout projection period.
        """
        # Project FCFs
        fcfs = []
        fcf = current_fcf
        for year in range(1, years + 1):
            fcf = fcf * (1 + growth_rate)
            fcfs.append(fcf)

        # PV of FCFs
        pv_fcfs = sum(fcf / ((1 + wacc) ** (i + 1)) for i, fcf in enumerate(fcfs))

        # Terminal value
        if wacc > terminal_growth:
            terminal_fcf = fcfs[-1]
            tv = terminal_fcf * (1 + terminal_growth) / (wacc - terminal_growth)
            pv_tv = tv / ((1 + wacc) ** years)
        else:
            pv_tv = 0

        return pv_fcfs + pv_tv
